"""Read-only public price checks; never replaces an old price after a failed check."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import time
from urllib.parse import urlsplit
import fcntl
import requests

CATALOG = Path(__file__).with_name('supplier_prices.json')
ALLOWED = {'www.gelmar.co.za', 'www.roco.co.za'}

class ProductData(HTMLParser):
    def __init__(self):
        super().__init__(); self.capture = False; self.data = []; self.blocks = []
    def handle_starttag(self, tag, attrs):
        if tag == 'script' and dict(attrs).get('type') == 'application/ld+json':
            self.capture = True; self.data = []
    def handle_data(self, data):
        if self.capture: self.data.append(data)
    def handle_endtag(self, tag):
        if tag == 'script' and self.capture:
            self.blocks.append(''.join(self.data)); self.capture = False

def nodes(value):
    if isinstance(value, list):
        for item in value: yield from nodes(item)
    elif isinstance(value, dict):
        yield value
        if '@graph' in value: yield from nodes(value['@graph'])

def parse_product(html, expected_sku=None, expected_name=None):
    parser = ProductData(); parser.feed(html)
    products = []
    for block in parser.blocks:
        try: data = json.loads(block, strict=False)
        except json.JSONDecodeError: continue
        for product in nodes(data):
            kind = product.get('@type')
            if kind != 'Product' and not (isinstance(kind,list) and 'Product' in kind): continue
            if expected_sku and str(product.get('sku')) != str(expected_sku): continue
            if expected_name and product.get('name') != expected_name: continue
            products.append(product)
    if len(products) != 1: raise ValueError('Exact product identity not found or ambiguous.')
    product = products[0]; offer = product.get('offers')
    if isinstance(offer,list):
        if len(offer) != 1: raise ValueError('Multiple variants require manual pricing.')
        offer = offer[0]
    if not isinstance(offer,dict) or offer.get('@type') != 'Offer' or offer.get('priceCurrency') != 'ZAR':
        raise ValueError('A single ZAR offer is required; range prices are not accepted.')
    try: price = Decimal(str(offer['price']))
    except (KeyError,InvalidOperation): raise ValueError('Price missing or invalid.')
    if not price.is_finite() or price <= 0: raise ValueError('Price must be positive and finite.')
    return {'price_zar':float(price), 'availability':offer.get('availability','Unknown')}

def checked_url(url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname not in ALLOWED or p.username or p.password or p.port not in (None,443):
        raise ValueError('Only configured supplier HTTPS product URLs are allowed.')

def fetch(url):
    for _ in range(4):
        checked_url(url)
        r = requests.get(url, timeout=25, allow_redirects=False)
        if r.status_code in (301,302,303,307,308):
            from urllib.parse import urljoin
            url = urljoin(url,r.headers['Location']); continue
        r.raise_for_status()
        if len(r.content) > 5_000_000: raise ValueError('Product page exceeds size limit.')
        return r.text
    raise ValueError('Too many redirects.')

def refresh(path=CATALOG, fetcher=fetch):
    path = Path(path)
    with path.with_suffix('.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        catalog = json.loads(path.read_text())
        now = datetime.now(timezone.utc).isoformat()
        for item in catalog['products']:
            item['last_attempt_utc'] = now
            try:
                checked_url(item['source_url'])
                observed = parse_product(fetcher(item['source_url']),item.get('sku'),item.get('expected_name'))
                item.update(observed,last_verified_utc=now,check_status='verified',last_error=None)
            except (requests.RequestException,ValueError,KeyError) as error:
                item['check_status'] = 'failed'
                item['last_error'] = type(error).__name__ + ': price check failed; retained previous observation'
        catalog['last_run_utc'] = now
        temp = path.with_suffix('.tmp'); temp.write_text(json.dumps(catalog,indent=2)); temp.replace(path)
        return catalog

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--loop',action='store_true')
    parser.add_argument('--interval-hours',type=float,default=24)
    args = parser.parse_args()
    if not math.isfinite(args.interval_hours) or args.interval_hours < 1: parser.error('Interval must be at least one hour.')
    while True:
        result = refresh()
        print(result['last_run_utc'], [(p['supplier'],p.get('sku'),p['check_status']) for p in result['products']],flush=True)
        if not args.loop: break
        time.sleep(args.interval_hours*3600)
