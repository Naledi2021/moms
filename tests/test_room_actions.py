from copy import deepcopy
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
from layout_ui import validate_layout
from room_actions import add_feature,edit_wall,editor_rows
from room_geometry import WALL_COLUMNS

class RoomActionsTests(unittest.TestCase):
 def setUp(self):self.layout=dict(validate_layout(3000,3000,2400,[]),wall_thickness=110)
 def test_add_wall_by_length_and_direction_locked_by_default(self):
  openings,walls=add_feature(self.layout,[],[],'Wall',{'x':500,'y':500,'length':1500,'angle':90,'thickness':110})
  self.assertTrue(walls[0]['Locked']);self.assertEqual(walls[0]['End X (mm)'],500);self.assertEqual(walls[0]['End Y (mm)'],2000)
  with self.assertRaises(ValueError):add_feature(self.layout,[],[],'Wall',{'x':2500,'y':500,'length':1500,'angle':0,'thickness':110})
 def test_openings_validate_dimensions_and_keep_existing(self):
  values={'wall':'Front','offset':100,'length':900,'height':1000,'sill':900}
  openings,walls=add_feature(self.layout,[],[],'Window',values)
  self.assertEqual(openings[0]['Width (mm)'],900)
  doors,_=add_feature(self.layout,openings,walls,'Door',dict(values,wall='Back',height=2100,sill=0))
  self.assertEqual(len(doors),2);self.assertEqual(len(openings),1)
  with self.assertRaises(ValueError):add_feature(self.layout,openings,walls,'Window',values)
  with self.assertRaises(ValueError):add_feature(self.layout,[],[],'Window',dict(values,height=2000))
 def test_locked_walls_cannot_move_then_unlock_move_endpoints_and_relock(self):
  _,walls=add_feature(self.layout,[],[],'Wall',{'x':500,'y':500,'length':1000,'angle':0,'thickness':110})
  original=deepcopy(walls)
  with self.assertRaises(ValueError):edit_wall(self.layout,walls,0,delta=(100,100))
  walls[0]['Locked']=False
  moved=edit_wall(self.layout,walls,0,delta=(100,200))
  self.assertEqual(moved[0]['Start X (mm)'],600);self.assertEqual(moved[0]['End X (mm)'],1600)
  changed=edit_wall(self.layout,moved,0,end=(1800,1200))
  self.assertEqual(changed[0]['End Y (mm)'],1200)
  with self.assertRaises(ValueError):edit_wall(self.layout,changed,0,end=(5000,1200))
  changed[0]['Locked']=True
  with self.assertRaises(ValueError):edit_wall(self.layout,changed,0,delta=(10,10))
  self.assertEqual(original[0]['Start X (mm)'],500)
 def test_preserve_table_edits_and_design_lock(self):
  _,walls=add_feature(self.layout,[],[],'Wall',{'x':500,'y':500,'length':1000,'angle':0,'thickness':110})
  merged=editor_rows(walls,WALL_COLUMNS+['Locked'],{'edited_rows':{0:{'Locked':False}}})
  self.assertFalse(merged[0]['Locked'])
  with self.assertRaises(ValueError):edit_wall(self.layout,merged,0,delta=(10,10),lock={'approved':True})
  with self.assertRaises(ValueError):add_feature(self.layout,[],[],'Door',{},lock={'approved':True})
 def test_add_feature_forms_preserve_both_types_and_require_room_confirmation(self):
  app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=10).run()
  app.number_input(key='room_feature_wall_length').set_value(1200).run()
  app.button(key='add_room_wall').click().run()
  self.assertFalse(app.exception,[e.message for e in app.exception])
  app.radio(key='room_feature_kind').set_value('Window').run()
  app.button(key='add_room_window').click().run()
  app.button(key='confirm_room_layout').click().run()
  self.assertFalse(app.exception,[e.message for e in app.exception])
  layout=app.session_state['_job_layout'];self.assertEqual(len(layout['walls']),1);self.assertEqual(len(layout['openings']),1)
  self.assertTrue(layout['walls'][0]['Locked'])
  self.assertFalse(any(n.key=='confirm_room_layout' and n.disabled for n in app.button))

if __name__=='__main__':unittest.main()
