from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import jobs,workshop_defaults
from workshop_defaults import BUILTIN,load_workshop,save_workshop,seed_workshop,catalogue_for_settings
from calculator import cabinet_parts
from designer_geometry import apply_event,fingerprint
from layout_ui import validate_layout

class WorkshopDefaultsTests(unittest.TestCase):
 def test_side_thickness_is_automatic_at_every_supported_size(self):
  for thickness,expected in ((16,568),(18,564),(22.5,555)):
   parts=cabinet_parts(600,720,500,thickness,1,0)
   self.assertEqual(next(p for p in parts if p.name=='Internal shelf').length_mm,expected)
   self.assertEqual(next(p for p in parts if p.name=='Bottom').length_mm,expected)
  self.assertEqual(next(p for p in cabinet_parts(600,720,500,16,1,2) if p.name=='Internal shelf').length_mm,566)

 def test_defaults_persist_seed_only_missing_and_never_copy_customers(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'defaults.json';save_workshop(dict(BUILTIN,job_thickness=16.,job_depth=550.),path)
   data=load_workshop(path);state={'job_clearance':2.};seed_workshop(state,data)
   self.assertEqual(state['job_thickness'],16);self.assertEqual(state['job_clearance'],2)
   self.assertNotIn('customer_name',state)
   before=path.read_bytes()
   with self.assertRaises(ValueError):save_workshop({'job_clearance':float('nan')},path)
   self.assertEqual(path.read_bytes(),before)

 def test_palette_uses_standard_base_dimensions_without_changing_tall_units(self):
  catalogue=catalogue_for_settings(dict(BUILTIN,job_height=740.,job_depth=550.,job_shelves=2))
  self.assertEqual(catalogue['Single door base']['height'],740)
  self.assertEqual(catalogue['Tall pantry']['height'],2100)
  layout=validate_layout(3000,3000,2400,[])
  result=apply_event([],layout,{'action':'add','unit_type':'Single door base','revision':fingerprint(layout,[])},presets=catalogue)
  self.assertEqual(result[0]['Depth (mm)'],550);self.assertEqual(result[0]['Shelves'],2)

 def test_saved_job_does_not_change_when_workshop_defaults_change(self):
  with tempfile.TemporaryDirectory() as directory,patch.object(workshop_defaults,'STORE',Path(directory)/'workshop.json'),patch.object(jobs,'STORE',Path(directory)/'jobs.json'):
   save_workshop(dict(BUILTIN,job_thickness=16.,job_door_thickness=16.))
   app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=10).run()
   app.button(key='confirm_room_layout').click().run()
   self.assertEqual(app.selectbox(key='job_thickness').value,16)
   self.assertEqual(app.number_input(key='job_clearance').value,0)
   self.assertTrue(any('600 − 16 − 16 = 568' in text.value for text in app.caption))
   app.number_input(key='job_clearance').set_value(32.).run()
   self.assertTrue(app.button(key='clear_duplicate_clearance'))
   app.button(key='clear_duplicate_clearance').click().run()
   self.assertEqual(app.number_input(key='job_clearance').value,0)
   app.selectbox(key='assistant_style').set_value('Luxury contemporary').run()
   app.button(key='assistant_example').click().run()
   self.assertIn('Design a practical luxury kitchen',app.text_area(key='assistant_prompt').value)
   app.button(key='save_job').click().run()
   app.selectbox(key='job_thickness').set_value(18.).run()
   app.button(key='save_workshop_defaults').click().run()
   self.assertEqual(load_workshop()['settings']['job_thickness'],18)
   app.button(key='new_job').click().run();app.button(key='confirm_room_layout').click().run()
   self.assertEqual(app.selectbox(key='job_thickness').value,18)
   app.button(key='open_saved_job').click().run()
   self.assertEqual(app.selectbox(key='job_thickness').value,16)
   self.assertEqual(app.selectbox(key='assistant_style').value,'Luxury contemporary')
   self.assertFalse(app.exception,[e.message for e in app.exception])

if __name__=='__main__':unittest.main()
