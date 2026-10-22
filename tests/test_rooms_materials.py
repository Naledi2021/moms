from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import materials,jobs
from materials import save_material,load_materials,details
from room_geometry import room_wall_boxes,wall_box,worktop_rectangles,validate_walls
from designer_geometry import collision_warnings,approve_design,floor_plan_svg,unit_polygons
from layout_ui import scene_boxes,validate_layout


def rect(x,y,w,d):return dict(zip(['X (mm)','Y (mm)','Width (mm)','Depth (mm)'],[x,y,w,d]))
def row(kind='Worktop'):
 return {'Name':'Test unit','Type':kind,'Width (mm)':2000.,'Height (mm)':30.,'Depth (mm)':2000.,'X (mm)':200.,'Y (mm)':200.,'Z (mm)':720.,'Rotation (deg)':0.,'Shelves':0}

class RoomsMaterialsTests(unittest.TestCase):
 def setUp(self):self.layout=validate_layout(4000,3000,2700,[])

 def test_worktop_union_cutouts_and_hole_validation(self):
  config={'sections':[rect(0,0,2000,600),rect(0,0,600,2000)],'cutouts':[rect(100,800,300,400)]}
  tiles=worktop_rectangles(2000,2000,config)
  area=sum((b-a)*(d-c) for a,c,b,d in tiles)
  self.assertEqual(area,1920000.)
  with self.assertRaises(ValueError):worktop_rectangles(2000,2000,{'sections':config['sections'],'cutouts':[rect(1000,1000,300,400)]})
  with self.assertRaises(ValueError):worktop_rectangles(2000,2000,{'sections':[]})
  with self.assertRaises(ValueError):worktop_rectangles(2000,2000,{'sections':[rect(0,0,float('nan'),100)]})

 def test_worktop_solid_parts_render_and_collision_void_is_empty(self):
  top=row();top['Design details']=json.dumps({'worktop':{'sections':[rect(0,0,2000,600),rect(0,0,600,2000)],'cutouts':[]}})
  other=dict(row('Panel'),Name='In void',**{'Width (mm)':400,'Depth (mm)':400,'Height (mm)':30,'X (mm)':1200,'Y (mm)':1200})
  self.assertFalse(collision_warnings([top,other],self.layout))
  other['X (mm)']=300
  self.assertTrue(collision_warnings([top,other],self.layout))
  boxes=scene_boxes([top],self.layout,18,0,18,False)
  self.assertEqual(sum(b.size[0]*b.size[1] for b in boxes),2040000.)
  self.assertEqual(len(unit_polygons(top)),2)
  self.assertIn('Test unit',floor_plan_svg(self.layout,[top]))

 def test_material_library_persistence_and_snapshot_does_not_change(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'materials.json'
   record=save_material(dict(name='Quartz sample',category='Worktop',thickness_mm=30,color='#123456',finish='Gloss',supplier='My supplier',price_m2=1200),path)
   top=row();top['Design details']=json.dumps({'materials':{'Worktop':record}})
   save_material(dict(record,color='#ffffff',price_m2=1900),path)
   self.assertEqual(details(top)['materials']['Worktop']['price_m2'],1200)
   self.assertEqual(load_materials(path)['materials'][-1]['price_m2'],1900)
   boxes=scene_boxes([top],self.layout,18,0,18,False)
   self.assertEqual(boxes[0].colour,'#123456');self.assertEqual(boxes[0].finish,'Gloss')
   with self.assertRaises(ValueError):save_material(dict(record,thickness_mm=-1),path)

 def test_room_walls_use_height_and_leave_openings(self):
  self.layout['openings']=[{'Type':'Door','Wall':'Front','Offset (mm)':1000,'Width (mm)':900,'Height (mm)':2100,'Sill (mm)':0}]
  boxes=room_wall_boxes(self.layout)
  self.assertEqual(max(b.origin[2]+b.size[2] for b in boxes),2700)
  self.assertFalse(any(b.origin[0]<1400<b.origin[0]+b.size[0] and b.origin[2]<1000<b.origin[2]+b.size[2] for b in boxes if b.name.startswith('Front')))
  wall={'Name':'Partition','Start X (mm)':500,'Start Y (mm)':500,'End X (mm)':500,'End Y (mm)':2000,'Thickness (mm)':110}
  validate_walls([wall],self.layout);self.layout['walls']=[wall]
  unit=dict(row('Panel'),**{'X (mm)':450,'Y (mm)':700,'Width (mm)':200,'Depth (mm)':200})
  self.assertTrue(any('Partition' in warning for warning in collision_warnings([unit],self.layout)))
  self.assertEqual(wall_box(wall,2700).size[2],2700)
  with self.assertRaises(ValueError):validate_walls([dict(wall,**{'End X (mm)':9000})],self.layout)

 def test_saved_materials_worktops_walls_and_approval_round_trip(self):
  top=row();top['Design details']=json.dumps({'worktop':{'sections':[rect(0,0,2000,600)]},'materials':{'Worktop':materials.starter_materials()[2]}})
  self.layout['walls']=[{'Name':'Return','Start X (mm)':3500,'Start Y (mm)':0,'End X (mm)':3500,'End Y (mm)':1000,'Thickness (mm)':110}]
  lock=approve_design(self.layout,[top]);snapshot={'layout':self.layout,'design_views':{'scene_rows':[top]},'design_lock':lock,'supplier_products':[],'manual_accessories':[]}
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'jobs.json'
   key,_=jobs.save_job('Kitchen',{},snapshot,b'%PDF-test','csv',path=path)
   revision=jobs.load_jobs(path)['jobs'][0]['revisions'][0];state={};jobs.restore_revision(state,key,revision)
   self.assertEqual(state['_job_walls'],self.layout['walls']);self.assertEqual(details(state['_job_scene_rows'][0]),details(top));self.assertEqual(state['_design_lock'],lock)

 def test_worktop_ui_add_shape_material_save_and_reopen(self):
  with tempfile.TemporaryDirectory() as directory,patch.object(jobs,'STORE',Path(directory)/'jobs.json'),patch.object(materials,'STORE',Path(directory)/'materials.json'):
   app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=10).run()
   app.button(key='confirm_room_layout').click().run()
   app.button(key='add_custom_worktop').click().run()
   self.assertFalse(app.exception,[e.message for e in app.exception])
   # Increase depth to allow an L shape with substantial arms.
   next(n for n in app.number_input if n.label=='Depth (mm)').set_value(1800.).run()
   next(b for b in app.button if b.label=='Apply precise dimensions').click().run()
   next(s for s in app.selectbox if s.label=='Worktop starting shape').set_value('L shape').run()
   app.button(key='load_worktop_shape').click().run()
   next(s for s in app.selectbox if s.label=='Worktop material for this unit').set_value('sample-stone').run()
   app.button(key='apply_unit_materials').click().run()
   self.assertFalse(app.exception,[e.message for e in app.exception])
   app.button(key='save_job').click().run()
   revision=jobs.load_jobs()['jobs'][0]['revisions'][0]
   saved=revision['snapshot']['design_views']['scene_rows'][0]
   self.assertEqual(len(details(saved)['worktop']['sections']),2)
   self.assertEqual(details(saved)['materials']['Worktop']['id'],'sample-stone')
   app.button(key='new_job').click().run();app.button(key='open_saved_job').click().run()
   self.assertFalse(app.exception,[e.message for e in app.exception])
   self.assertEqual(details(app.session_state['_job_scene_rows'][0]),details(saved))

 def test_material_backup_restore_validates_before_writing(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'materials.json'
   sample=dict(materials.starter_materials()[0],id='custom',name='My new board')
   materials.restore_material_library(json.dumps({'materials':[sample]}).encode(),path)
   self.assertEqual(len(load_materials(path)['materials']),4)
   before=path.read_bytes()
   with self.assertRaises(ValueError):materials.restore_material_library(json.dumps({'materials':[dict(sample,thickness_mm=-5)]}).encode(),path)
   self.assertEqual(path.read_bytes(),before)

if __name__=='__main__':unittest.main()
