"""Shared price defaults, separate from customer jobs and immutable quotations."""
from datetime import datetime,timezone
import fcntl
import json
import math
from pathlib import Path

STORE=Path(__file__).with_name('data')/'default_prices.json'
ALLOWANCES={'job_waste','job_hardware','job_labour','job_transport','job_markup','job_tax'}

def load_defaults(path=None):
    path=Path(path or STORE)
    return json.loads(path.read_text()) if path.exists() else {'version':1,'updated_utc':None,'prices':{}}


def validate_prices(prices):
    if not isinstance(prices,dict) or len(prices)>300:raise ValueError('Use at most 300 default price entries.')
    for key,value in prices.items():
        parts=key.split('|')
        valid=key in ALLOWANCES or key=='back|Masonite|3' or (len(parts)==3 and parts[0] in ('carcass','door') and parts[1] in ('Melamine','MDF','Solid wood') and parts[2] in ('16','18','22.5')) or (len(parts)==2 and parts[0] in ('hinge','plate') and parts[1] in ('Roco','Blum','Gelmar')) or key.startswith('accessory|') and 0<len(key[10:])<=160
        if not valid:raise ValueError('Unknown price setting: '+key)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:raise ValueError('Default prices must be finite, nonnegative numbers.')
    return prices


def save_defaults(prices,path=None,replace=False):
    validate_prices(prices)
    path=Path(path or STORE);path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix('.lock').open('w') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        current=load_defaults(path)
        result={'version':1,'updated_utc':datetime.now(timezone.utc).isoformat(),'prices':dict(prices) if replace else current['prices']|prices}
        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(result,indent=2,allow_nan=False));temp.replace(path)
    return result


def material_key(kind,material,thickness):return f'{kind}|{material}|{float(thickness):g}'


def seed_defaults(state,defaults):
    """Apply the job's frozen defaults only to uninitialised pricing widgets."""
    prices=defaults['prices']
    profiles={'carcass_supplier_rate':material_key('carcass',state.get('job_material','Melamine'),state.get('job_thickness',18)),
              'door_supplier_rate':material_key('door',state.get('job_door_material','Melamine'),state.get('job_door_thickness',18)),
              'back_supplier_rate':'back|Masonite|3',
              'hinge_price_manual':'hinge|'+state.get('job_hinge_brand','Roco'),
              'plate_price_manual':'plate|'+state.get('job_hinge_brand','Roco')}
    for widget,profile in profiles.items():
        previous=state.get('_default_profile_'+widget)
        if previous is not None and previous!=profile:
            # Switching a material/thickness/brand starts its appropriate price input.
            prefix=widget.rsplit('_',1)[0]+'_'
            for field in list(state):
                if field.startswith(prefix):state.pop(field,None)
        if widget not in state and profile in prices:state[widget]=float(prices[profile])
        state['_default_profile_'+widget]=profile
    for key in ALLOWANCES:
        if key not in state and key in prices:state[key]=float(prices[key])


def capture_defaults(state,carcass_rate,back_rate,door_rate,hinge,plate,accessories):
    prices={material_key('carcass',state.get('job_material','Melamine'),state.get('job_thickness',18)):carcass_rate,
            material_key('door',state.get('job_door_material','Melamine'),state.get('job_door_thickness',18)):door_rate,
            'back|Masonite|3':back_rate}
    brand=state.get('job_hinge_brand','Roco')
    if hinge is not None:prices['hinge|'+brand]=hinge
    if plate is not None:prices['plate|'+brand]=plate
    for key in ALLOWANCES:
        if key in state:prices[key]=float(state[key])
    for row in accessories:
        name=str(row.get('Accessory','')).strip()
        value=row.get('Unit price (R)')
        if name and value is not None:prices['accessory|'+name]=float(value)
    return validate_prices(prices)
