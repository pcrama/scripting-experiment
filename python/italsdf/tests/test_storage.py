# -*- coding: utf-8 -*-
import cgi
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import sys_path_hack
from conftest import make_reservation

with sys_path_hack.app_in_path():
    import config
    import storage


class TestPayments(unittest.TestCase):
    TEMP_DIR = None
    CONNECTION = None
    CONFIGURATION = {}
    UUID_WITH_TWO_PAYMENTS = "c0ffee00beef1234"

    @classmethod
    def setUpClass(cls):
        cls.TEMP_DIR = tempfile.TemporaryDirectory()
        cls.CONFIGURATION = {"dbdir": cls.TEMP_DIR.name}
        cls.CONNECTION = storage.ensure_connection(cls.CONFIGURATION)
        payments = [storage.Payment(
                        rowid=1,
                        timestamp=2.5,
                        amount_in_cents=3,
                        comment="unit test comment",
                        uuid=cls.UUID_WITH_TWO_PAYMENTS,
                        src_id='src_id_0',
                        other_account='BE515300',
                        other_name='name 0',
                        status='Accepté',
                        user="unit-test-user",
                        ip="1.2.3.4"),
                    storage.Payment(
                        rowid=2,
                        timestamp=3.0,
                        amount_in_cents=4,
                        comment="second payment for same uuid",
                        uuid=cls.UUID_WITH_TWO_PAYMENTS,
                        src_id='src_id_1',
                        other_account='BE515401',
                        other_name='name 1',
                        status='Accepté',
                        user="unit-test-user",
                        ip="1.2.3.4"),
                    storage.Payment(
                        rowid=3,
                        timestamp=5.0,
                        amount_in_cents=4,
                        comment="other unit test comment",
                        uuid="beef12346789fedc",
                        src_id='src_id_2',
                        other_account='BE515502',
                        other_name='name 2',
                        status='Accepté',
                        user="unit-test-user",
                        ip="2.1.4.3")] + [
                            storage.Payment(
                                rowid=x + (53 if x % 3 == 0 else 28),
                                timestamp = (104.5 if x % 2 == 0 else 99) - x,
                                amount_in_cents=x * (1 + x % 4),
                                comment=f"Auto comment {x}" if x % 2 == 0 else None,
                                uuid=f"0102{x:08x}3040" if x % 3 > 1 else None,
                                src_id=f'src_id_{x:02d}',
                                other_account=f'BE515603{x:02d}',
                                other_name=f'name 3{x:02d}',
                                status='Accepté',
                                user="other-test-user" if x % 7 == 0 else "unit-test-user",
                                ip=f"1.{x}.3.{x}",
                            )
                            for x in range(10)
                        ]
        for pmnt in payments:
            pmnt.insert_data(cls.CONNECTION)

    @classmethod
    def tearDownClass(cls):
        cls.CONNECTION.close()
        cls.TEMP_DIR.cleanup()

    def test_sum_of_two_payments(self):
        self.assertEqual(storage.Payment.sum_payments(self.CONNECTION, self.UUID_WITH_TWO_PAYMENTS), 7)

    def test_sum_payments_for_one_payment(self):
        self.assertEqual(storage.Payment.sum_payments(self.CONNECTION, "beef12346789fedc"), 4)

    def test_sum_payments_for_unknown_payment(self):
        self.assertEqual(storage.Payment.sum_payments(self.CONNECTION, "unknown"), 0)

    def test_reservations_and_payments_collaboration(self):
        for reservation, expected in (
                (make_reservation(cents_due=10, uuid=self.UUID_WITH_TWO_PAYMENTS), 3),
                (make_reservation(cents_due=11, uuid="beef12346789fedc"), 7),
                (make_reservation(cents_due=12, uuid="unknown"), 12),
        ):
            with self.subTest(uuid=reservation.uuid):
                self.assertEqual(reservation.remaining_amount_due_in_cents(self.CONNECTION), expected)


if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python3 test_storage.py"
# End:
