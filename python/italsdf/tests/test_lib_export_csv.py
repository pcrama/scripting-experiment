# -*- coding: utf-8 -*-
import unittest

import sys_path_hack

with sys_path_hack.app_in_path():
    import lib_export_csv
    import storage


def make_reservation(**overrides):
    defaults = dict(
        name='testing',
        email='test@example.com',
        places=0,
        date='2022-03-19',
        outside_extra_starter=0,
        outside_main_starter=0,
        outside_bolo=0,
        outside_extra_dish=0,
        outside_dessert=0,
        inside_extra_starter=0,
        inside_main_starter=0,
        inside_bolo=0,
        inside_extra_dish=0,
        kids_bolo=0,
        kids_extra_dish=0,
        gdpr_accepts_use=True,
        uuid='deadbeef',
        time=12345678.9,
        active=True,
        origin='unit tests')
    defaults.update(**overrides)
    return storage.Reservation(**defaults)


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
        for data, expected in (
                (dict(name='t1',email='comment',places=2,outside_extra_starter=1,outside_main_starter=2,outside_extra_dish=3,outside_bolo=4,outside_dessert=5+6,inside_main_starter=7,inside_extra_starter=15,inside_bolo=8,inside_extra_dish=14,origin='unit test',gdpr_accepts_use=False,active=True),
                 ('t1',2,7,15,8,14,22,0,0,0,2,1,4,3,11,'804.00 €','comment','','',True,'unit test')),
                (dict(name='t2',email='t2@b.com',places=1,outside_extra_starter=2,outside_main_starter=1,outside_extra_dish=3,outside_bolo=4,outside_dessert=6+5,inside_main_starter=6,inside_extra_starter=14,inside_bolo=7,inside_extra_dish=13,kids_bolo=1,kids_extra_dish=2,origin=None,gdpr_accepts_use=True,active=True),
                 ('t2',1,6,14,7,13,20,1,2,3,1,2,4,3,11,'798.00 €','','t2@b.com','t2@b.com',True,None)),
                (dict(name='t3',email='t3@b.com',places=3,outside_extra_starter=2,outside_main_starter=0,outside_extra_dish=0,outside_bolo=0,outside_dessert=0,inside_main_starter=0,inside_extra_starter=0,inside_bolo=0,inside_extra_dish=0,origin=None,gdpr_accepts_use=False,active=True),
                 ('t3',3,0,0,0,0,0,0,0,0,0,2,0,0,0,'15.00 €','','t3@b.com','',True,None)),
                (dict(name='t4',email='t4@b.com',places=3,outside_extra_starter=2,outside_main_starter=0,outside_extra_dish=0,outside_bolo=0,outside_dessert=0,inside_main_starter=0,inside_extra_starter=0,inside_bolo=0,inside_extra_dish=0,origin=None,gdpr_accepts_use=False,active=False),
                 ('t4',3,0,0,0,0,0,0,0,0,0,2,0,0,0,'15.00 €','','t4@b.com','',False,None)),
        ):
            with self.subTest(expected=expected):
                lib_export_csv.export_reservation(writer, make_reservation(**data))
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
                 'Total','Commentaire','Email','RGPD','Actif','Origine'),
        )):
            with self.subTest(idx=idx + 1):
                self.assertEqual(writer.rows[idx], expected)


if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python3 test_lib_export_csv.py"
# End:
