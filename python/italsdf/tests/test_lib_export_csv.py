# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch

import sys_path_hack
from conftest import make_reservation

with sys_path_hack.app_in_path():
    import lib_export_csv
    import storage


class FakeWriter:
    def __init__(self):
        self.rows = []

    def writerow(self, row):
        self.rows.append(row)

    @property
    def last_row(self):
        return self.rows[-1]


class ExportDataRow(unittest.TestCase):
    def test_examples(self):
        writer = FakeWriter()
        for data, cents_payed, expected in (
                (dict(name='t1',email='comment',places=2,outside_extra_starter=1,outside_main_starter=2,outside_extra_dish=3,outside_bolo=4,outside_dessert=5+6,inside_main_starter=7,inside_extra_starter=15,inside_bolo=8,inside_extra_dish=14,origin='unit test',gdpr_accepts_use=False,active=True,cents_due=80400),
                 0,
                 ('t1',2,7,15,8,14,22,0,0,0,2,1,4,3,11,'804.00 €','804.00 €','unit test extra comment','','',True,'unit test')),
                (dict(name='t2',email='t2@b.com',places=1,outside_extra_starter=2,outside_main_starter=1,outside_extra_dish=3,outside_bolo=4,outside_dessert=6+5,inside_main_starter=6,inside_extra_starter=14,inside_bolo=7,inside_extra_dish=13,kids_bolo=1,kids_extra_dish=2,origin=None,gdpr_accepts_use=True,active=True,extra_comment='foobar',cents_due=79800),
                 0,
                 ('t2',1,6,14,7,13,20,1,2,3,1,2,4,3,11,'798.00 €','798.00 €','foobar','t2@b.com','t2@b.com',True,None)),
                (dict(name='t3',email='t3@b.com',places=3,outside_extra_starter=2,outside_main_starter=0,outside_extra_dish=0,outside_bolo=0,outside_dessert=0,inside_main_starter=0,inside_extra_starter=0,inside_bolo=0,inside_extra_dish=0,origin=None,gdpr_accepts_use=False,active=True,cents_due=1500),
                 0,
                 ('t3',3,0,0,0,0,0,0,0,0,0,2,0,0,0,'15.00 €','15.00 €','unit test extra comment','t3@b.com','',True,None)),
                (dict(name='t4',email='t4@b.com',places=3,outside_extra_starter=2,outside_main_starter=0,outside_extra_dish=0,outside_bolo=0,outside_dessert=0,inside_main_starter=0,inside_extra_starter=0,inside_bolo=0,inside_extra_dish=0,origin=None,gdpr_accepts_use=False,active=False,extra_comment='',cents_due=1500),
                 0,
                 ('t4',3,0,0,0,0,0,0,0,0,0,2,0,0,0,'15.00 €','15.00 €','','t4@b.com','',False,None)),
                (dict(name='t5',email='t5@b.com',places=3,outside_extra_starter=2,outside_main_starter=0,outside_extra_dish=0,outside_bolo=0,outside_dessert=0,inside_main_starter=0,inside_extra_starter=0,inside_bolo=0,inside_extra_dish=0,origin=None,gdpr_accepts_use=False,active=False,extra_comment='',cents_due=1500),
                 1500,
                 ('t5',3,0,0,0,0,0,0,0,0,0,2,0,0,0,'15.00 €','0.00 €','','t5@b.com','',False,None)),
                (dict(name='t6',email='t6@b.com',places=3,outside_extra_starter=2,outside_main_starter=0,outside_extra_dish=0,outside_bolo=0,outside_dessert=0,inside_main_starter=0,inside_extra_starter=0,inside_bolo=0,inside_extra_dish=0,origin=None,gdpr_accepts_use=False,active=False,extra_comment='',cents_due=1500),
                 1050,
                 ('t6',3,0,0,0,0,0,0,0,0,0,2,0,0,0,'15.00 €','4.50 €','','t6@b.com','',False,None)),
        ):
            connection = object()
            with self.subTest(expected=expected):
                reservation = make_reservation(**data)
                with patch("storage.Payment") as patched_payments:
                    patched_payments.sum_payments.return_value = cents_payed
                    lib_export_csv.export_reservation(writer, connection, reservation)
                    patched_payments.sum_payments.assert_called_once_with(connection, reservation.uuid)
                self.assertEqual(writer.last_row, expected)


class ExportHeaders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lib_export_csv.MAIN_STARTER_SHORT = "main_starter_short"
        lib_export_csv.EXTRA_STARTER_SHORT = "extra_starter_short"
        lib_export_csv.BOLO_SHORT = "bolo_short"
        lib_export_csv.EXTRA_DISH_SHORT = "extra_dish_short"
        lib_export_csv.KIDS_BOLO_SHORT = "kids_bolo_short"
        lib_export_csv.KIDS_EXTRA_DISH_SHORT = "kids_extra_dish_short"
        lib_export_csv.DESSERT_SHORT = "dessert_short"

    def test_static_values(self):
        writer = FakeWriter()
        lib_export_csv.write_column_header_rows(writer)
        for idx, expected in enumerate((
                ('','',
                 'Menu','...','...','...','...',
                 'Enfants','...','...',
                 'À la carte','...','...','...','...',
                 '','','','','',''),
                ('Nom','Places',
                 "main_starter_short", "extra_starter_short", "bolo_short", "extra_dish_short", "dessert_short",
                 "kids_bolo_short", "kids_extra_dish_short", "dessert_short",
                 "main_starter_short", "extra_starter_short", "bolo_short", "extra_dish_short", "dessert_short",
                 'Total','Dû','Commentaire','Email','RGPD','Actif','Origine'),
        )):
            with self.subTest(idx=idx + 1):
                self.assertEqual(writer.rows[idx], expected)


if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python3 test_lib_export_csv.py"
# End:
