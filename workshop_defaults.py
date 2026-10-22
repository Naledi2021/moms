"""Reusable construction preferences, separate from prices and customer revisions."""
from copy import deepcopy
from datetime import datetime,timezone
import fcntl
import json
import math
from pathlib import Path

STORE=Path(__file__).with_name('data')/'workshop_defaults.json'
BUILTIN={'job_material':'Melamine','job_thickness':18.,'job_width':600.,'job_height':720.,'job_depth':500.,'job_shelves':1,'job_clearance':0.,
 'job_carcass_edging':1,'job_door_material':'Melamine','job_door_thickness':18.,'job_door_edging':1,'job_door_edges':['Top','Bottom','Left','Right'],
 'job_hinge_brand':'Roco','job_hinges_per_door':2,'plates_included':False}


def validate_settings(settings):
    if not isinstance(settings,dict) or any(k not in BUILTIN for k in settings):raise ValueError('Use a workshop-defaults backup or the construction controls.')
    result=deepcopy(BUILTIN);result.update(settings)
    for k in ('job_material','job_door_material'):
        if result[k] not in ('Melamine','MDF','Solid wood'):raise ValueError('Choose a supported board material.')
    for k in ('job_thickness','job_door_thickness'):
        if result[k] not in (16,18,22.5):raise ValueError('Board thickness must be 16, 18 or 22.5 mm.')
    for k in ('job_carcass_edging','job_door_edging'):
        if result[k] not in (1,2):raise ValueError('Edging must be 1 or 2 mm.')
    for k in ('job_width','job_height','job_depth','job_clearance','job_shelves','job_hinges_per_door'):
        if isinstance(result[k],bool) or not isinstance(result[k],(int,float)) or not math.isfinite(result[k]):raise ValueError('Workshop dimensions and counts must be finite numbers.')
    if min(result['job_width'],result['job_height'])<=2*result['job_thickness'] or result['job_depth']<200:raise ValueError('Standard cabinet dimensions must allow both sides and two 100 mm rails.')
    if not 0<=result['job_clearance']<result['job_width']-2*result['job_thickness']:raise ValueError('The extra shelf fitting gap must be nonnegative and leave a positive shelf width.')
    if not 0<=result['job_shelves']<=20 or int(result['job_shelves'])!=result['job_shelves']:raise ValueError('Shelf count must be a whole number from 0 to 20.')
    if result['job_hinges_per_door']<1 or int(result['job_hinges_per_door'])!=result['job_hinges_per_door']:raise ValueError('Hinge count must be a positive whole number.')
    if result['job_hinge_brand'] not in ('Roco','Blum','Gelmar'):raise ValueError('Choose a supported hinge brand.')
    edges=result['job_door_edges']
    if not isinstance(edges,list) or any(e not in ('Top','Bottom','Left','Right') for e in edges) or len(set(edges))!=len(edges):raise ValueError('Choose valid door edges.')
    if not isinstance(result['plates_included'],bool):raise ValueError('Mounting plate setting must be true or false.')
    return result


def load_workshop(path=None):
    path=Path(path or STORE)
    if not path.exists():return {'version':1,'updated_utc':None,'settings':deepcopy(BUILTIN)}
    data=json.loads(path.read_text());data['settings']=validate_settings(data['settings']);return data


def save_workshop(settings,path=None):
    values=validate_settings(settings);path=Path(path or STORE);path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix('.lock').open('w') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        data={'version':1,'updated_utc':datetime.now(timezone.utc).isoformat(),'settings':values}
        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2,allow_nan=False));temp.replace(path)
    return data


def seed_workshop(state,defaults):
    for k,v in defaults.get('settings',{}).items():
        if k not in state:state[k]=deepcopy(v)


def catalogue_for_settings(settings):
    from unit_library import LIBRARY
    library=deepcopy(LIBRARY)
    for spec in library.values():
        if spec['category']=='Corner':spec['height']=settings.get('job_height',720)
        if spec['category']=='Base':
            spec.update(height=settings.get('job_height',720),depth=settings.get('job_depth',500))
            if spec['shelves']>0:spec['shelves']=int(settings.get('job_shelves',spec['shelves']))
            # Drawer, sink, oven and pull-out models retain their zero-shelf construction.
    return library
