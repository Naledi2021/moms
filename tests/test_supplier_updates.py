import unittest
from datetime import date
from io import BytesIO
from pathlib import Path
import tempfile
import pandas as pd
from supplier_updates import read_upload, validate, save, load, current_products, material_rate

MAPPING={k:k for k in ('sku','product','price','unit','length_mm','width_mm','thickness_mm')}
CSV=b'sku,product,price,unit,length_mm,width_mm,thickness_mm\n001,White board,1150,sheet,2500,2000,18\n002,Hinge,25,each,,,\n'

class SupplierUpdatesTests(unittest.TestCase):
    def test_csv_and_excel_preserve_codes(self):
        frame=read_upload(CSV,'prices.csv')
        rows,errors=validate(frame,MAPPING)
        self.assertFalse(errors);self.assertEqual(rows[0]['sku'],'001')
        output=BytesIO()
        with pd.ExcelWriter(output,engine='openpyxl') as writer:
            frame.to_excel(writer,sheet_name='Boards',index=False)
        excel=read_upload(output.getvalue(),'prices.xlsx','Boards')
        self.assertEqual(validate(excel,MAPPING)[0],rows)

    def test_invalid_rows_block_update(self):
        frame=read_upload(CSV,'prices.csv')
        frame.loc[0,'length_mm']=''
        frame.loc[1,'price']='NaN'
        rows,errors=validate(frame,MAPPING)
        self.assertEqual(len(errors),2);self.assertFalse(rows)
        frame=read_upload(CSV,'prices.csv');frame.loc[1,'sku']='001'
        self.assertTrue(validate(frame,MAPPING)[1])

    def test_history_dates_merge_vat_and_duplicate_uploads(self):
        rows,_=validate(read_upload(CSV,'prices.csv'),MAPPING)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'prices.json'
            self.assertTrue(save(rows,'Seno SA','2026-01-01','Included',15,'prices.csv',path))
            self.assertFalse(save(rows,'Seno SA','2026-01-01','Included',15,'prices.csv',path))
            latest=dict(rows[0],price=2300)
            save([latest],'Seno SA','2027-01-01','Included',15,'next.csv',path)
            older=dict(rows[0],price=575)
            save([older],'Seno SA','2025-01-01','Included',15,'old.csv',path)
            current=current_products(load(path),date(2026,10,8))
            self.assertEqual(len(current),2)
            self.assertEqual(current[0]['price'],1150)
            self.assertAlmostEqual(material_rate(current[0]),200)
            future=current_products(load(path),date(2027,1,1))
            self.assertEqual(future[0]['price'],2300)
            self.assertEqual(len(load(path)['updates']),3)

    def test_unknown_vat_is_not_silently_used(self):
        with self.assertRaises(ValueError):material_rate({'vat_basis':'Not specified'})
        rows,_=validate(read_upload(CSV,'prices.csv'),MAPPING)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):save(rows,'Seno SA','2026-01-01','Included',None,'prices.csv',Path(directory)/'p.json')

if __name__=='__main__':unittest.main()
