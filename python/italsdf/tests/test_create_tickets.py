# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch

import sys_path_hack
from conftest import make_reservation

with sys_path_hack.app_in_path():
    import create_tickets
    import storage


EXTRA_STARTER = ((('div', 'class', 'ticket-left-col'),
                  ('div', 'table n°'), ('div', 'serveur'), ('div', 'entrée:'), ('div', 'extra_starter')),
                 ('div', (('img', 'src', 'extra_starter_image'),)))

MAIN_STARTER = ((('div', 'class', 'ticket-left-col'),
                 ('div', 'table n°'), ('div', 'serveur'), ('div', 'entrée:'), ('div', 'main_starter')),
                ('div', (('img', 'src', 'main_starter_image'),)))

MAIN_DISH = ((('div', 'class', 'ticket-left-col'),
              ('div', 'table n°'), ('div', 'serveur'), ('div', 'plat:'), ('div', 'bolo')),
             ('div', (('img', 'src', 'main_dish_image'),)))

EXTRA_DISH = ((('div', 'class', 'ticket-left-col'),
               ('div', 'table n°'), ('div', 'serveur'), ('div', 'plat:'), ('div', 'extra_dish')),
              ('div', (('img', 'src', 'extra_dish_image'),)))

THIRD_DISH = ((('div', 'class', 'ticket-left-col'),
               ('div', 'table n°'), ('div', 'serveur'), ('div', 'plat:'), ('div', 'third_dish')),
              ('div', (('img', 'src', 'third_dish_image'),)))

KIDS_MAIN_DISH = ((('div', 'class', 'ticket-left-col'),
                   ('div', 'table n°'), ('div', 'serveur'), ('div', 'plat enfant:'), ('div', 'kids_main_dish')),
                  ('div', (('img', 'src', 'kids_main_dish_image'),)))

KIDS_EXTRA_DISH = ((('div', 'class', 'ticket-left-col'),
                    ('div', 'table n°'), ('div', 'serveur'), ('div', 'plat enfant:'), ('div', 'kids_extra_dish')),
                   ('div', (('img', 'src', 'kids_extra_dish_image'),)))

KIDS_THIRD_DISH = ((('div', 'class', 'ticket-left-col'),
                    ('div', 'table n°'), ('div', 'serveur'), ('div', 'plat enfant:'), ('div', 'kids_third_dish')),
                   ('div', (('img', 'src', 'kids_third_dish_image'),)))

MAIN_DESSERT = ((('div', 'class', 'ticket-left-col'),
                 ('div', 'table n°'), ('div', 'serveur'), ('div', 'dessert:'), ('div', 'main_dessert')),
                ('div', (('img', 'src', 'main_dessert_image'),)))

EXTRA_DESSERT = ((('div', 'class', 'ticket-left-col'),
                  ('div', 'table n°'), ('div', 'serveur'), ('div', 'dessert:'), ('div', 'extra_dessert')),
                 ('div', (('img', 'src', 'extra_dessert_image'),)))


def expected_result_1(expected_price='210.00 €'):
    return [(('div', 'class', 'no-print-page-break'),
             (('div', 'class', 'ticket-heading'), 'testing', ': ', '8 places', ' le ', '2022-03-19'),
             ('div', 'Total dû: ', expected_price, ' pour ', '21 tickets', ': ',
              '0m+2c main_starter, 0m+1c extra_starter, 0m+2c bolo, 0m+4c extra_dish, 0m+1c third_dish, 0m+4c main_dessert, 0m+7c extra_dessert', '.')),
            (('div', 'class', 'tickets'),
             *MAIN_STARTER, *MAIN_STARTER,
             *EXTRA_STARTER, *MAIN_DISH,
             *MAIN_DISH, *EXTRA_DISH,
             *EXTRA_DISH, *EXTRA_DISH,
             *EXTRA_DISH, *THIRD_DISH,
             *MAIN_DESSERT, *MAIN_DESSERT,
             *MAIN_DESSERT, *MAIN_DESSERT,
             *EXTRA_DESSERT, *EXTRA_DESSERT,
             *EXTRA_DESSERT, *EXTRA_DESSERT,
             *EXTRA_DESSERT, *EXTRA_DESSERT,
             *EXTRA_DESSERT)]


