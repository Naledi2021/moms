import unittest
from unittest.mock import patch
from pathlib import Path
from streamlit.testing.v1 import AppTest
from unit_library import LIBRARY,library_row,unit_geometry
from layout_ui import validate_layout,scene_preview
from design_assistant import validate_proposal,plan_rows,ask_ai

class LibraryTests(unittest.TestCase):
    def setUp(self):self.layout=validate_layout(3000,3000,2400,[])

    def test_multiple_additions_are_separate_and_all_visible(self):
        rows=[]
        for kind in ('Single door base','Sink base','Three drawer base'):
            rows.append(library_row(kind,LIBRARY[kind]['width'],720,500,rows,self.layout))
        self.assertEqual([r['X (mm)'] for r in rows],[0,600,1500])
        boxes,warnings,valid=scene_preview(rows,self.layout,18,0,18,False)
        self.assertEqual(len(valid),3);self.assertFalse(warnings)
        for row in rows:self.assertTrue(any(b.name.startswith(row['Name']+' — ') for b in boxes))

    def test_invalid_row_does_not_hide_valid_rows(self):
        a=library_row('Single door base',600,720,500,[],self.layout)
        bad=dict(a,Name='Bad');bad['X (mm)']=9000
        b=library_row('Sink base',900,720,500,[a],self.layout)
        boxes,warnings,valid=scene_preview([a,bad,b],self.layout,18,0,18,False)
        self.assertEqual(len(valid),2);self.assertIn('Row 2',warnings[0]);self.assertTrue(boxes)
        bad['X (mm)']=None
        self.assertEqual(len(scene_preview([bad,a],self.layout,18,0,18,False)[2]),1)

    def test_types_have_distinct_fronts_and_open_drawers_stay_visible(self):
        for kind,spec in LIBRARY.items():
            if spec['category']!='Base':continue
            boxes=unit_geometry(kind,spec['width'],720,500,18,spec['shelves'],0,18)
            front=[b for b in boxes if b.kind=='door']
            expected={'Double door base':2,'Sink base':2,'Three drawer base':3,'Two drawer base':2,'Open shelf base':0,'Oven base':2}.get(kind,1)
            self.assertEqual(len(front),expected,kind)
        row=library_row('Three drawer base',600,720,500,[],self.layout)
        boxes,warnings,valid=scene_preview([row],self.layout,18,0,18,True)
        self.assertFalse(warnings);self.assertEqual(len(valid),1)
        self.assertTrue(any(b.origin[1]<-100 for b in boxes if b.kind=='door'))

    def test_overlapping_saved_units_are_reported(self):
        row=library_row('Single door base',600,720,500,[],self.layout)
        boxes,warnings,valid=scene_preview([row,dict(row,Name='Second')],self.layout,18,0,18,False)
        self.assertEqual(len(valid),2);self.assertTrue(any('overlaps' in w for w in warnings))

    def test_ai_proposals_validated_and_append_without_overwriting(self):
        proposal=validate_proposal({'answer':'Review these units','units':[{'type':'Sink base','width':900,'height':720,'depth':500}]})
        row=library_row('Single door base',600,720,500,[],self.layout)
        planned=plan_rows(proposal,[row],self.layout)
        self.assertEqual(planned[0],row);self.assertEqual(planned[1]['X (mm)'],600)
        for unit in ({'type':'Invented'},{'type':'Sink base','width':float('nan')}):
            with self.assertRaises(ValueError):validate_proposal({'answer':'bad','units':[unit]})
        with self.assertRaises(ValueError):plan_rows(validate_proposal({'answer':'wide','units':[{'type':'Sink base','width':2400}]*5}),[row],self.layout)

    def test_ai_service_payload_and_response(self):
        with patch('design_assistant.requests.post') as post:
            post.return_value.ok=True
            post.return_value.json.return_value={'choices':[{'message':{'content':'{"answer":"Use a sink base","units":[{"type":"Sink base","width":900}]}'}}]}
            result=ask_ai('Suggest a sink base',self.layout,[],[],'fake-test-key')
            self.assertEqual(result['units'][0]['height'],720)
            payload=post.call_args.kwargs['json']
            self.assertEqual(payload['response_format'],{'type':'json_object'})
            self.assertNotIn('customer_email',str(payload))

    def test_library_ui_adds_two_distinct_units_and_renders_all_views(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run()
        app.button(key='confirm_room_layout').click().run()
        app.button(key='add_library_unit').click().run()
        app.selectbox(key='library_selection').set_value('Three drawer base').run()
        app.button(key='add_library_unit').click().run()
        self.assertFalse(app.exception,[e.message for e in app.exception])
        rows=next(table.value for table in app.dataframe if 'X (mm)' in table.value.columns).to_dict(orient='records')
        self.assertEqual(len(rows),2);self.assertNotEqual(rows[0]['X (mm)'],rows[1]['X (mm)'])
        for mode in ('Lines','Sketch','3D','Ultra'):
            app.radio(key='render_mode').set_value(mode).run()
            self.assertFalse(app.exception,[e.message for e in app.exception])
        self.assertTrue(any('Previewing 2 of 2' in n.value for n in app.info))

    def test_ai_ui_requires_review_and_applies_without_losing_existing_unit(self):
        import os
        with patch.dict(os.environ,{'KITCHEN_AI_API_KEY':'fake-test-key'}),patch('design_assistant.ask_ai',return_value={'answer':'Review a sink unit','units':[{'type':'Sink base','width':900,'height':720,'depth':500}]}):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run()
            app.button(key='confirm_room_layout').click().run()
            app.button(key='add_library_unit').click().run()
            app.text_area(key='assistant_prompt').set_value('Add a sink base').run()
            app.button(key='assistant_ask').click().run()
            self.assertFalse(app.exception,[e.message for e in app.exception])
            rows=next(table.value for table in app.dataframe if 'X (mm)' in table.value.columns)
            self.assertEqual(len(rows),1)
            app.button(key='assistant_apply').click().run()
            self.assertFalse(app.exception,[e.message for e in app.exception])
            rows=next(table.value for table in app.dataframe if 'X (mm)' in table.value.columns)
            self.assertEqual(len(rows),2);self.assertEqual(rows.iloc[1]['Type'],'Sink base')

if __name__=='__main__':unittest.main()
