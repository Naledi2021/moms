from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import default_prices
from default_prices import load_defaults,save_defaults,seed_defaults,capture_defaults
import jobs

class DefaultsTests(unittest.TestCase):
    def test_persistence_profiles_and_invalid_prices(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'prices.json'
            save_defaults({'carcass|Melamine|18':120,'hinge|Roco':35},path)
            save_defaults({'carcass|Melamine|16':90},path)
            self.assertEqual(len(load_defaults(path)['prices']),3)
            before=path.read_bytes()
            for value in (-1,float('nan'),float('inf')):
                with self.assertRaises(ValueError):save_defaults({'hinge|Roco':value},path)
            self.assertEqual(path.read_bytes(),before)
            with self.assertRaises(ValueError):save_defaults({'customer_name':25},path)

    def test_defaults_do_not_override_job_prices_and_switch_profiles(self):
        defaults={'prices':{'carcass|Melamine|18':120,'carcass|Melamine|16':95,'hinge|Roco':35,'hinge|Blum':85}}
        state={};seed_defaults(state,defaults)
        self.assertEqual(state['carcass_supplier_rate'],120)
        state['carcass_supplier_rate']=135;seed_defaults(state,defaults)
        self.assertEqual(state['carcass_supplier_rate'],135)
        state['job_thickness']=16;seed_defaults(state,defaults)
        self.assertEqual(state['carcass_supplier_rate'],95)
        state['job_hinge_brand']='Blum';seed_defaults(state,defaults)
        self.assertEqual(state['hinge_price_manual'],85)

    def test_capture_excludes_customer_details_and_quantities(self):
        state={'customer_name':'private','job_units':4,'job_labour':200,'job_thickness':18}
        prices=capture_defaults(state,120,40,140,35,5,[{'Accessory':'Runner','Quantity':9,'Unit price (R)':450}])
        self.assertEqual(prices['accessory|Runner'],450)
        self.assertNotIn('customer_name',prices);self.assertNotIn('job_units',prices)

    def test_new_job_defaults_editable_saved_job_frozen(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(default_prices,'STORE',Path(directory)/'defaults.json'),patch.object(jobs,'STORE',Path(directory)/'jobs.json'):
            save_defaults({'carcass|Melamine|18':120,'door|Melamine|18':150,'back|Masonite|3':40,'hinge|Roco':35,'plate|Roco':5,'job_labour':200})
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run()
            app.button(key='confirm_room_layout').click().run()
            self.assertFalse(app.exception,[e.message for e in app.exception])
            self.assertEqual(app.number_input(key='carcass_supplier_rate').value,120)
            app.number_input(key='carcass_supplier_rate').set_value(130).run()
            app.button(key='save_current_defaults').click().run()
            self.assertEqual(load_defaults()['prices']['carcass|Melamine|18'],130)
            app.button(key='save_job').click().run()
            save_defaults({'carcass|Melamine|18':190})
            app.button(key='new_job').click().run();app.button(key='confirm_room_layout').click().run()
            self.assertEqual(app.number_input(key='carcass_supplier_rate').value,190)
            app.button(key='open_saved_job').click().run()
            self.assertFalse(app.exception,[e.message for e in app.exception])
            self.assertEqual(app.number_input(key='carcass_supplier_rate').value,130)
            app.button(key='refresh_shared_defaults').click().run()
            self.assertEqual(app.number_input(key='carcass_supplier_rate').value,190)

if __name__=='__main__':unittest.main()