class ConfiguredTestCase(unittest.TestCase):
    patched_payments = None

    @classmethod
    def setUpClass(cls):
        cls.maxDiff = None
        create_tickets.MAIN_STARTER_NAME = "main_starter"
        create_tickets.MAIN_STARTER_NAME_PLURAL = "main_starter_plural"
        create_tickets.EXTRA_STARTER_NAME = "extra_starter"
        create_tickets.EXTRA_STARTER_NAME_PLURAL = "extra_starter_plural"
        create_tickets.MAIN_DISH_NAME = "bolo"
        create_tickets.MAIN_DISH_NAME_PLURAL = "main_dish_plural"
        create_tickets.EXTRA_DISH_NAME = "extra_dish"
        create_tickets.EXTRA_DISH_NAME_PLURAL = "extra_dish_plural"
        create_tickets.THIRD_DISH_NAME = "third_dish"
        create_tickets.THIRD_DISH_NAME_PLURAL = "third_dish_plural"
        create_tickets.MAIN_DESSERT_NAME = "main_dessert"
        create_tickets.MAIN_DESSERT_NAME_PLURAL = "main_dessert_plural"
        create_tickets.EXTRA_DESSERT_NAME = "extra_dessert"
        create_tickets.EXTRA_DESSERT_NAME_PLURAL = "extra_dessert_plural"
        create_tickets.KIDS_MAIN_DISH_NAME = "kids_main_dish"
        create_tickets.KIDS_MAIN_DISH_NAME_PLURAL = "kids_main_dish_plural"
        create_tickets.KIDS_EXTRA_DISH_NAME = "kids_extra_dish"
        create_tickets.KIDS_EXTRA_DISH_NAME_PLURAL = "kids_extra_dish_plural"
        create_tickets.KIDS_THIRD_DISH_NAME = "kids_third_dish"
        create_tickets.KIDS_THIRD_DISH_NAME_PLURAL = "kids_third_dish_plural"
        create_tickets.MAIN_STARTER_IMAGE = "main_starter_image"
        create_tickets.EXTRA_STARTER_IMAGE = "extra_starter_image"
        create_tickets.MAIN_DISH_IMAGE = "main_dish_image"
        create_tickets.EXTRA_DISH_IMAGE = "extra_dish_image"
        create_tickets.THIRD_DISH_IMAGE = "third_dish_image"
        create_tickets.MAIN_DESSERT_IMAGE = "main_dessert_image"
        create_tickets.EXTRA_DESSERT_IMAGE = "extra_dessert_image"
        create_tickets.KIDS_MAIN_DISH_IMAGE = "kids_main_dish_image"
        create_tickets.KIDS_EXTRA_DISH_IMAGE = "kids_extra_dish_image"
        create_tickets.KIDS_THIRD_DISH_IMAGE = "kids_third_dish_image"
        cls.patched_payments = patch("storage.Payment")
        cls.patched_payments.__enter__().sum_payments.return_value = 0

    @classmethod
    def tearDownClass(cls):
        cls.patched_payments.__exit__(None, None, None)


