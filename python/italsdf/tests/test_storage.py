# -*- coding: utf-8 -*-
import sqlite3
import time
from typing import Optional
import unittest

import sys_path_hack
from conftest import make_payment, make_reservation

try:
    import app.storage as storage
except ImportError:
    with sys_path_hack.app_in_path():
        import storage


class TestPayments(unittest.TestCase):
    CONNECTION: Optional[sqlite3.Connection]
    CONFIGURATION = {}
    UUID_WITH_TWO_PAYMENTS = "c0ffee00beef1234"

    @classmethod
    def setUpClass(cls):
        cls.CONFIGURATION = {"dbdir": ":memory:"}
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
        with cls.CONNECTION:
            for pmnt in payments:
                pmnt.insert_data(cls.CONNECTION)
            make_reservation(name="name1", email="one@example.com", places=3, outside_dessert=1, inside_bolo=1, inside_main_starter=1, cents_due=12345, bank_id="bank_id_1", uuid=cls.UUID_WITH_TWO_PAYMENTS).insert_data(cls.CONNECTION)
            make_reservation(name="name2", email="two@example.com", places=2, outside_dessert=1, inside_bolo=2, inside_main_starter=2, cents_due=34512, bank_id="bank_id_2", uuid="beef12346789fedc").insert_data(cls.CONNECTION)

    @classmethod
    def tearDownClass(cls):
        if cls.CONNECTION:
            cls.CONNECTION.close()

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

    def test_join_payments_and_reservations(self):
        joined = list(storage.Payment.join_reservations(self.CONNECTION))
        self.assertEqual(len(joined), 13)
        self.assertEqual(sum((res is not None for _, res in joined)), 3)
        self.assertEqual(sum((res is not None and res.bank_id == "bank_id_1" for _, res in joined)), 2)
        self.assertEqual(sum((res is not None and res.bank_id == "bank_id_2" for _, res in joined)), 1)


class TestPayments_max_timestamp(unittest.TestCase):
    def test_max_timestamp_empty_db(self):
        configuration = {"dbdir": ":memory:"}
        with storage.ensure_connection(configuration) as connection:
            self.assertEqual(storage.Payment.max_timestamp(connection), storage.Payment.EMPTY_DB_TIMESTAMP)

    def test_max_timestamp_one_payment(self):
        configuration = {"dbdir": ":memory:"}
        connection = storage.ensure_connection(configuration)
        with connection:
            make_payment(timestamp=3.14).insert_data(connection)

        self.assertEqual(storage.Payment.max_timestamp(connection), 3.14)

    def test_set_bank_id(self):
        configuration = {"dbdir": ":memory:"}
        connection = storage.ensure_connection(configuration)
        with connection:
            payment = make_payment(timestamp=3.14).insert_data(connection)

        before_save = time.time()
        with connection:
            payment.update_uuid(connection, "new_uuid", "the-new-user", "192.0.0.1")
        after_save = time.time()

        reloaded = storage.Payment.find_by_src_id(connection, payment.src_id)

        self.assertEqual(reloaded.uuid, "new_uuid")
        self.assertEqual(reloaded.user, "the-new-user")
        self.assertEqual(reloaded.ip, "192.0.0.1")
        self.assertEqual(reloaded.comment, payment.comment)
        self.assertEqual(reloaded.amount_in_cents, payment.amount_in_cents)
        self.assertLessEqual(before_save, reloaded.timestamp)
        self.assertLessEqual(reloaded.timestamp, after_save)

    def test_clear_bank_id(self):
        configuration = {"dbdir": ":memory:"}
        connection = storage.ensure_connection(configuration)
        for idx, blank_uuid in enumerate(("", None)):
            with self.subTest(blank_uuid=blank_uuid):
                src_id = f"the-src-id-{idx}"
                with connection:
                    payment = make_payment(
                        src_id=src_id, timestamp=3.14, uuid="some-uuid-that-is-not-blank"
                    ).insert_data(connection)

                before_save = time.time()
                with connection:
                    payment.update_uuid(connection, blank_uuid, "the-new-user", "192.0.0.1")
                after_save = time.time()

                reloaded = storage.Payment.find_by_src_id(connection, payment.src_id)

                self.assertIs(reloaded.uuid, None)
                self.assertEqual(reloaded.user, "the-new-user")
                self.assertEqual(reloaded.ip, "192.0.0.1")
                self.assertEqual(reloaded.comment, payment.comment)
                self.assertEqual(reloaded.amount_in_cents, payment.amount_in_cents)
                self.assertLessEqual(before_save, reloaded.timestamp)
                self.assertLessEqual(reloaded.timestamp, after_save)


if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python3 test_storage.py"
# End:
