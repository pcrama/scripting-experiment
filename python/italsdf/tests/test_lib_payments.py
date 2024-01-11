# -*- coding: utf-8 -*-
import cgi
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import sys_path_hack

with sys_path_hack.app_in_path():
    import config
    import lib_payments
    import storage


class GetParametersParsing(unittest.TestCase):
    def test_examples(self):
        for (cgi_parse, expected_filter, expected_offset, expected_limit) in (
                ({}, None, None, None),
                ({"filtering": "abc"}, "abc", None, None),
                ({"filtering": "def", "offset": "3"}, "def", 3, None),
                ({"filtering": "ghilkj", "offset": "0", "limit": "8"}, "ghilkj", 0, 8,),
                ({"fubar": "mno", "offset": "7", "limit": "-11"}, None, 7, -11),
                ({"offset": "-2"}, None, -2, None),
                ({"limit": "9"}, None, None, 9),
                ({"offset": "two", "limit": "22"}, None, None, 22),
                ({"offset": "33", "limit": "three"}, None, 33, None),
        ):
            with self.subTest(
                    cgi_parse=cgi_parse,
                    expected=(expected_filter, expected_offset, expected_limit)
            ), patch("cgi.parse") as patched_cgi_parse:
                patched_cgi_parse.return_value = cgi_parse
                filtering, offset, limit = lib_payments.get_parameters_for_GET()
                self.assertEqual(filtering, expected_filter)
                self.assertEqual(offset, expected_offset)
                self.assertEqual(limit, expected_limit)


class MakePaymentBuilder(unittest.TestCase):
    EXAMPLE_DATA = [
        ['Nº de séquence', "Date d'exécution", 'Date valeur', 'Montant', 'Devise du compte', 'Numéro de compte', 'Type de transaction', 'Contrepartie', 'Nom de la contrepartie', 'Communication', 'Détails', 'Statut', 'Motif du refus'],
        ['2023-00127', '28/03/2023', '28/03/2023', '18', 'EUR', 'BE00010001000101', 'Virement en euros', 'BE00020002000202', 'ccccc-ccccccccc', 'Reprise marchandises (viande hachee) souper italien', 'VIREMENT EN EUROS DU COMPTE BE00020002000202 BIC GABBBEBB CCCCC-CCCCCCCCC AV DE LA GARE 76 9999 WAGADOUGOU COMMUNICATION : REPRISE MARCHANDISES (VIANDE HACHEE) SOUPER ITALIEN REFERENCE BANQUE : 2303244501612 DATE VALEUR : 28/03/2023', 'Accepté', ''],
        ['2023-00126', '26/02/2023', '26/02/2023', '50.34', 'EUR', 'BE00010001000101', 'Virement en euros', 'BE00030003000303', 'HHHHHHH SSSSSSSS', 'Cotisation', 'VIREMENT EN EUROS DU COMPTE BE00030003000303 BIC GABBBEBB HHHHHHH SSSSSSSS CHEMIN DE LA GARE 123 9999 WAGADOUGOU COMMUNICATION : COTISATION REFERENCE BANQUE : 2303244503009 DATE VALEUR : 26/02/2023', 'Accepté', ''],
    ]
    def test_examples(self):
        builder = lib_payments.make_payment_builder(self.EXAMPLE_DATA[0])
        with self.subTest(data_row=0, with_proto=False):
            self.assertEqual(
                builder(self.EXAMPLE_DATA[1]).to_dict(),
                { 'rowid': None,
                  'timestamp': 1679997600.0,
                  'amount_in_cents': 1800,
                  'comment': 'Reprise marchandises (viande hachee) souper italien',
                  'uuid': None,
                  'src_id': '2023-00127',
                  'other_account': 'BE00020002000202',
                  'other_name': 'ccccc-ccccccccc',
                  'status': 'Accepté',
                  'user': None,
                  'ip': None})
        with self.subTest(data_row=0, with_proto=True):
            self.assertEqual(
                builder(
                    self.EXAMPLE_DATA[1],
                    storage.Payment(
                        rowid=1,
                        timestamp=2.5,
                        amount_in_cents=3,
                        comment="unit test comment",
                        uuid="c0ffee00beef1234",
                        src_id="2023-1000",
                        other_account="BE0101",
                        other_name="Ms Abc",
                        status="Accepté",
                        user="unit-test-user",
                        ip="1.2.3.4")
                ).to_dict(),
                { 'rowid': None,
                  'timestamp': 1679997600.0,
                  'amount_in_cents': 1800,
                  'comment': 'Reprise marchandises (viande hachee) souper italien',
                  'uuid': None,
                  'src_id': '2023-00127',
                  'other_account': 'BE00020002000202',
                  'other_name': 'ccccc-ccccccccc',
                  'status': 'Accepté',
                  'user': "unit-test-user",
                  'ip': "1.2.3.4"})
        with self.subTest(data_row=1, with_proto=False):
            self.assertEqual(
                builder(self.EXAMPLE_DATA[2]).to_dict(),
                { 'rowid': None,
                  'timestamp': 1677409200.0,
                  'amount_in_cents': 5034,
                  'comment': 'Cotisation',
                  'uuid': None,
                  'src_id': '2023-00126',
                  'other_account': 'BE00030003000303',
                  'other_name': 'HHHHHHH SSSSSSSS',
                  'status': 'Accepté',
                  'user': None,
                  'ip': None})

