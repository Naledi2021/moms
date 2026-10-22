import unittest
import tempfile
import json
from pathlib import Path
from materials import CATEGORIES,save_material,load_materials,restore_material_library,details
from catalogue_placement import place_product
from layout_ui import scene_boxes

class CatalogueTests(unittest.TestCase):
 def record(self,category):
  return dict(name='Test '+category,category=category,thickness_mm=3,color='#123456',finish='Matte',supplier='Supplier',price_m2=None,price_each=125,width_mm=300,height_mm=200,depth_mm=100,sku='ABC',notes='Verify clearances')
 def test_all_categories_save_edit_restore(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'library.json'
   for category in CATEGORIES:save_material(self.record(category),path)
   original=load_materials(path)
   item=original['materials'][-1];item['price_each']=250;save_material(item,path)
   self.assertEqual(load_materials(path)['materials'][-1]['price_each'],250)
   restored=Path(directory)/'restored.json';restore_material_library(json.dumps(load_materials(path)),restored)
   self.assertEqual(load_materials(restored),load_materials(path))
 def test_snapshot_placement_rendering_bounds_and_lock(self):
  layout=dict(length=3000,width=3000,height=2400,openings=[],walls=[])
  for category in CATEGORIES:
   record=self.record(category);original=[]
   rows=place_product(record,layout,original,x=100,y=200,z=900)
   record['color']='#ffffff';self.assertEqual(details(rows[0])['materials']['Carcass']['color'],'#123456')
   self.assertEqual(original,[])
   boxes=scene_boxes(rows,layout,18,0,18,False)
   self.assertTrue(boxes);self.assertEqual(boxes[0].colour,'#123456')
   with self.assertRaises(ValueError):place_product(record,layout,rows,lock={'approved':True})
   with self.assertRaises(ValueError):place_product(record,layout,rows,x=2999)
 def test_streamlit_create_and_place_product(self):
  from unittest.mock import patch
  from streamlit.testing.v1 import AppTest
  with tempfile.TemporaryDirectory() as directory,patch('materials.STORE',Path(directory)/'materials.json'):
   app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=15).run()
   app.selectbox(key='library_category_filter').set_value('Sink').run()
   name=next(n for n in app.text_input if n.label=='Material name');name.set_value('Test sink')
   next(n for n in app.button if n.label=='Save material to library').click().run()
   self.assertFalse(app.exception,[e.message for e in app.exception])
   self.assertEqual(load_materials()['materials'][-1]['category'],'Sink')
   app.button(key='confirm_room_layout').click().run()
   app.selectbox(key='product_placement_category').set_value('Sink').run()
   next(n for n in app.button if n.label=='Place library product').click().run()
   self.assertFalse(app.exception,[e.message for e in app.exception])
   row=app.session_state['_job_scene_rows'][-1]
   self.assertEqual(row['Name'],'Test sink')
   self.assertEqual(details(row)['catalogue_category'],'Sink')
 def test_invalid_backup_does_not_mutate_library(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'library.json';record=self.record('Sink');save_material(record,path)
   before=path.read_bytes();record.update(id='bad',width_mm=float('nan'))
   with self.assertRaises(ValueError):restore_material_library(json.dumps({'materials':[record]}),path)
   self.assertEqual(before,path.read_bytes())

if __name__=='__main__':unittest.main()
