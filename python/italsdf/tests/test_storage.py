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
                 name='n1',
                 email='n1@e.com',
                 extra_comment='nn1',
                 places=1,
                 date='2024-03-23',
                 outside=storage.FullMealCount(main_starter=0, extra_starter=0, main_dish=1, extra_dish=0, third_dish=0, main_dessert=0, extra_dessert=1),
                 inside=storage.MenuCount(main_starter=0, extra_starter=2, main_dish=1, extra_dish=0, third_dish=1, main_dessert=1, extra_dessert=1),
                 kids=storage.KidMealCount(main_dish=2, extra_dish=0, third_dish=0, main_dessert=2, extra_dessert=0),
                 gdpr_accepts_use=True,
                 cents_due=1234,
                 bank_id='bank_id_1',
                 uuid='uuid_1',
                 time=3.14,
                 active=True,
                 origin=None).insert_data(cls.connection)
            storage.Reservation(
                 name='n2',
                 email='n2@f.com',
                 extra_comment='mm2',
                 places=4,
                 date='2024-03-23',
                 outside=storage.FullMealCount(main_starter=1, extra_starter=1, main_dish=0, extra_dish=0, third_dish=0, main_dessert=1, extra_dessert=1),
                 inside=storage.MenuCount(main_starter=1, extra_starter=2, main_dish=1, extra_dish=1, third_dish=1, main_dessert=2, extra_dessert=1),
                 kids=storage.KidMealCount(main_dish=0, extra_dish=0, third_dish=0, main_dessert=0, extra_dessert=0),
                 gdpr_accepts_use=True,
                 cents_due=2345,
                 bank_id='bank_id_2',
                 uuid='uuid_2',
                 time=1.41,
                 active=True,
                 origin=None).insert_data(cls.connection)
            storage.Reservation(
                 name='n3',
                 email='n3@g.com',
                 extra_comment='pp3',
                 places=4,
                 date='2024-03-23',
                 outside=storage.FullMealCount(main_starter=1, extra_starter=1, main_dish=0, extra_dish=0, third_dish=0, main_dessert=1, extra_dessert=1),
                 inside=storage.MenuCount(main_starter=1, extra_starter=2, main_dish=1, extra_dish=1, third_dish=1, main_dessert=2, extra_dessert=1),
                 kids=storage.KidMealCount(main_dish=3, extra_dish=0, third_dish=0, main_dessert=1, extra_dessert=2),
                 gdpr_accepts_use=True,
                 cents_due=2345,
                 bank_id='bank_id_3',
                 uuid='uuid_3',
                 time=1.71,
                 active=False,
                 origin='admin').insert_data(cls.connection)
            storage.Reservation(
                 name='n1',
                 email='n1@e.com',
                 extra_comment='mm4',
                 places=5,
                 date='2099-12-31',
                 outside=storage.FullMealCount(main_starter=2, extra_starter=2, main_dish=1, extra_dish=1, third_dish=1, main_dessert=2, extra_dessert=3),
                 inside=storage.MenuCount(main_starter=2, extra_starter=3, main_dish=1, extra_dish=2, third_dish=2, main_dessert=3, extra_dessert=2),
                 kids=storage.KidMealCount(main_dish=2, extra_dish=0, third_dish=0, main_dessert=1, extra_dessert=1),
                 gdpr_accepts_use=True,
                 cents_due=3456,
                 bank_id='bank_id_4',
                 uuid='uuid_4',
                 time=2.72,
                 active=True,
                 origin=None).insert_data(cls.connection)

    def test_count_places(self):
        self.assertEqual(storage.Reservation.count_places(self.connection), (3, 10))
        self.assertEqual(storage.Reservation.count_places(self.connection, name='n1'), (2, 6))
        self.assertEqual(storage.Reservation.count_places(self.connection, name='N1', email='N2@F.COM'), (3, 10))

    def test_count_menu_data(self):
        self.assertEqual(storage.Reservation.count_menu_data(self.connection), (3, 6, 10, 5, 4, 5, 4, 0, 0, 12, 10))
        self.assertEqual(storage.Reservation.count_menu_data(self.connection, '2099-12-31'), (1, 4, 5, 2, 3, 3, 2, 0, 0, 6, 6))

    def test_parse_from_row_simple_reservation(self):
        reservation, tail = storage.Reservation.parse_from_row(
            ['name', 'email@example.com', 'extra_comment', 333, '2024-03-23',
             1, 2, 3, 4, 5, 6, 7,
             8, 9, 10, 11, 12, 13, 14,
             15, 16, 17, 18, 19,
             True, 100, 'bank_id', 'uuid', 3.1415, True, 'origin'])
        self.assertIsNotNone(reservation)
        self.assertEqual(tail, [])
        self.assertEqual(reservation.name, 'name')
        self.assertEqual(reservation.email, 'email@example.com')
        self.assertEqual(reservation.extra_comment, 'extra_comment')
        self.assertEqual(reservation.places, 333)
        self.assertEqual(reservation.date, '2024-03-23')
        self.assertEqual(reservation.outside.main_starter, 1)
        self.assertEqual(reservation.outside.extra_starter, 2)
        self.assertEqual(reservation.outside.main_dish, 3)
        self.assertEqual(reservation.outside.extra_dish, 4)
        self.assertEqual(reservation.outside.third_dish, 5)
        self.assertEqual(reservation.outside.main_dessert, 6)
        self.assertEqual(reservation.outside.extra_dessert, 7)
        self.assertEqual(reservation.inside.main_starter, 8)
        self.assertEqual(reservation.inside.extra_starter, 9)
        self.assertEqual(reservation.inside.main_dish, 10)
        self.assertEqual(reservation.inside.extra_dish, 11)
        self.assertEqual(reservation.inside.third_dish, 12)
        self.assertEqual(reservation.inside.main_dessert, 13)
        self.assertEqual(reservation.inside.extra_dessert, 14)
        self.assertEqual(reservation.kids.main_dish, 15)
        self.assertEqual(reservation.kids.extra_dish, 16)
        self.assertEqual(reservation.kids.third_dish, 17)
        self.assertEqual(reservation.kids.main_dessert, 18)
        self.assertEqual(reservation.kids.extra_dessert, 19)
        self.assertEqual(reservation.gdpr_accepts_use, True)
        self.assertEqual(reservation.cents_due, 100)
        self.assertEqual(reservation.bank_id, 'bank_id')
        self.assertEqual(reservation.uuid, 'uuid')
        self.assertEqual(reservation.timestamp, 3.1415)
        self.assertEqual(reservation.active, True)
        self.assertEqual(reservation.origin, 'origin')

    def test_only_main_dishes_are_allowed_for_kids(self):
        for extra_dish, third_dish in ((1, 0), (0, 1)):
            with self.subTest(extra_dish=extra_dish, third_dish=third_dish):
                reservation = storage.Reservation(
                                      name=f'e={extra_dish} t={third_dish}',
                                      email=f'ne{extra_dish}t{third_dish}@e.com',
                                      extra_comment='',
                                      places=1,
                                      date='2099-12-31',
                                      outside=storage.FullMealCount(main_starter=2, extra_starter=2, main_dish=1, extra_dish=1, third_dish=1, main_dessert=2, extra_dessert=3),
                                      inside=storage.MenuCount(main_starter=2, extra_starter=3, main_dish=1, extra_dish=2, third_dish=2, main_dessert=3, extra_dessert=2),
                                      kids=storage.KidMealCount(main_dish=0, extra_dish=extra_dish, third_dish=third_dish, main_dessert=extra_dish + third_dish, extra_dessert=0),
                                      gdpr_accepts_use=True,
                                      cents_due=3456,
                                      bank_id=f'bank_id_e{extra_dish}_t{third_dish}',
                                      uuid=f'uuid_e{extra_dish}_t{third_dish}',
                                      time=2.72,
                                      active=True,
                                      origin=None)
                # extra dish or third_dish should raise ...
                self.assertRaises(sqlite3.IntegrityError, reservation.insert_data, self.connection)
                # ... but not main dish
                reservation.kids.main_dish, reservation.kids.extra_dish, reservation.kids.third_dish = extra_dish + third_dish, 0, 0
                reservation.insert_data(self.connection)

