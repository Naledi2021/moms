import unittest
from copy import deepcopy
from pathlib import Path
from streamlit.testing.v1 import AppTest
from room_actions import correct_wall,add_feature

class WallCorrectionTests(unittest.TestCase):
 def test_explicit_correction_relocks_and_preserves_other_walls(self):
  layout=dict(length=3000,width=3000,height=2400,openings=[])
  _,walls=add_feature(layout,[],[],'Wall',dict(x=500,y=500,length=1000,angle=0,thickness=110))
  _,walls=add_feature(layout,[],walls,'Wall',dict(x=500,y=1800,length=1000,angle=0,thickness=110))
  before=deepcopy(walls)
  updated=correct_wall(layout,walls,0,1000,600,1200,90)
  self.assertEqual(updated[0]['End Y (mm)'],1800)
  self.assertEqual(updated[0]['End X (mm)'],1000)
  self.assertTrue(updated[0]['Locked']);self.assertEqual(updated[1],before[1]);self.assertEqual(walls,before)
  for args in [(2900,600,1200,0),(0,0,float('nan'),0),(0,0,10,0)]:
   with self.assertRaises(ValueError):correct_wall(layout,walls,0,*args)
  with self.assertRaises(ValueError):correct_wall(layout,walls,0,600,600,1200,0,lock={'approved':True})
 def test_form_correction_undo_and_confirmation(self):
  app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=15).run()
  app.button(key='add_room_wall').click().run()
  app.button(key='confirm_room_layout').click().run()
  original=deepcopy(app.session_state['_job_walls'])
  next(n for n in app.number_input if n.label=='Position Y (mm)').set_value(800)
  next(n for n in app.button if n.label=='Apply position and lock wall').click().run()
  self.assertFalse(app.exception,[e.message for e in app.exception])
  self.assertEqual(app.session_state['_job_walls'][0]['Start Y (mm)'],800)
  self.assertTrue(app.session_state['_job_walls'][0]['Locked'])
  self.assertNotIn('design_layout_signature',app.session_state)
  app.button(key='undo_wall_change').click().run()
  self.assertEqual(app.session_state['_job_walls'],original)
  self.assertTrue(app.button(key='undo_wall_change').disabled)
  self.assertFalse(app.exception,[e.message for e in app.exception])

if __name__=='__main__':unittest.main()
