"""Freeze room geometry independently from cabinet layout approval."""
from copy import deepcopy
import hashlib
import json


def room_fingerprint(layout):
    return hashlib.sha256(json.dumps(layout,sort_keys=True,allow_nan=False).encode()).hexdigest()


def freeze_room(layout):
    from layout_ui import validate_layout
    from room_geometry import validate_walls
    validate_layout(layout['length'],layout['width'],layout['height'],layout['openings'])
    validate_walls(layout.get('walls',[]),layout)
    return {'layout':deepcopy(layout),'fingerprint':room_fingerprint(layout)}


def check_room_lock(lock,layout):
    if lock and (room_fingerprint(lock['layout'])!=lock['fingerprint'] or room_fingerprint(layout)!=lock['fingerprint']):
        raise ValueError('Room structure differs from the frozen plan. Unlock the room before changing walls or openings.')
