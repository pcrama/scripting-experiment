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


class TestReservation(unittest.TestCase):
    connection: Optional[sqlite3.Connection] = None

    @classmethod
    def setUpClass(cls):
        cls.connection = storage.create_db({'dbdir': ':memory:'})
        with cls.connection:
            storage.Reservation(
                 civility='',
                 first_name='',
                 last_name='n1',
                 email='n1@e.com',
                 date='2024-03-23',
                 paying_seats=1,
                 free_seats=2,
                 gdpr_accepts_use=True,
                 cents_due=1234,
                 bank_id='bank_id_1',
                 uuid='uuid_1',
                 timestamp=3.14,
                 active=True,
                 origin=None).insert_data(cls.connection)
            storage.Reservation(
                 civility='',
                 first_name='',
                 last_name='n2',
                 email='n2@f.com',
                 date='2024-03-23',
                 paying_seats=4,
                 free_seats=0,
                 gdpr_accepts_use=True,
                 cents_due=2345,
                 bank_id='bank_id_2',
                 uuid='uuid_2',
                 timestamp=1.41,
                 active=True,
                 origin=None).insert_data(cls.connection)
            storage.Reservation(
                 civility='',
                 first_name='',
                 last_name='n3',
                 email='n3@g.com',
                 date='2024-03-23',
                 paying_seats=4,
                 free_seats=5,
                 gdpr_accepts_use=True,
                 cents_due=2345,
                 bank_id='bank_id_3',
                 uuid='uuid_3',
                 timestamp=1.71,
                 active=False,
                 origin='admin').insert_data(cls.connection)
            storage.Reservation(
                 civility='',
                 first_name='',
                 last_name='n1',
                 email='n1@e.com',
                 paying_seats=5,
                 free_seats=0,
                 date='2099-12-31',
                 gdpr_accepts_use=True,
                 cents_due=3456,
                 bank_id='bank_id_4',
                 uuid='uuid_4',
                 timestamp=2.72,
                 active=True,
                 origin=None).insert_data(cls.connection)

    def test_count_places(self):
        self.assertEqual(storage.Reservation.count_reservations(self.connection, first_name='', last_name='n3', email='n3@g.com'), (1, 9))
        self.assertEqual(storage.Reservation.count_reservations(self.connection, first_name='', last_name='n1', email='n1@e.com'), (2, 8))
        self.assertEqual(storage.Reservation.count_reservations(self.connection, first_name='', last_name='N1', email='N2@F.COM'), (3, 12))

    def test_parse_from_row_simple_reservation(self):
        reservation, tail = storage.Reservation.parse_from_row(
            ['', '', 'name', 'email@example.com', '2024-03-23', 1, 2, True, 4, 'bank_id', 'uuid', 3.1415, True, 'origin'])
        self.assertIsNotNone(reservation)
        self.assertEqual(tail, [])
        self.assertEqual(reservation.civility, '')
        self.assertEqual(reservation.first_name, '')
        self.assertEqual(reservation.last_name, 'name')
        self.assertEqual(reservation.name, 'name')
        self.assertEqual(reservation.email, 'email@example.com')
        self.assertEqual(reservation.date, '2024-03-23')
        self.assertEqual(reservation.paying_seats, 1)
        self.assertEqual(reservation.free_seats, 2)
        self.assertEqual(reservation.gdpr_accepts_use, True)
        self.assertEqual(reservation.cents_due, 4)
        self.assertEqual(reservation.bank_id, 'bank_id')
        self.assertEqual(reservation.uuid, 'uuid')
        self.assertEqual(reservation.timestamp, 3.1415)
        self.assertEqual(reservation.active, True)
        self.assertEqual(reservation.origin, 'origin')


