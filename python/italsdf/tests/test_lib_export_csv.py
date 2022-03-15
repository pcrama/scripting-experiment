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
        outside_fondus=0,
        outside_assiettes=0,
        outside_bolo=0,
        outside_scampis=0,
        outside_tiramisu=0,
        outside_tranches=0,
        inside_fondus=0,
        inside_assiettes=0,
        inside_bolo=0,
        inside_scampis=0,
        inside_tiramisu=0,
        inside_tranches=0,
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
                (dict(name='t1',email='comment',places=2,outside_fondus=1,outside_assiettes=2,outside_scampis=3,outside_bolo=4,outside_tiramisu=5,outside_tranches=6,inside_assiettes=7,inside_fondus=15,inside_bolo=8,inside_scampis=14,inside_tiramisu=9,inside_tranches=13,origin='unit test',gdpr_accepts_use=False,active=True),
                 ('t1',2,2,1,4,3,5,6,7,15,8,14,9,13,'812.00 €','comment','','',True,'unit test')),
                (dict(name='t2',email='t2@b.com',places=1,outside_fondus=2,outside_assiettes=1,outside_scampis=3,outside_bolo=4,outside_tiramisu=6,outside_tranches=5,inside_assiettes=6,inside_fondus=14,inside_bolo=7,inside_scampis=13,inside_tiramisu=8,inside_tranches=12,origin=None,gdpr_accepts_use=True,active=True),
                 ('t2',1,1,2,4,3,6,5,6,14,7,13,8,12,'757.00 €','','t2@b.com','t2@b.com',True,None)),
                (dict(name='t3',email='t3@b.com',places=3,outside_fondus=2,outside_assiettes=0,outside_scampis=0,outside_bolo=0,outside_tiramisu=0,outside_tranches=0,inside_assiettes=0,inside_fondus=0,inside_bolo=0,inside_scampis=0,inside_tiramisu=0,inside_tranches=0,origin=None,gdpr_accepts_use=False,active=True),
                 ('t3',3,0,2,0,0,0,0,0,0,0,0,0,0,'18.00 €','','t3@b.com','',True,None)),
                (dict(name='t4',email='t4@b.com',places=3,outside_fondus=2,outside_assiettes=0,outside_scampis=0,outside_bolo=0,outside_tiramisu=0,outside_tranches=0,inside_assiettes=0,inside_fondus=0,inside_bolo=0,inside_scampis=0,inside_tiramisu=0,inside_tranches=0,origin=None,gdpr_accepts_use=False,active=False),
                 ('t4',3,0,2,0,0,0,0,0,0,0,0,0,0,'18.00 €','','t4@b.com','',False,None)),
        ):
            with self.subTest(expected=expected):
                lib_export_csv.export_reservation(writer, make_reservation(**data))
                self.assertEqual(writer.last_row, expected)


class ExportHeaders(unittest.TestCase):
    def test_static_values(self):
        writer = FakeWriter()
        lib_export_csv.write_column_header_rows(writer)
        for idx, expected in enumerate((
                ('','',
                 'À la carte','...','...','...','...','...',
                 'Menu','...','...','...','...','...',
                 '','','','','',''),
                ('Nom','Places',
                 'Assiette','Fondu','Bolo','Scampi','Tiramisu','Tranche',
                 'Assiette','Fondu','Bolo','Scampi','Tiramisu','Tranche',
                 'Total','Commentaire','Email','RGPD','Actif','Origine'),
        )):
            with self.subTest(idx=idx + 1):
                self.assertEqual(writer.rows[idx], expected)


if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python test_lib_export_csv.py"
# End:
