import unittest
import tempfile
from pathlib import Path
from copy import deepcopy
from streamlit.testing.v1 import AppTest
from plan_import import single_measurements,reviewed_room

TEXT='4000 mm\n600 mm\n2800 mm (Door)\n1000 mm (Window)\n600 mm high\n3000 mm'

class PlanRoomTests(unittest.TestCase):
 def test_scalar_measurements_preserve_labels_and_units(self):
  self.assertEqual([r['mm'] for r in single_measurements(TEXT)],[4000,600,2800,1000,600,3000])
  self.assertIn('Door',single_measurements(TEXT)[2]['context'])
  self.assertEqual([r['mm'] for r in single_measurements('4 m 300 cm 600 MM')],[4000,3000,600])
 def test_room_openings_bounds_locks_and_no_partial_mutation(self):
  openings=[{'Type':'Door','Wall':'Front','Offset (mm)':600,'Width (mm)':2800,'Height (mm)':2100,'Sill (mm)':0},
   {'Type':'Window','Wall':'Left','Offset (mm)':1000,'Width (mm)':1000,'Height (mm)':600,'Sill (mm)':1000}]
  before=deepcopy(openings)
  room=reviewed_room({},4000,3000,2400,openings,[])
  self.assertEqual(len(room['openings']),2);self.assertEqual(room['length'],4000)
  self.assertEqual(openings,before)
  with self.assertRaises(ValueError):reviewed_room({},4000,3000,2400,openings,[],lock={'approved':True})
  with self.assertRaises(ValueError):reviewed_room({},3000,3000,2400,openings,[])
  with self.assertRaises(ValueError):reviewed_room({},4000,3000,1500,openings,[])
  with self.assertRaises(ValueError):reviewed_room({},400,3000,2400,[],[])
  bad=deepcopy(openings);bad[0]['Sill (mm)']=100
  with self.assertRaises(ValueError):reviewed_room({},4000,3000,2400,bad,[])
 def test_builder_creates_editable_geometry_and_preserves_units(self):
  script="""import streamlit as st
from plan_layout_ui import render_plan_layout
from layout_ui import render_room_layout
st.session_state.setdefault('_job_scene_rows',[{'Name':'Keep cabinet'}])
render_plan_layout({'digest':'test','filename':'floorplan.pdf'},%r)
render_room_layout()
"""%TEXT
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'builder.py';path.write_text(script)
   app=AppTest.from_file(str(path),default_timeout=15).run()
   app.selectbox(key='plan_room_length_source').set_value(0).run()
   app.selectbox(key='plan_room_depth_source').set_value(5).run()
   app.number_input(key='plan_room_height').set_value(2400).run()
   app.selectbox(key='plan_opening_width_source').set_value(2).run()
   app.number_input(key='plan_opening_offset').set_value(600)
   app.number_input(key='plan_opening_height').set_value(2100)
   app.button(key='plan_stage_opening').click().run()
   self.assertEqual(len(app.session_state['_plan_layout_openings']),1)
   app.selectbox(key='plan_opening_type').set_value('Window').run()
   app.selectbox(key='plan_opening_wall').set_value('Left').run()
   app.selectbox(key='plan_opening_width_source').set_value(3).run()
   app.number_input(key='plan_opening_offset').set_value(1000)
   app.number_input(key='plan_opening_height').set_value(600)
   app.number_input(key='plan_opening_sill').set_value(900)
   app.button(key='plan_stage_opening').click().run()
   self.assertEqual(len(app.session_state['_plan_layout_openings']),2)
   verify=next(c for c in app.checkbox if c.key.startswith('plan_geometry_verified_'))
   verify.check().run()
   app.button(key='plan_create_room').click().run()
   self.assertFalse(app.exception,[e.message for e in app.exception])
   self.assertEqual(app.session_state['design_room_length'],4000)
   self.assertEqual(app.session_state['_job_scene_rows'],[{'Name':'Keep cabinet'}])
   app.button(key='confirm_room_layout').click().run()
   self.assertEqual(app.session_state['_job_layout']['openings'][0]['Width (mm)'],2800)
   self.assertEqual(app.session_state['_job_layout']['length'],4000)
   self.assertEqual(app.session_state['_job_layout']['openings'][1]['Sill (mm)'],900)

if __name__=='__main__':unittest.main()
