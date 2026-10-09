from dataclasses import asdict
from io import BytesIO
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image,ImageDraw,ImageFont
from reportlab.pdfgen import canvas
from streamlit.testing.v1 import AppTest
import jobs
import video_render
from rendering import cabinet_geometry,interactive_figure,sketch_svg
from layout_ui import validate_layout,scene_boxes
from plan_import import document_pages,local_ocr,measurement_candidates

APP=str(Path(__file__).resolve().parents[1]/'app.py')

class DesignTests(unittest.TestCase):
    def test_layout_gates_units_and_requires_reconfirmation(self):
        app=AppTest.from_file(APP).run()
        self.assertFalse(app.exception)
        self.assertFalse(any(n.key=='job_width' for n in app.number_input))
        app.button(key='confirm_room_layout').click().run()
        self.assertFalse(app.exception)
        app.button(key='add_design_item').click().run()
        self.assertFalse(app.exception,[e.message for e in app.exception])
        for mode in ('Lines','Sketch','3D','Ultra'):
            app.radio(key='render_mode').set_value(mode).run()
            self.assertFalse(app.exception,[e.message for e in app.exception])
        app.number_input(key='design_room_length').set_value(3500).run()
        self.assertFalse(any(n.key=='job_width' for n in app.number_input))
        self.assertFalse(any(b.key=='add_design_item' for b in app.button))

    def test_scene_geometry_and_opening_validation(self):
        layout=validate_layout(3000,3000,2400,[])
        row={'Name':'Base','Type':'Base cabinet','Width (mm)':600,'Height (mm)':720,'Depth (mm)':500,'X (mm)':600,'Y (mm)':600,'Z (mm)':0,'Rotation (deg)':90,'Shelves':1}
        boxes=scene_boxes([row],layout,18,0,18,True)
        self.assertEqual(len(boxes),8)
        self.assertAlmostEqual(boxes[0].origin[0],600)
        self.assertIn('<svg',sketch_svg(boxes))
        self.assertTrue(interactive_figure(boxes,ultra=True,finish='Wood grain').data)
        bad={'Type':'Window','Wall':'Front','Offset (mm)':2900,'Width (mm)':500,'Height (mm)':1000,'Sill (mm)':900}
        with self.assertRaises(ValueError):validate_layout(3000,3000,2400,[bad])

    def test_actual_mp4_generation_for_multiple_scene_items(self):
        boxes=cabinet_geometry(600,720,500,18,1,0,18)
        # A second item exercises whole-design rather than single-cabinet animation.
        from rendering import Box
        boxes.append(Box('Worktop',(0,0,740),(1200,600,30),'panel'))
        settings=dict(width=600,height=720,depth=500,thickness=18,shelves=1,clearance=0,door_thickness=18,open_door=False,carcass_colour='#eeeae2',door_colour='#b88a55',finish='Matte',hardware=False,hinges=2,seconds=3,format='Square',scene=[asdict(b) for b in boxes])
        with tempfile.TemporaryDirectory() as directory,patch.object(video_render,'ROOT',Path(directory)):
            path=video_render.create_video(settings)
            probe=subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_name,width,height,nb_frames','-show_entries','format=duration','-of','json',str(path)],capture_output=True,text=True,check=True)
            data=json.loads(probe.stdout)
            self.assertEqual(data['streams'][0]['codec_name'],'h264')
            self.assertEqual(int(data['streams'][0]['nb_frames']),72)
            self.assertAlmostEqual(float(data['format']['duration']),3,places=1)
            self.assertEqual(video_render.create_video(settings),path)

    def test_pdf_text_and_real_local_ocr(self):
        output=BytesIO();pdf=canvas.Canvas(output);pdf.drawString(60,750,'Room 3000 x 4000 x 2400 mm');pdf.save()
        text,pages=document_pages(output.getvalue(),'plan.pdf')
        self.assertIn('3000',text);self.assertEqual(len(pages),1)
        self.assertEqual(measurement_candidates(text)[0]['values'],[3000,4000,2400])
        image=Image.new('RGB',(1500,300),'white');draw=ImageDraw.Draw(image)
        font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',48)
        draw.text((50,70),'Room 3000 x 4000 x 2400 mm',fill='black',font=font)
        out=BytesIO();image.save(out,format='PNG')
        _,images=document_pages(out.getvalue(),'sketch.png')
        ocr=local_ocr(images)
        self.assertIn('3000',ocr)
        self.assertEqual(measurement_candidates(ocr)[0]['values'],[3000,4000,2400])

    def test_reviewed_pdf_dimensions_require_confirmation(self):
        output=BytesIO();pdf=canvas.Canvas(output);pdf.drawString(60,750,'Room 3500 x 4000 x 2400 mm');pdf.save()
        class Upload(BytesIO):name='floor_plan.pdf'
        upload=Upload(output.getvalue())
        def file_uploader(label,*args,**kwargs):
            return upload if label=='Sketch or plan document' else None
        with patch('streamlit.file_uploader',side_effect=file_uploader):
            app=AppTest.from_file(APP).run()
            app.button(key='read_plan_document').click().run()
            self.assertFalse(app.exception,[e.message for e in app.exception])
            app.selectbox(key='plan_dimension_order').set_value('Room length × depth × height').run()
            self.assertTrue(app.button(key='apply_plan_dimensions').disabled)
            app.checkbox(key='plan_annotation_verified').check().run()
            app.button(key='apply_plan_dimensions').click().run()
            self.assertFalse(app.exception,[e.message for e in app.exception])
            self.assertEqual(app.number_input(key='design_room_length').value,3500)
            self.assertEqual(app.number_input(key='design_room_width').value,4000)
            self.assertFalse(any(n.key=='job_width' for n in app.number_input))
            app.button(key='confirm_room_layout').click().run()
            self.assertTrue(any(n.key=='job_width' for n in app.number_input))

    def test_saved_scene_and_video_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(jobs,'STORE',Path(directory)/'jobs.json'):
            app=AppTest.from_file(APP).run()
            app.button(key='confirm_room_layout').click().run()
            app.button(key='add_design_item').click().run()
            app.radio(key='render_mode').set_value('Ultra').run()
            self.assertFalse(app.exception)
            app.button(key='save_job').click().run()
            self.assertFalse(app.exception)
            revision=jobs.load_jobs()['jobs'][0]['revisions'][0]
            self.assertEqual(len(revision['snapshot']['design_views']['scene_rows']),1)
            self.assertIn('<svg',revision['snapshot']['design_views']['line_svg'])
            app.button(key='new_job').click().run()
            app.button(key='open_saved_job').click().run()
            self.assertFalse(app.exception,[e.message for e in app.exception])
            self.assertEqual(app.radio(key='render_mode').value,'Ultra')
            self.assertEqual(len(app.session_state['_job_scene_rows']),1)
