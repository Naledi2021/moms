"""Local customer jobs and immutable quotation revisions."""
from datetime import datetime, timezone
import base64
import fcntl
import json
from pathlib import Path
import uuid

STORE = Path(__file__).with_name('data') / 'jobs.json'
JOB_KEYS = {'job_name','customer_name','customer_phone','customer_email','customer_address','job_notes','job_status',
 'job_material','job_thickness','job_units','job_width','job_height','job_depth','job_shelves','job_clearance',
 'job_carcass_edging','job_door_material','job_door_thickness','job_door_edging','job_door_edges',
 'job_waste','job_hinge_brand','job_hinges_per_door','plates_included','job_hardware','job_labour','job_transport','job_markup','job_tax',
 'uploaded_accessories'}
PREFIXES = ('carcass_supplier_', 'back_supplier_', 'door_supplier_', 'hinge_price_', 'plate_price_', 'uploaded_qty_', 'render_', 'design_')

def is_job_key(key):
    return key not in ('render_create_video','design_scene_editor','design_openings_editor','_job_plan_import','_job_import_units') and (key in JOB_KEYS or key.startswith(PREFIXES))

def capture_state(state):
    return {k:v for k,v in state.items() if is_job_key(k)}

def load_jobs(path=None):
    path=Path(path or STORE)
    return json.loads(path.read_text()) if path.exists() else {'jobs':[]}

def save_job(name, state, snapshot, pdf, cutting_csv, job_id=None, path=None):
    name=name.strip()
    if not name: raise ValueError('Enter a job name before saving.')
    if not pdf.startswith(b'%PDF'): raise ValueError('A generated PDF quotation is required.')
    # Reject unsupported/non-finite values before touching persistent state.
    json.dumps({'state':state,'snapshot':snapshot},allow_nan=False)
    path=Path(path or STORE);path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix('.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        data=load_jobs(path)
        if job_id:
            job=next((j for j in data['jobs'] if j['id']==job_id),None)
            if job is None: raise ValueError('Saved job was not found. Save as a new job instead.')
        else:
            job={'id':str(uuid.uuid4()),'created_utc':datetime.now(timezone.utc).isoformat(),'revisions':[]}
            data['jobs'].append(job)
        revision={'number':len(job['revisions'])+1,'saved_utc':datetime.now(timezone.utc).isoformat(),
                  'name':name,'state':state,'snapshot':snapshot,
                  'pdf_base64':base64.b64encode(pdf).decode('ascii'),'cutting_csv':cutting_csv}
        job['name']=name;job['updated_utc']=revision['saved_utc'];job['revisions'].append(revision)
        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2,allow_nan=False));temp.replace(path)
        return job['id'],revision['number']

def restore_revision(state, job_id, revision):
    for key in list(state):
        if is_job_key(key) or key in ('blum_accessories','_job_manual_accessories','_job_supplier_snapshot','_job_scene_rows','_job_layout','_job_room_openings','design_scene_editor','design_openings_editor','_job_plan_import','_job_import_units','_assistant_proposal','assistant_prompt'):
            del state[key]
    for key,value in revision['state'].items():
        if is_job_key(key): state[key]=value
    state['_active_job_id']=job_id
    state['_active_revision']=revision['number']
    state['_job_supplier_snapshot']=revision['snapshot']['supplier_products']
    state['_job_manual_accessories']=revision['snapshot']['manual_accessories']
    state['_job_plan_import']=revision['snapshot'].get('plan_import')
    state['_job_import_units']=revision['snapshot'].get('plan_pending_units',[])
    state['_job_layout']=revision['snapshot'].get('layout')
    state['_job_room_openings']=revision['snapshot'].get('layout',{}).get('openings',[]) if revision['snapshot'].get('layout') else []
    state['_job_scene_rows']=revision['snapshot'].get('design_views',{}).get('scene_rows',[])

def clear_job(state):
    for key in list(state):
        if is_job_key(key) or key in ('blum_accessories','_job_manual_accessories','_job_supplier_snapshot','_active_job_id','_active_revision','_job_scene_rows','_job_layout','_job_room_openings','design_scene_editor','design_openings_editor','_job_plan_import','_job_import_units','_assistant_proposal','assistant_prompt'):
            del state[key]
