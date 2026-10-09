from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import jobs
from designer_geometry import (footprint,bounds,intersects,along_wall,snap_unit,collision_warnings,approve_design,apply_event,fingerprint)
from layout_ui import validate_layout,commit_scene
from unit_library import library_row,LIBRARY
from design_assistant import validate_proposal,plan_rows

class DesignerTests(unittest.TestCase):
    def setUp(self):
        self.layout=validate_layout(4000,3000,2400,[])
        self.row=library_row('Single door base',600,720,500,[],self.layout)
        self.row.update({'X (mm)':1000.,'Y (mm)':1000.})
    def event(self,rows,action,**changes):return dict(id='test-event',revision=fingerprint(self.layout,rows),index=0,action=action,**changes)

    def test_wall_placements_face_into_room_at_precise_offsets(self):
        expected={'Front':(250,0,850,500),'Back':(250,2500,850,3000),'Left':(0,250,500,850),'Right':(3500,250,4000,850)}
        for wall,box in expected.items():
            row=along_wall(self.row,wall,250,self.layout)
            for a,b in zip(bounds(row),box):self.assertAlmostEqual(a,b)
        with self.assertRaises(ValueError):along_wall(self.row,'Front',3800,self.layout)

    def test_move_rotation_and_delete_preserve_millimetres(self):
        rows=apply_event([self.row],self.layout,self.event([self.row],'move',x=1250.25,y=1110.75),snap=False)
        self.assertEqual(rows[0]['X (mm)'],1250.25)
        old=footprint(rows[0]);rotated=apply_event(rows,self.layout,self.event(rows,'rotate'))
        new=footprint(rotated[0]);self.assertEqual(rotated[0]['Rotation (deg)'],90)
        for axis in (0,1):self.assertAlmostEqual(sum(p[axis] for p in old),sum(p[axis] for p in new))
        self.assertEqual(apply_event(rotated,self.layout,self.event(rotated,'delete')),[])
        with self.assertRaises(ValueError):apply_event([self.row],self.layout,self.event([self.row],'move',x=-100,y=0),snap=False)

    def test_snaps_wall_neighbour_and_ignores_distant_or_elevated_unit(self):
        row=dict(self.row);row['X (mm)']=12.;row['Y (mm)']=10.
        snapped=snap_unit(row,[row],0,self.layout);self.assertEqual((snapped['X (mm)'],snapped['Y (mm)']),(0,0))
        neighbour=dict(self.row);neighbour['X (mm)']=0;neighbour['Y (mm)']=1000
        row=dict(self.row);row['X (mm)']=615
        self.assertEqual(snap_unit(row,[neighbour,row],1,self.layout)['X (mm)'],600)
        neighbour['Z (mm)']=1400
        self.assertEqual(snap_unit(row,[neighbour,row],1,self.layout)['X (mm)'],615)

    def test_rotated_polygon_collision_not_bounding_box_false_positive(self):
        a=dict(self.row);a.update({'Width (mm)':1000,'Depth (mm)':100,'Rotation (deg)':45})
        b=dict(a);b['Y (mm)']=1300
        self.assertFalse(intersects(footprint(a),footprint(b)))
        b['Y (mm)']=1020
        self.assertTrue(intersects(footprint(a),footprint(b)))
        self.assertTrue(any('overlaps' in text for text in collision_warnings([a,b],self.layout)))
        b['Z (mm)']=1400
        self.assertFalse(collision_warnings([a,b],self.layout))

    def test_openings_check_all_walls_and_elevation(self):
        for wall in ('Front','Back','Left','Right'):
            opening={'Type':'Door','Wall':wall,'Offset (mm)':200,'Width (mm)':900,'Height (mm)':2100,'Sill (mm)':0}
            layout=validate_layout(4000,3000,2400,[opening]);row=along_wall(self.row,wall,250,layout)
            self.assertTrue(any('door' in x for x in collision_warnings([row],layout)))
            window=dict(opening,Type='Window',**{'Height (mm)':900,'Sill (mm)':1000})
            layout=validate_layout(4000,3000,2400,[window])
            self.assertFalse(collision_warnings([row],layout))
            row['Z (mm)']=1400
            self.assertTrue(any('window' in x for x in collision_warnings([row],layout)))

    def test_approval_rejects_collisions_and_guards_all_event_types(self):
        lock=approve_design(self.layout,[self.row])
        for action in ('move','rotate','delete'):
            with self.assertRaises(ValueError):apply_event([self.row],self.layout,self.event([self.row],action,x=1200,y=1200),lock)
        with self.assertRaises(ValueError):approve_design(self.layout,[self.row,dict(self.row,Name='overlap')])
        stale=self.event([self.row],'delete');stale['revision']='old'
        with self.assertRaises(ValueError):apply_event([self.row],self.layout,stale)
        proposal=validate_proposal({'answer':'review','units':[{'type':'Sink base','width':900,'wall':'Back','offset':0}]})
        with self.assertRaises(ValueError):plan_rows(proposal,[self.row],self.layout,lock)
        planned=plan_rows(proposal,[self.row],self.layout)
        self.assertEqual(bounds(planned[-1]),(0,2500,900,3000))

    def test_categories_and_vertical_stacking(self):
        self.assertEqual({s['category'] for s in LIBRARY.values()},{'Base','Wall','Tall','Corner'})
        base=library_row('Single door base',600,720,500,[],self.layout)
        wall=library_row('Single door wall',600,720,320,[base],self.layout)
        self.assertEqual(base['X (mm)'],wall['X (mm)']);self.assertEqual(wall['Z (mm)'],1400)
        self.assertFalse(collision_warnings([base,wall],self.layout))

    def test_save_restore_precision_openings_and_approval_without_migration(self):
        opening={'Type':'Window','Wall':'Back','Offset (mm)':150.25,'Width (mm)':800.5,'Height (mm)':900,'Sill (mm)':1000}
        layout=validate_layout(4000.5,3000.25,2400,[opening]);row=dict(self.row);row['X (mm)']=1000.125
        lock=approve_design(layout,[row])
        snapshot={'layout':layout,'design_views':{'scene_rows':[row]},'design_lock':lock,'supplier_products':[],'manual_accessories':[]}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'jobs.json'
            key,_=jobs.save_job('Precise design',{},snapshot,b'%PDF-test','csv',path=path)
            revision=jobs.load_jobs(path)['jobs'][0]['revisions'][0];state={};jobs.restore_revision(state,key,revision)
            self.assertEqual(state['_job_scene_rows'],[row]);self.assertEqual(state['_design_lock'],lock);self.assertEqual(state['_job_room_openings'],[opening])
            changed=deepcopy(snapshot);changed['design_views']['scene_rows'][0]['X (mm)']+=1
            with self.assertRaises(ValueError):jobs.save_job('changed',{},changed,b'%PDF-test','csv',key,path=path)
            self.assertEqual(len(jobs.load_jobs(path)['jobs'][0]['revisions']),1)
            jobs.clear_job(state);self.assertNotIn('_design_lock',state)
            old=deepcopy(revision);old['snapshot'].pop('design_lock');jobs.restore_revision(state,key,old);self.assertIsNone(state['_design_lock'])

    def test_ui_lock_save_reopen_and_explicit_unlock(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(jobs,'STORE',Path(directory)/'jobs.json'):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run()
            app.number_input(key='design_room_length').set_value(3500).run()
            app.button(key='confirm_room_layout').click().run()
            app.button(key='add_library_unit').click().run()
            app.button(key='approve_design').click().run()
            self.assertFalse(app.exception,[x.message for x in app.exception])
            self.assertTrue(app.button(key='add_library_unit').disabled)
            self.assertTrue(app.button(key='unlock_design').disabled)
            app.button(key='save_job').click().run()
            self.assertFalse(app.exception,[x.message for x in app.exception])
            self.assertTrue(jobs.load_jobs()['jobs'][0]['revisions'][0]['snapshot']['design_lock'])
            app.button(key='new_job').click().run();app.button(key='open_saved_job').click().run()
            self.assertTrue(app.button(key='add_library_unit').disabled)
            app.checkbox(key='unlock_confirmed').check().run();app.button(key='unlock_design').click().run()
            self.assertFalse(app.exception,[x.message for x in app.exception])
            self.assertEqual(app.number_input(key='design_room_length').value,3500)
            self.assertFalse(app.button(key='add_library_unit').disabled)

    def test_backup_restore_preserves_revisions_and_rejects_conflicts(self):
        import json
        snapshot={'supplier_products':[],'manual_accessories':[],'pricing_status':'test','total':0,'layout':self.layout,'design_views':{'scene_rows':[self.row]}}
        with tempfile.TemporaryDirectory() as directory:
            original=Path(directory)/'original.json';restored=Path(directory)/'restored.json'
            key,_=jobs.save_job('Backup',{},snapshot,b'%PDF-test','csv',path=original)
            jobs.save_job('Backup revision',{},snapshot,b'%PDF-test','csv',key,path=original)
            archive=jobs.load_jobs(original)['jobs'][0]
            self.assertTrue(jobs.import_job_history(json.dumps(archive).encode(),restored))
            self.assertEqual(jobs.load_jobs(restored)['jobs'][0],archive)
            self.assertFalse(jobs.import_job_history(json.dumps(archive).encode(),restored))
            changed=deepcopy(archive);changed['revisions'][0]['name']='Changed'
            with self.assertRaises(ValueError):jobs.import_job_history(json.dumps(changed).encode(),restored)
            self.assertEqual(jobs.load_jobs(restored)['jobs'][0],archive)

    def test_ai_suggestions_remain_read_only_when_locked(self):
        import os
        with patch.dict(os.environ,{'KITCHEN_AI_API_KEY':'test-only'}),patch('design_assistant.ask_ai',return_value={'answer':'Review','units':[{'type':'Sink base','width':900,'height':720,'depth':500}]}):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run()
            app.button(key='confirm_room_layout').click().run();app.button(key='add_library_unit').click().run()
            app.button(key='approve_design').click().run()
            app.text_area(key='assistant_prompt').set_value('Suggest another unit').run()
            app.button(key='assistant_ask').click().run()
            self.assertFalse(app.exception,[x.message for x in app.exception])
            self.assertTrue(app.button(key='assistant_apply').disabled)

if __name__=='__main__':unittest.main()
