import unittest
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import tempfile
from PIL import Image
from streamlit.testing.v1 import AppTest
from room_lock import freeze_room,check_room_lock
from jobs import save_job,load_jobs,restore_revision,clear_job
from plan_import import plan_reference_image

class RoomFreezeTests(unittest.TestCase):
 def room(self):return dict(length=4000.,width=3000.,height=2400.,wall_thickness=110.,walls=[],openings=[{'Type':'Window','Wall':'Left','Offset (mm)':1000.,'Width (mm)':1000.,'Height (mm)':600.,'Sill (mm)':900.}])
 def test_frozen_geometry_detects_changes_and_copies(self):
  room=self.room();frozen=freeze_room(room)
  check_room_lock(frozen,room)
  room['openings'][0]['Width (mm)']=900
  self.assertEqual(frozen['layout']['openings'][0]['Width (mm)'],1000)
  with self.assertRaises(ValueError):check_room_lock(frozen,room)
 def test_source_and_freeze_survive_revision_restore(self):
  room=self.room();lock=freeze_room(room)
  source={'filename':'plan.png','text':'4000 mm','reference_image_base64':'sample'}
  snapshot=dict(layout=room,room_lock=lock,plan_import=source,supplier_products=[],manual_accessories=[],design_views={'scene_rows':[]})
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'jobs.json'
   identity,_=save_job('Test',{},snapshot,b'%PDF-1.4','',path=path)
   state={};restore_revision(state,identity,load_jobs(path)['jobs'][0]['revisions'][0])
   self.assertEqual(state['_room_lock'],lock);self.assertEqual(state['_job_plan_import'],source)
   state['_job_scene_rows']=[{'Name':'Cabinet placed after freezing'}]
   check_room_lock(state['_room_lock'],state['_job_layout'])
   bad=deepcopy(snapshot);bad['layout']['length']=5000
   with self.assertRaises(ValueError):save_job('Invalid',{},bad,b'%PDF-1.4','',path=path)
   clear_job(state);self.assertNotIn('_room_lock',state)
 def test_frozen_ui_keeps_cabinet_placement_enabled(self):
  app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=15).run()
  app.button(key='confirm_room_layout').click().run()
  app.button(key='freeze_room_structure').click().run()
  self.assertFalse(app.exception,[e.message for e in app.exception])
  self.assertTrue(app.session_state['_room_lock'])
  self.assertFalse(any(n.key=='design_room_length' for n in app.number_input))
  self.assertFalse(app.button(key='add_design_item').disabled)
  app.button(key='add_design_item').click().run()
  self.assertEqual(len(app.session_state['_job_scene_rows']),1)
  app.checkbox(key='room_structure_unlock_confirmed').check().run()
  app.button(key='unlock_room_structure').click().run()
  self.assertNotIn('_room_lock',app.session_state)
  self.assertTrue(any(n.key=='design_room_length' for n in app.number_input))
 def test_reference_image_is_bounded(self):
  stream=BytesIO();Image.new('RGB',(2000,2000),'white').save(stream,format='PNG')
  import base64
  reference=plan_reference_image([stream.getvalue()]);image=Image.open(BytesIO(base64.b64decode(reference)))
  self.assertLessEqual(max(image.size),1000)
  self.assertIsNone(plan_reference_image([]))

if __name__=='__main__':unittest.main()