class TestOneReservation(ConfiguredTestCase):
    R1 = make_reservation(
        cents_due=21000,
        places=8,
        outside_extra_starter=1, outside_main_starter=2,
        outside_main_dish=2, outside_extra_dish=4, outside_third_dish=1,
        outside_main_dessert=4, outside_extra_dessert=7)

    E1 = expected_result_1()

    R2 = make_reservation(
        name='other', date='2022-03-20',
        cents_due=9550,
        places=4,
        outside_extra_starter=1, outside_main_starter=2, outside_main_dish=1, outside_extra_dish=1,
        inside_extra_starter=1, inside_main_dish=1, inside_main_dessert=1,
        kids_third_dish=1, kids_extra_dessert=1)

    E2 = [(('div', 'class', 'no-print-page-break'),
           (('div', 'class', 'ticket-heading'), 'other', ': ', '4 places', ' le ', '2022-03-20'),
           ('div', 'Total dû: ', '95.50 €', ' pour ', '10 tickets', ': ',
            '0m+2c main_starter, 1m+1c extra_starter, 1m+1c bolo, 0m+1c extra_dish, 1m+0c kids_third_dish, 1m+0c main_dessert, 1m+0c extra_dessert', '.')),
          (('div', 'class', 'tickets'),
           *MAIN_STARTER, *MAIN_STARTER,
           *EXTRA_STARTER, *EXTRA_STARTER,
           *MAIN_DISH, *MAIN_DISH,
           *EXTRA_DISH, *KIDS_THIRD_DISH,
           *MAIN_DESSERT, *EXTRA_DESSERT)]

    def test_example0(self):
        connection = object()
        self.assertEqual(
            list(create_tickets.create_tickets_for_one_reservation(
                connection,
                make_reservation(places=1, cents_due=905, outside_extra_starter=1, name='one extra starter'))),
         [(('div', 'class', 'no-print-page-break'),
           (('div', 'class', 'ticket-heading'), 'one extra starter', ': ', '1 place', ' le ', '2022-03-19'),
           ('div', 'Total dû: ', '9.05 €', ' pour ', '1 ticket', ': ', '0m+1c extra_starter', '.')),
          (('div', 'class', 'tickets'),
           *EXTRA_STARTER)])

    def test_example1(self):
        connection = object()
        self.assertEqual(
            list(create_tickets.create_tickets_for_one_reservation(connection, self.R1)),
            self.E1)

    def test_example2(self):
        connection = object()
        self.assertEqual(
            list(create_tickets.create_tickets_for_one_reservation(connection, self.R2)),
            self.E2)

    def test_example1_with_pre_payed(self):
        connection = object()
        with patch("storage.Payment") as patched_payments:
            patched_payments.sum_payments.return_value = 1000
            self.assertEqual(
                list(create_tickets.create_tickets_for_one_reservation(connection, self.R1)),
                expected_result_1("200.00 €"))


class TestFullTicketList(ConfiguredTestCase):
    def test_example1(self):
        connection = object()
        self.assertEqual(
            list(create_tickets.create_full_ticket_list(
                connection,
                [TestOneReservation.R1, TestOneReservation.R2],
                main_starter=5,
                extra_starter=3,
                main_dish=6,
                extra_dish=9,
                third_dish=3,
                kids_main_dish=3,
                kids_extra_dish=1,
                kids_third_dish=1,
                main_dessert=11,
                extra_dessert=11)),
            [*TestOneReservation.E1,
             *TestOneReservation.E2,
             (('div', 'class', 'ticket-heading'), 'Vente libre'),
             ('div', 'main_starter=1, extra_starter=0, bolo=2, extra_dish=4, third_dish=2, kids_main_dish=3, kids_extra_dish=1, kids_third_dish=0, main_dessert=6, extra_dessert=3'),
             (('div', 'class', 'tickets'),
              *MAIN_STARTER, *MAIN_DISH,
              *MAIN_DISH, *EXTRA_DISH,
              *EXTRA_DISH, *EXTRA_DISH, *EXTRA_DISH,
              *THIRD_DISH, *THIRD_DISH,
              *KIDS_MAIN_DISH, *KIDS_MAIN_DISH,
              *KIDS_MAIN_DISH, *KIDS_EXTRA_DISH,
              *MAIN_DESSERT, *MAIN_DESSERT,
              *MAIN_DESSERT, *MAIN_DESSERT,
              *MAIN_DESSERT, *MAIN_DESSERT,
              *EXTRA_DESSERT, *EXTRA_DESSERT,
              *EXTRA_DESSERT)])

    def test_example2(self):
        connection = object()
        with self.assertRaises(RuntimeError) as cm:
            # wrap in list to force all elements of the iterable
            list(create_tickets.create_full_ticket_list(
                connection,
                [TestOneReservation.R1, TestOneReservation.R2],
                main_starter=3,
                extra_starter=3,
                main_dish=3,
                extra_dish=3,
                third_dish=0,
                kids_main_dish=0,
                kids_extra_dish=0,
                kids_third_dish=1,
                main_dessert=2,
                extra_dessert=6))
        self.assertEqual(
            cm.exception.args,
            ('Not enough tickets: main_starter=1, extra_starter=2, bolo=1, extra_dish=-1, third_dish=-1, kids_main_dish=0, kids_extra_dish=0, kids_third_dish=1, main_dessert=-2, extra_dessert=-1',))

    def test_reservations_without_tickets_elided(self):
        connection = object()
        self.assertEqual(
            list(create_tickets.create_full_ticket_list(
                connection,
                (make_reservation(name=f'user {idx}') for idx in range(3)),
                extra_starter=1,
                main_starter=2,
                main_dish=1,
                extra_dish=2,
                third_dish=1,
                kids_main_dish=1,
                kids_extra_dish=0,
                kids_third_dish=2,
                main_dessert=3,
                extra_dessert=1)),
            [(('div', 'class', 'ticket-heading'), 'Vente libre'),
             ('div', 'main_starter=2, extra_starter=1, bolo=1, extra_dish=2, third_dish=1, kids_main_dish=1, kids_extra_dish=0, kids_third_dish=2, main_dessert=3, extra_dessert=1'),
             (('div', 'class', 'tickets'),
              *MAIN_STARTER, *MAIN_STARTER,
              *EXTRA_STARTER, *MAIN_DISH,
              *EXTRA_DISH, *EXTRA_DISH,
              *THIRD_DISH, *KIDS_MAIN_DISH,
              *KIDS_THIRD_DISH, *KIDS_THIRD_DISH,
              *MAIN_DESSERT, *MAIN_DESSERT,
              *MAIN_DESSERT, *EXTRA_DESSERT)])
    

class UlForMenuDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.maxDiff = None
        create_tickets.MAIN_STARTER_NAME = "main_starter"
        create_tickets.MAIN_STARTER_NAME_PLURAL = "main_starter_plural"
        create_tickets.EXTRA_STARTER_NAME = "extra_starter"
        create_tickets.EXTRA_STARTER_NAME_PLURAL = "extra_starter_plural"
        create_tickets.MAIN_DISH_NAME = "bolo"
        create_tickets.MAIN_DISH_NAME_PLURAL = "main_dish_plural"
        create_tickets.EXTRA_DISH_NAME = "extra_dish"
        create_tickets.EXTRA_DISH_NAME_PLURAL = "extra_dish_plural"
        create_tickets.EXTRA_DESSERT_NAME = "extra_dessert"
        create_tickets.EXTRA_DESSERT_NAME_PLURAL = "extra_dessert_plural"
        create_tickets.KIDS_MAIN_DISH_NAME = "kids_main_dish"
        create_tickets.KIDS_MAIN_DISH_NAME_PLURAL = "kids_main_dish_plural"
        create_tickets.KIDS_EXTRA_DISH_NAME = "kids_extra_dish"
        create_tickets.KIDS_EXTRA_DISH_NAME_PLURAL = "kids_extra_dish_plural"
        create_tickets.MAIN_STARTER_IMAGE = "main_starter_image"
        create_tickets.EXTRA_STARTER_IMAGE = "extra_starter_image"
        create_tickets.MAIN_DISH_IMAGE = "main_dish_image"
        create_tickets.EXTRA_DISH_IMAGE = "extra_dish_image"
        create_tickets.EXTRA_DESSERT_IMAGE = "extra_dessert_image"
        create_tickets.KIDS_MAIN_DISH_IMAGE = "kids_main_dish_image"
        create_tickets.KIDS_EXTRA_DISH_IMAGE = "kids_extra_dish_image"

    def test_full_example(self):
        self.assertEqual(
            create_tickets.ul_for_menu_data(
                total_main_starter=1,
                total_extra_starter=2,
                total_main_dish=3,
                total_extra_dish=4,
                total_third_dish=7,
                total_kids_main_dish=5,
                total_kids_extra_dish=0,
                total_kids_third_dish=8,
                total_main_dessert=6,
                total_extra_dessert=1),
            ('ul',
             ('li', '1 main_starter'),
                ('li', '2 extra_starter_plural'),
                ('li', '3 main_dish_plural'),
                ('li', '4 extra_dish_plural'),
                ('li', '7 third_dish_plural'),
                ('li', '5 kids_main_dish_plural'),
                ('li', '0 kids_extra_dish_plural'),
                ('li', '8 kids_third_dish_plural'),
                ('li', '6 main_dessert_plural'),
                ('li', '1 extra_dessert')))


if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python3 test_create_tickets.py"
# End:
