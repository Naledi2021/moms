"""Place a frozen catalogue record; later library edits never alter saved designs."""
from copy import deepcopy
import json
from materials import validate_material,FIXTURES
from designer_geometry import require_unlocked,validate_unit


def place_product(record,layout,rows,x=0,y=0,z=0,lock=None):
    require_unlocked(lock)
    validate_material(record)
    if len(rows)>=30:raise ValueError('Use at most 30 design items.')
    if any(k not in record for k in ('width_mm','height_mm','depth_mm')):
        raise ValueError('Edit this library item and save its product dimensions before placing it.')
    row={'Name':record['name'],'Type':'Appliance' if record['category'] in FIXTURES else 'Panel',
         'Width (mm)':float(record['width_mm']),'Height (mm)':float(record['height_mm']),
         'Depth (mm)':float(record['depth_mm']),'X (mm)':float(x),'Y (mm)':float(y),'Z (mm)':float(z),
         'Rotation (deg)':0.,'Shelves':0,
         'Design details':json.dumps({'materials':{'Carcass':deepcopy(record)},'catalogue_category':record['category']},sort_keys=True)}
    validate_unit(row,layout)
    return [*deepcopy(rows),row]
