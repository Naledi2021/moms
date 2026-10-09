from datetime import date
from pathlib import Path
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import hardware_ui

APP=str(Path(__file__).resolve().parents[1]/'app.py')

class HardwareUiTests(unittest.TestCase):
    def test_uploaded_components_vat_quantities_and_included_plates(self):
        records=[]
        for sku,name,price,unit in [('H','Soft-close hinge',115,'each'),('P','Plate',23,'each'),('A','AVENTOS complete set',1150,'set')]:
            records.append(dict(sku=sku,product=name,price=price,unit=unit,length_mm=None,width_mm=None,thickness_mm=None))
        history={'updates':[dict(supplier='Blum',effective_date='2026-01-01',uploaded_utc='2026-01-01T00:00:00+00:00',vat_basis='Included',vat_rate=15,filename='blum.csv',products=records)]}
        with patch.object(hardware_ui,'load',return_value=history):
            app=AppTest.from_file(APP).run()
            app.button(key='confirm_room_layout').click().run()
            self.assertFalse(app.exception)
            app.selectbox(key='hinge_price_source').set_value('Uploaded supplier prices').run()
            app.selectbox(key='plate_price_source').set_value('Uploaded supplier prices').run()
            app.selectbox(key='plate_price_product').set_value('Blum · P · Plate').run()
            next(n for n in app.number_input if n.label=='Identical cabinets').set_value(2).run()
            app.multiselect(key='uploaded_accessories').set_value(['Blum · A · AVENTOS complete set']).run()
            self.assertFalse(app.exception)
            total=next(m for m in app.metric if m.label=='Job total including entered tax')
            self.assertEqual(total.value,'R 1,480.00')
            app.checkbox(key='plates_included').check().run()
            self.assertFalse(app.exception)
            self.assertEqual(next(m for m in app.metric if m.label=='Job total including entered tax').value,'R 1,400.00')
            self.assertTrue(any(b.label=='Download selected hardware CSV' for b in app.get('download_button')))
            # Imported hardware with unknown VAT must not yield a misleading quotation.
            history['updates'][0]['vat_basis']='Not specified'
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(app.error)
            self.assertFalse(app.metric)

    def test_manual_prices_still_work(self):
        with patch.object(hardware_ui,'load',return_value={'updates':[]}):
            app=AppTest.from_file(APP).run()
            app.button(key='confirm_room_layout').click().run()
            app.number_input(key='hinge_price_manual').set_value(25)
            app.checkbox(key='plates_included').check().run()
            self.assertFalse(app.exception)
            self.assertEqual(next(m for m in app.metric if m.label=='Job total including entered tax').value,'R 50.00')