class TestPayments(unittest.TestCase):
    CONNECTION: sqlite3.Connection
    CONFIGURATION = {}
    UUID_WITH_TWO_PAYMENTS = "c0ffee00beef1234"

    def setUp(self):
        self.CONFIGURATION = {"dbdir": ":memory:"}
        self.CONNECTION = storage.ensure_connection(self.CONFIGURATION)
        payments = [storage.Payment(
                        rowid=1,
                        timestamp=2.5,
                        amount_in_cents=3,
                        comment="unit test comment",
                        uuid=self.UUID_WITH_TWO_PAYMENTS,
                        src_id='src_id_00',
                        bank_ref='ref_src_id_0',
                        other_account='BE515300',
                        other_name='name 0',
                        status='Accepté',
                        confirmation_timestamp=864060.3,
                        active=True,
                        user="unit-test-user",
                        ip="1.2.3.4"),
                    storage.Payment(
                        rowid=2,
                        timestamp=3.0,
                        amount_in_cents=4,
                        comment="second payment for same uuid",
                        uuid=self.UUID_WITH_TWO_PAYMENTS,
                        src_id='src_id_99',
                        bank_ref='ref_src_id_99',
                        other_account='BE515401',
                        other_name='name 1',
                        status='Accepté',
                        user="unit-test-user",
                        ip="1.2.3.4",
                        confirmation_timestamp=None,
                        active=True),
                    storage.Payment(
                        rowid=3,
                        timestamp=5.0,
                        amount_in_cents=4,
                        comment="other unit test comment",
                        uuid="beef12346789fedc",
                        src_id='src_id_02',
                        bank_ref='ref_src_id_2',
                        other_account='BE515502',
                        other_name='name 2',
                        status='Accepté',
                        user="unit-test-user",
                        ip="2.1.4.3",
                        confirmation_timestamp=None,
                        active=True)] + [
                            storage.Payment(
                                rowid=x + (53 if x % 3 == 0 else 28),
                                timestamp = (104.5 if x % 2 == 0 else 99) - x,
                                amount_in_cents=x * (1 + x % 4),
                                comment=f"Auto comment {x}" if x % 2 == 0 else None,
                                uuid=f"01029{x:03x}{x:03x}03040" if x % 3 > 1 else None,
                                src_id=f'src_id_{x + 20:02d}',
                                bank_ref=f'ref_src_id_{x:02d}',
                                other_account=f'BE515603{x:02d}',
                                other_name=f'name 3{x:02d}',
                                status='Accepté',
                                user="other-test-user" if x % 7 == 0 else "unit-test-user",
                                ip=f"1.{x}.3.{x}",
                                confirmation_timestamp=None,
                                active=True,
                            )
                            for x in range(10)
                        ]
        with self.CONNECTION:
            for pmnt in payments:
                pmnt.insert_data(self.CONNECTION)
            make_reservation(civility='', first_name='', name="name1", email="one@example.com", paying_seats=3, outside_main_dessert=1, inside_main_dish=1, inside_main_starter=1, inside_extra_dessert=1, cents_due=12345, bank_id="bank_id_1", uuid=self.UUID_WITH_TWO_PAYMENTS).insert_data(self.CONNECTION)
            make_reservation(civility='', first_name='', name="name2", email="two@example.com", paying_seats=2, outside_main_dessert=1, inside_main_dish=1, inside_third_dish=1, inside_main_starter=2, inside_extra_dessert=1, inside_main_dessert=1, cents_due=34512, bank_id="bank_id_2", uuid="beef12346789fedc").insert_data(self.CONNECTION)

    def tearDown(self):
        if self.CONNECTION:
            self.CONNECTION.close()

    def test_column_ordering_clause(self):
        # It's a class method, but Payment is nicely set up and I have to fix a bug there anyway...
        for col, prefix, expected in [
                ('src_id', None, 'src_id ASC'),
                ('SRC_ID', None, 'src_id DESC'),
                ('src_id', '', 'src_id ASC'),
                ('SRC_ID', '', 'src_id DESC'),
                ('src_id', 'pys', 'pys.src_id ASC'),
                ('user', None, 'LOWER(user) ASC'),
                ('user', 'pys', 'LOWER(pys.user) ASC'),
        ]:
            with self.subTest(col=col, prefix=prefix, expected=expected):
                self.assertEqual(storage.Payment.column_ordering_clause(col, table_id_prefix=prefix),
                                 expected)

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

    def test_join_payments_and_reservations__like_list_payments_cgi(self):
        joined = list(storage.Payment.join_reservations(self.CONNECTION, filtering=[('active', True)], order_columns=['SRC_ID'], limit=20, offset=1))
        self.assertEqual(len(joined), 12)
        self.assertEqual(sum((res is not None for _, res in joined)), 2)
        self.assertEqual(sum((res is not None and res.bank_id == "bank_id_1" for _, res in joined)), 1)
        self.assertEqual(sum((res is not None and res.bank_id == "bank_id_2" for _, res in joined)), 1)

    def test_confirmation_timestamp(self):
        p1 = storage.Payment.find_by_bank_ref(self.CONNECTION, "ref_src_id_0")
        self.assertEqual(p1.confirmation_timestamp, 864060.3)

        p2 = storage.Payment.find_by_bank_ref(self.CONNECTION, "ref_src_id_99")
        self.assertIsNone(p2.confirmation_timestamp)

        with self.CONNECTION:
            p2.update_confirmation_timestamp(self.CONNECTION, 987654.32)

        p2_after = storage.Payment.find_by_bank_ref(self.CONNECTION, p2.bank_ref)
        self.assertEqual(p2_after.confirmation_timestamp, 987654.32)

    def test_hide_payment_associated_with_reservation_fails(self):
        p1 = storage.Payment.find_by_bank_ref(self.CONNECTION, "ref_src_id_0")
        assert p1 is not None
        self.assertTrue(p1.active)

        with self.assertRaises(Exception):
            with self.CONNECTION:
                p1.hide(self.CONNECTION)

        new_p1 = storage.Payment.find_by_bank_ref(self.CONNECTION, p1.bank_ref)
        self.assertTrue(new_p1.active)

    def test_hide_payment_without_reservation_association_succeeds(self):
        p1 = storage.Payment.find_by_bank_ref(self.CONNECTION, "ref_src_id_0")
        with self.CONNECTION:
            p1.update_uuid(self.CONNECTION, None, "unit-test-user", "1.2.3.6")

        with self.CONNECTION:
            p1.hide(self.CONNECTION, 'deactivating-user', '9.8.7.6')

        new_p1 = storage.Payment.find_by_bank_ref(self.CONNECTION, p1.bank_ref)
        self.assertFalse(new_p1.active)
        self.assertEqual(new_p1.user, 'deactivating-user')
        self.assertEqual(new_p1.ip, "9.8.7.6")


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
        for idx, (active, old_uuid, new_uuid) in enumerate([
                (True, None, "res-uuid"), (False, None, "res-uuid"), (True, "res-uuid", None), (True, "res-uuid", "res-uuid")]):
            with self.subTest(idx=idx, active=active, old_uuid=old_uuid, new_uuid=new_uuid):
                with connection:
                    payment = make_payment(
                        timestamp=3.14, active=active, bank_ref=f"bank_ref_{idx}",
                        confirmation_timestamp=6.28, uuid=old_uuid
                    ).insert_data(connection)

                self.assertEqual(
                    payment.active, active, f"Precondition not met: payment.active != {active}")

                before_save = time.time()
                with connection:
                    payment.update_uuid(connection, new_uuid, "the-new-user", "192.0.0.1")
                after_save = time.time()

                reloaded = storage.Payment.find_by_bank_ref(connection, payment.bank_ref)

                if new_uuid is None:
                    self.assertIsNone(reloaded.uuid)
                else:
                    self.assertEqual(reloaded.uuid, new_uuid)
                self.assertEqual(reloaded.user, "the-new-user")
                self.assertEqual(reloaded.ip, "192.0.0.1")
                self.assertEqual(reloaded.comment, payment.comment)
                self.assertEqual(reloaded.amount_in_cents, payment.amount_in_cents)
                self.assertLessEqual(before_save, reloaded.timestamp)
                self.assertLessEqual(reloaded.timestamp, after_save)
                # linking to a reservation always makes the payment active (again)
                self.assertEqual(payment.active, True)
                self.assertEqual(reloaded.active, True)
                if old_uuid == new_uuid:
                    self.assertEqual(reloaded.confirmation_timestamp, 6.28)
                else:
                    # linking to a different reservation always resets the confirmation timestamp
                    self.assertIsNone(reloaded.confirmation_timestamp)

    def test_clear_bank_id(self):
        configuration = {"dbdir": ":memory:"}
        connection = storage.ensure_connection(configuration)
        for idx, blank_uuid in enumerate(("", None)):
            with self.subTest(blank_uuid=blank_uuid):
                src_id = f"the-src-id-{idx}" if idx % 2 == 0 else None
                bank_ref = f"the-ref-{idx}"
                with connection:
                    payment = make_payment(
                        src_id=src_id, bank_ref=bank_ref, timestamp=3.14, uuid="some-uuid-that-is-not-blank"
                    ).insert_data(connection)

                before_save = time.time()
                with connection:
                    payment.update_uuid(connection, blank_uuid, "the-new-user", "192.0.0.1")
                after_save = time.time()

                reloaded = storage.Payment.find_by_bank_ref(connection, payment.bank_ref)

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