class GetPaymentsData(unittest.TestCase):
    def test_examples(self):
        SEL_FROM = 'SELECT rowid,timestamp,amount_in_cents,comment,uuid,src_id,other_account,other_name,status,user,ip FROM payments'
        LIM_OFFS = 'LIMIT :limit OFFSET :offset'
        for (max_rows, filtering, offset, limit, expected_sql, expected_bindings) in (
                (10, None, None, None, f"{SEL_FROM} {LIM_OFFS}", {"limit": 10, "offset": 0}),
                (5, "aBc", None, None, f"{SEL_FROM} WHERE (LOWER(comment) like :filter_comment) {LIM_OFFS}", {'filter_comment': '%abc%', "limit": 5, "offset": 0}),
                (5, "aBc", -3, 27, f"{SEL_FROM} WHERE (LOWER(comment) like :filter_comment) {LIM_OFFS}", {'filter_comment': '%abc%', "limit": 5, "offset": 0}),
                (5, "%aBc", 3, 2, f"{SEL_FROM} WHERE (LOWER(comment) like :filter_comment) {LIM_OFFS}", {'filter_comment': '%abc', "limit": 2, "offset": 3}),
                (5, "", 3, 2, f"{SEL_FROM} {LIM_OFFS}", {"limit": 2, "offset": 3}),):
            mock_connection = MagicMock(spec=['execute'])
            mock_connection.execute = mock_execute = MagicMock(return_value=[])
            self.assertEqual(lib_payments.get_payments_data(mock_connection, max_rows, filtering, offset=offset, limit=limit), [])
            mock_execute.assert_called_once_with(expected_sql, expected_bindings)
    def test_integration(self):
        # Given
        payments = [storage.Payment(
                        rowid=None,
                        timestamp=2.5,
                        amount_in_cents=3,
                        comment="unit test comment",
                        uuid="c0ffee00beef1234",
                        src_id="2023-1000",
                        other_account="BE0101",
                        other_name="Ms Abc",
                        status="Accepté",
                        user="unit-test-user",
                        ip="1.2.3.4"),
                    storage.Payment(
                        rowid=2,
                        timestamp=5.0,
                        amount_in_cents=4,
                        comment="other unit test comment",
                        uuid="beef12346789fedc",
                        src_id="2023-1001",
                        other_account="BE0101",
                        other_name="Ms Abc",
                        status="Accepté",
                        user="unit-test-user",
                        ip="2.1.4.3")] + [
                            storage.Payment(
                                rowid=x + (53 if x % 3 == 0 else 28),
                                timestamp = (104.5 if x % 2 == 0 else 99) - x,
                                amount_in_cents=x * (1 + x % 4),
                                comment=f"Auto comment {x}" if x % 2 == 0 else None,
                                uuid=f"0102{x:08x}3040" if x % 3 > 1 else None,
                                src_id=f"2023-9{x}0{x}",
                                other_account="BE{x:02d}33",
                                other_name="Ms Abc {x % 7}",
                                status="Accepté",
                                user="other-test-user" if x % 7 == 0 else "unit-test-user",
                                ip=f"1.{x}.3.{x}",
                            )
                            for x in range(10)
                        ]
        with tempfile.TemporaryDirectory() as dbdir:
            configuration = {"dbdir": dbdir}
            connection = storage.ensure_connection(configuration)
            for pmnt in payments:
                pmnt.insert_data(connection)

        for params, expected in (
                ((1, None, None, None),
                 [{'amount_in_cents': 3, 'comment': 'unit test comment', 'rowid': 1, 'timestamp': 2.5}]),
                ((2, None, None, None),
                 [{'amount_in_cents': 3, 'comment': 'unit test comment', 'rowid': 1, 'timestamp': 2.5},
                  {'amount_in_cents': 4, 'comment': 'other unit test comment', 'rowid': 2, 'timestamp': 5.0}]),
                ((3, None, None, None),
                 [{'amount_in_cents': 3, 'comment': 'unit test comment', 'rowid': 1, 'timestamp': 2.5},
                  {'amount_in_cents': 4, 'comment': 'other unit test comment', 'rowid': 2, 'timestamp': 5.0},
                  {'amount_in_cents': 2, 'comment': None, 'rowid': 29, 'timestamp': 98.0}]),
                ((0, "unit", None, None),
                 []),
                ((3, "unit", None, None),
                 [{'amount_in_cents': 3, 'comment': 'unit test comment', 'rowid': 1, 'timestamp': 2.5},
                  {'amount_in_cents': 4, 'comment': 'other unit test comment', 'rowid': 2, 'timestamp': 5.0}]),
                ((3, "other", None, None),
                 [{'amount_in_cents': 4, 'comment': 'other unit test comment', 'rowid': 2, 'timestamp': 5.0}]),
                ((3, "unit%", None, None),
                 [{'amount_in_cents': 3, 'comment': 'unit test comment', 'rowid': 1, 'timestamp': 2.5}]),
                ((3, "unit", 1, None),
                 [{'amount_in_cents': 4, 'comment': 'other unit test comment', 'rowid': 2, 'timestamp': 5.0}]),
                ((5, None, 3, 10),
                 [{'amount_in_cents': 6, 'comment': 'Auto comment 2', 'rowid': 30, 'timestamp': 102.5},
                  {'amount_in_cents': 4, 'comment': 'Auto comment 4', 'rowid': 32, 'timestamp': 100.5},
                  {'amount_in_cents': 10, 'comment': None, 'rowid': 33, 'timestamp': 94.0},
                  {'amount_in_cents': 28, 'comment': None, 'rowid': 35, 'timestamp': 92.0},
                  {'amount_in_cents': 8, 'comment': 'Auto comment 8', 'rowid': 36, 'timestamp': 96.5}]),
        ):
            with self.subTest(max_rows=params[0], filtering=params[1], offset=params[2], limit=params[3]):
                # When
                result = lib_payments.get_payments_data(connection, *params)
                # Then
                self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python3 test_lib_payments.py"
# End:
