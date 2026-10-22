"""Business material library. Catalogue records are copied into design snapshots."""
import fcntl
import json
import math
from pathlib import Path
import re
import uuid

STORE=Path(__file__).with_name('data')/'materials.json'
SURFACES=('Carcass','Front','Worktop','Tiles','Paint','Splashback','Glass')
FIXTURES=('Lighting','Sink','Tap','Appliance','Extractor','Handle','Accessory')
CATEGORIES=(*SURFACES,*FIXTURES)

def starter_materials():
    return [dict(id='sample-white',name='Sample white melamine',category='Carcass',thickness_mm=18,color='#eeeae2',finish='Matte',supplier='',price_m2=None),
            dict(id='sample-oak',name='Sample oak finish',category='Front',thickness_mm=18,color='#b88a55',finish='Wood grain',supplier='',price_m2=None),
            dict(id='sample-stone',name='Sample light stone worktop',category='Worktop',thickness_mm=30,color='#d6d1c7',finish='Matte',supplier='',price_m2=None)]

def validate_material(record):
    if not isinstance(record,dict) or not isinstance(record.get('name'),str) or not 1<=len(record['name'].strip())<=100:raise ValueError('Enter a material name of 1–100 characters.')
    if record.get('category') not in CATEGORIES:raise ValueError('Choose a material category.')
    t=float(record['thickness_mm']);price=record.get('price_m2')
    if not math.isfinite(t) or not 0<t<=200:raise ValueError('Material thickness must be positive and at most 200 mm.')
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',str(record.get('color',''))):raise ValueError('Choose a valid material colour.')
    if record.get('finish') not in ('Matte','Gloss','Wood grain'):raise ValueError('Choose a supported finish.')
    if price is not None and (not math.isfinite(float(price)) or float(price)<0):raise ValueError('Material price must be nonnegative and finite.')
    if not isinstance(record.get('supplier',''),str) or len(record.get('supplier',''))>150:raise ValueError('Supplier name is too long.')
    for key in ('width_mm','height_mm','depth_mm'):
        if key in record and (not math.isfinite(float(record[key])) or not 0<float(record[key])<=20000):raise ValueError('Product dimensions must be positive and at most 20,000 mm.')
    if record.get('price_each') is not None and (not math.isfinite(float(record['price_each'])) or float(record['price_each'])<0):raise ValueError('Item price must be nonnegative and finite.')
    for key in ('sku','notes'):
        if not isinstance(record.get(key,''),str) or len(record.get(key,''))>1000:raise ValueError('Product reference or notes are too long.')
    return record

def load_materials(path=None):
    path=Path(path or STORE)
    return json.loads(path.read_text()) if path.exists() else {'version':1,'materials':starter_materials()}

def save_material(record,path=None):
    record=dict(validate_material(record));record['name']=record['name'].strip()
    record.setdefault('id',str(uuid.uuid4()))
    path=Path(path or STORE);path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix('.lock').open('w') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX);data=load_materials(path)
        records=data['materials'];found=next((i for i,item in enumerate(records) if item['id']==record['id']),None)
        if found is None:
            if len(records)>=500:raise ValueError('Use at most 500 materials.')
            records.append(record)
        else:records[found]=record
        tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2,allow_nan=False));tmp.replace(path)
    return record

def details(row):
    value=row.get('Design details','')
    if not value:return {}
    if not isinstance(value,str) or len(value)>60000:raise ValueError('Unit details must be a supported design record.')
    result=json.loads(value)
    if not isinstance(result,dict):raise ValueError('Unit design details are invalid.')
    assigned=result.get('materials',{})
    if not isinstance(assigned,dict) or any(key not in CATEGORIES for key in assigned):raise ValueError('Unit material roles are invalid.')
    for record in assigned.values():validate_material(record)
    if not isinstance(result.get('worktop',{}),dict):raise ValueError('Worktop configuration is invalid.')
    return result


def restore_material_library(raw,path=None):
    if len(raw)>2_000_000:raise ValueError('Material backup exceeds 2 MB.')
    data=json.loads(raw)
    records=data['materials']
    if not isinstance(records,list) or len(records)>500:raise ValueError('Invalid material library backup.')
    for record in records:
        validate_material(record)
        if not isinstance(record.get('id'),str) or not 1<=len(record['id'])<=100:raise ValueError('Each restored material needs its original ID.')
    if len({r['id'] for r in records})!=len(records):raise ValueError('Material IDs must be unique.')
    path=Path(path or STORE);path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix('.lock').open('w') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        merged={r['id']:r for r in load_materials(path)['materials']}
        merged.update({r['id']:r for r in records})
        if len(merged)>500:raise ValueError('Use at most 500 materials.')
        tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps({'version':1,'materials':list(merged.values())},indent=2,allow_nan=False));tmp.replace(path)


def starter_products():
    """Unpriced presentation templates, not manufacturer specifications."""
    sizes={'Tiles':(600,600,10),'Paint':(1000,1000,1),'Splashback':(1200,600,6),
           'Glass':(600,720,6),'Lighting':(300,80,300),'Sink':(800,180,500),
           'Tap':(180,350,60),'Appliance':(600,850,600),'Extractor':(900,400,500),
           'Handle':(160,20,30),'Accessory':(300,300,300)}
    return [dict(id='template-'+category.lower(),name='Sample '+category.lower()+' — edit before use',
                 category=category,thickness_mm=min(d,18),color='#c9ced2',finish='Matte',supplier='',
                 price_m2=None,price_each=None,width_mm=w,height_mm=h,depth_mm=d,sku='',
                 notes='Illustrative envelope only. Replace dimensions and specifications with verified product data.')
            for category,(w,h,d) in sizes.items()]
