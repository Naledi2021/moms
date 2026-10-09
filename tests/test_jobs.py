import base64
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import jobs
import supplier_updates
import hardware_ui
import supplier_upload_ui

APP=str(Path(__file__).resolve().parents[1]/'app.py')

class JobTests(unittest.TestCase):
    def test_append_revisions_preserves_original_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'jobs.json'
            snapshot={'total':100,'supplier_products':[],'manual_accessories':[]}
            job_id,number=jobs.save_job('Kitchen',{'job_width':600},snapshot,b'%PDF-first','first CSV',path=path)
            snapshot['total']=200
            jobs.save_job('Kitchen revised',{'job_width':800},snapshot,b'%PDF-second','second CSV',job_id,path)
            data=jobs.load_jobs(path)['jobs'][0]
            self.assertEqual(len(data['revisions']),2)
            first=data['revisions'][0]
            self.assertEqual(first['snapshot']['total'],100)
            self.assertEqual(base64.b64decode(first['pdf_base64']),b'%PDF-first')
            state={'job_width':900,'upload_supplier':'Seno SA','blum_accessories':{'edited_rows':{}}}
            jobs.restore_revision(state,job_id,first)
            self.assertEqual(state['job_width'],600)
            self.assertEqual(state['upload_supplier'],'Seno SA')
            self.assertNotIn('blum_accessories',state)
            jobs.clear_job(state)
            self.assertNotIn('job_width',state)
            self.assertEqual(state['upload_supplier'],'Seno SA')

    def test_ui_save_reopen_and_revise_customer_job(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(jobs,'STORE',Path(directory)/'jobs.json'):
            app=AppTest.from_file(APP).run()
            app.button(key='confirm_room_layout').click().run()
            self.assertFalse(app.exception)
            app.text_input(key='job_name').set_value('Mokoena kitchen')
            app.text_input(key='customer_name').set_value('Thandi Mokoena')
            app.text_input(key='customer_phone').set_value('0100000000')
            app.number_input(key='job_width').set_value(800)
            app.number_input(key='hinge_price_manual').set_value(30)
            app.checkbox(key='plates_included').check().run()
            app.button(key='save_job').click().run()
            self.assertFalse(app.exception,[e.message for e in app.exception])
            job=jobs.load_jobs()['jobs'][0]
            first=job['revisions'][0]
            self.assertEqual(first['state']['customer_name'],'Thandi Mokoena')
            self.assertEqual(first['snapshot']['total'],60)
            app.button(key='new_job').click().run()
            app.button(key='confirm_room_layout').click().run()
            self.assertEqual(app.number_input(key='job_width').value,600)
            app.button(key='open_saved_job').click().run()
            self.assertFalse(app.exception,[e.message for e in app.exception])
            self.assertEqual(app.number_input(key='job_width').value,800)
            self.assertEqual(app.text_input(key='customer_phone').value,'0100000000')
            self.assertEqual(next(m for m in app.metric if m.label=='Job total including entered tax').value,'R 60.00')
            app.number_input(key='job_width').set_value(900).run()
            app.button(key='save_job').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(jobs.load_jobs()['jobs'][0]['revisions']),2)
            self.assertEqual(jobs.load_jobs()['jobs'][0]['revisions'][0]['state']['job_width'],800)

    def test_supplier_snapshot_does_not_reprice_saved_job(self):
        records=[dict(sku='B',product='White board',price=100,unit='m2',length_mm=None,width_mm=None,thickness_mm=18)]
        history={'updates':[dict(supplier='Seno SA',effective_date='2026-01-01',uploaded_utc='2026-01-01T00:00:00+00:00',vat_basis='Excluded',vat_rate=None,filename='prices.csv',products=records)]}
        with tempfile.TemporaryDirectory() as directory,patch.object(jobs,'STORE',Path(directory)/'jobs.json'),patch.object(supplier_updates,'load',return_value=history),patch.object(hardware_ui,'load',return_value=history),patch.object(supplier_upload_ui,'load',return_value=history):
            app=AppTest.from_file(APP).run()
            app.button(key='confirm_room_layout').click().run()
            self.assertFalse(app.exception)
            app.selectbox(key='carcass_supplier_source').set_value('Uploaded supplier prices').run()
            app.number_input(key='hinge_price_manual').set_value(20)
            app.checkbox(key='plates_included').check().run()
            original_total=next(m for m in app.metric if m.label=='Job total including entered tax').value
            app.button(key='save_job').click().run()
            self.assertFalse(app.exception)
            app.button(key='new_job').click().run()
            records[0]['price']=200
            app.button(key='open_saved_job').click().run()
            self.assertFalse(app.exception,[e.message for e in app.exception])
            self.assertEqual(next(m for m in app.metric if m.label=='Job total including entered tax').value,original_total)
            app.button(key='refresh_job_prices').click().run()
            self.assertFalse(app.exception)
            self.assertNotEqual(next(m for m in app.metric if m.label=='Job total including entered tax').value,original_total)