class TestPayments(unittest.TestCase):
    CONNECTION: sqlite3.Connection
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
                        confirmation_timestamp=864060.3,
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
                        ip="1.2.3.4",
                        confirmation_timestamp=None),
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
                        ip="2.1.4.3",
                        confirmation_timestamp=None)] + [
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
                                confirmation_timestamp=None,
                            )
                            for x in range(10)
                        ]
        with cls.CONNECTION:
            for pmnt in payments:
                pmnt.insert_data(cls.CONNECTION)
            make_reservation(name="name1", email="one@example.com", places=3, outside_main_dessert=1, inside_main_dish=1, inside_main_starter=1, inside_extra_dessert=1, cents_due=12345, bank_id="bank_id_1", uuid=cls.UUID_WITH_TWO_PAYMENTS).insert_data(cls.CONNECTION)
            make_reservation(name="name2", email="two@example.com", places=2, outside_main_dessert=1, inside_main_dish=1, inside_third_dish=1, inside_main_starter=2, inside_extra_dessert=1, inside_main_dessert=1, cents_due=34512, bank_id="bank_id_2", uuid="beef12346789fedc").insert_data(cls.CONNECTION)

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

    def test_confirmation_timestamp(self):
        p1 = storage.Payment.find_by_src_id(self.CONNECTION, "src_id_0")
        self.assertEqual(p1.confirmation_timestamp, 864060.3)

        p2 = storage.Payment.find_by_src_id(self.CONNECTION, "src_id_1")
        self.assertIsNone(p2.confirmation_timestamp)

        with self.CONNECTION:
            p2.update_confirmation_timestamp(self.CONNECTION, 987654.32)

        p2_after = storage.Payment.find_by_src_id(self.CONNECTION, p2.src_id)
        self.assertEqual(p2_after.confirmation_timestamp, 987654.32)
            


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
