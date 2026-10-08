"""Validated supplier price uploads with effective dates and retained revision history."""
from datetime import date, datetime, timezone
import fcntl
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import zipfile
import pandas as pd

STORE = Path(__file__).with_name('data') / 'supplier_updates.json'
UNITS = {'sheet': 'sheet', 'panel': 'sheet', 'm2': 'm2', 'm²': 'm2', 'each': 'each', 'set': 'set', 'metre': 'metre', 'meter': 'metre', 'm': 'metre'}
TEMPLATE = 'sku,product,price,unit,length_mm,width_mm,thickness_mm\nEXAMPLE-BOARD,Example board,1000,sheet,2750,1840,18\nEXAMPLE-HINGE,Example soft-close hinge,25,each,,,\n'

def read_upload(contents, filename, sheet=None):
    if len(contents) > 10_000_000: raise ValueError('Upload must be smaller than 10 MB.')
    ext = Path(filename).suffix.lower()
    if ext == '.csv':
        frame = pd.read_csv(BytesIO(contents), dtype=str, keep_default_na=False, sep=None, engine='python', nrows=5001)
    elif ext == '.xlsx':
        with zipfile.ZipFile(BytesIO(contents)) as z:
            if sum(f.file_size for f in z.infolist()) > 50_000_000: raise ValueError('Workbook is too large when unpacked.')
        frame = pd.read_excel(BytesIO(contents), sheet_name=sheet if sheet is not None else 0, dtype=str, keep_default_na=False, nrows=5001, engine='openpyxl')
    else: raise ValueError('Use a CSV or .xlsx file. PDF lists must be converted to a spreadsheet first.')
    if frame.empty or len(frame) > 5000 or len(frame.columns) > 40:
        raise ValueError('Upload must contain 1–5000 product rows and at most 40 columns.')
    frame.columns = [str(c).strip() for c in frame.columns]
    if len(set(frame.columns)) != len(frame.columns): raise ValueError('Column names must be unique.')
    return frame

def numeric(value, label, optional=False):
    text = str(value).strip()
    if optional and not text: return None
    try: number = float(text)
    except ValueError: raise ValueError(f'{label} must be a number (use a decimal point, without R or thousands separators).')
    if not math.isfinite(number) or number <= 0: raise ValueError(f'{label} must be positive and finite.')
    return number

def validate(frame, mapping):
    rows=[]; errors=[]; seen=set()
    for index, raw in frame.iterrows():
        try:
            def value(key):
                col=mapping.get(key)
                return str(raw[col]).strip() if col else ''
            sku=value('sku'); name=value('product')
            if not sku or not name: raise ValueError('SKU/code and product name are required.')
            if sku.casefold() in seen: raise ValueError(f'Duplicate SKU: {sku}')
            unit=UNITS.get(value('unit').lower())
            if not unit: raise ValueError('Unit must be sheet, m2, each, set or metre.')
            row=dict(sku=sku,product=name,price=numeric(value('price'),'Price'),unit=unit,
                length_mm=numeric(value('length_mm'),'Length',True),width_mm=numeric(value('width_mm'),'Width',True),thickness_mm=numeric(value('thickness_mm'),'Thickness',True))
            if unit=='sheet' and (row['length_mm'] is None or row['width_mm'] is None):
                raise ValueError('Sheet/panel prices require length and width in mm.')
            seen.add(sku.casefold()); rows.append(row)
        except ValueError as e: errors.append(f'Row {index+2}: {e}')
    return rows,errors

def load(path=STORE):
    path=Path(path)
    return json.loads(path.read_text()) if path.exists() else {'updates':[]}

def save(rows,supplier,effective_date,vat_basis,vat_rate,filename,path=STORE):
    supplier=supplier.strip()
    if not supplier or not rows: raise ValueError('Supplier and validated products are required.')
    if vat_basis not in ('Excluded','Included','Not specified'): raise ValueError('Choose a VAT basis.')
    if vat_basis=='Included' and (vat_rate is None or not math.isfinite(vat_rate) or vat_rate<0):
        raise ValueError('Enter the VAT percentage included in these supplier prices.')
    revision=dict(supplier=supplier,effective_date=date.fromisoformat(str(effective_date)).isoformat(),vat_basis=vat_basis,vat_rate=vat_rate if vat_basis=='Included' else None,filename=Path(filename).name,products=rows)
    revision['id']=hashlib.sha256(json.dumps(revision,sort_keys=True).encode()).hexdigest()
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix('.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        history=load(path)
        if any(u['id']==revision['id'] for u in history['updates']): return False
        revision['uploaded_utc']=datetime.now(timezone.utc).isoformat()
        history['updates'].append(revision)
        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(history,indent=2));temp.replace(path)
    return True

def current_products(history,today=None):
    today=today or date.today(); latest={}
    for update in sorted(history['updates'],key=lambda u:(u['effective_date'],u['uploaded_utc'])):
        if date.fromisoformat(update['effective_date'])>today: continue
        for product in update['products']:
            latest[(update['supplier'].casefold(),product['sku'].casefold())]=dict(product,supplier=update['supplier'],effective_date=update['effective_date'],vat_basis=update['vat_basis'],vat_rate=update['vat_rate'],filename=update['filename'])
    return list(latest.values())

def unit_price_ex_vat(product):
    if product['vat_basis']=='Not specified': raise ValueError('VAT basis is unknown. Update the supplier entry before using it for costing.')
    price=product['price']
    if product['vat_basis']=='Included': price/=1+product['vat_rate']/100
    return price

def material_rate(product):
    price=unit_price_ex_vat(product)
    if product['unit']=='m2': return price
    if product['unit']=='sheet': return price/(product['length_mm']*product['width_mm']/1_000_000)
    raise ValueError('Material costing requires a sheet/panel or m2 price.')
