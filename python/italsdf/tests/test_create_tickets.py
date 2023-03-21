# -*- coding: utf-8 -*-
import itertools
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

BOLO = ((('div', 'class', 'ticket-left-col'),
         ('div', 'table n°'), ('div', 'serveur'), ('div', 'plat:'), ('div', 'bolo')),
        ('div', (('img', 'src', 'bolo_image'),)))

EXTRA_DISH = ((('div', 'class', 'ticket-left-col'),
               ('div', 'table n°'), ('div', 'serveur'), ('div', 'plat:'), ('div', 'extra_dish')),
              ('div', (('img', 'src', 'extra_dish_image'),)))

KIDS_BOLO = ((('div', 'class', 'ticket-left-col'),
              ('div', 'table n°'), ('div', 'serveur'), ('div', 'plat enfant:'), ('div', 'kids_bolo')),
             ('div', (('img', 'src', 'kids_bolo_image'),)))

KIDS_EXTRA_DISH = ((('div', 'class', 'ticket-left-col'),
                    ('div', 'table n°'), ('div', 'serveur'), ('div', 'plat enfant:'), ('div', 'kids_extra_dish')),
                   ('div', (('img', 'src', 'kids_extra_dish_image'),)))

DESSERT = ((('div', 'class', 'ticket-left-col'),
            ('div', 'table n°'), ('div', 'serveur'), ('div', 'dessert:'), ('div', 'dessert')),
           ('div', (('img', 'src', 'dessert_image'),)))


def expected_result_1(expected_price='210.00 €'):
    return [(('div', 'class', 'no-print-page-break'),
             (('div', 'class', 'ticket-heading'), 'testing', ': ', '8 places', ' le ', '2022-03-19'),
             ('div', 'Total dû: ', expected_price, ' pour ', '21 tickets', ': ',
              '0m+2c main_starter, 0m+1c extra_starter, 0m+3c bolo, 0m+4c extra_dish, 0m+11c dessert', '.')),
            (('div', 'class', 'tickets'),
             *MAIN_STARTER, *MAIN_STARTER,
             *EXTRA_STARTER, *BOLO,
             *BOLO, *BOLO,
             *EXTRA_DISH, *EXTRA_DISH,
             *EXTRA_DISH, *EXTRA_DISH,
             *DESSERT, *DESSERT,
             *DESSERT, *DESSERT,
             *DESSERT, *DESSERT,
             *DESSERT, *DESSERT,
             *DESSERT, *DESSERT,
             *DESSERT)]

class ConfiguredTestCase(unittest.TestCase):
    patched_payments = None

    @classmethod
    def setUpClass(cls):
        cls.maxDiff = None
        create_tickets.BOLO_NAME = "bolo"
        create_tickets.BOLO_NAME_PLURAL = "bolos"
        create_tickets.EXTRA_DISH_NAME = "sampis"
        create_tickets.EXTRA_DISH_NAME_PLURAL = "sampis"
        create_tickets.MAIN_STARTER_NAME = "main_starter"
        create_tickets.MAIN_STARTER_NAME_PLURAL = "main_starter_plural"
        create_tickets.EXTRA_STARTER_NAME = "extra_starter"
        create_tickets.EXTRA_STARTER_NAME_PLURAL = "extra_starter_plural"
        create_tickets.BOLO_NAME = "bolo"
        create_tickets.BOLO_NAME_PLURAL = "bolo_plural"
        create_tickets.EXTRA_DISH_NAME = "extra_dish"
        create_tickets.EXTRA_DISH_NAME_PLURAL = "extra_dish_plural"
        create_tickets.DESSERT_NAME = "dessert"
        create_tickets.DESSERT_NAME_PLURAL = "dessert_plural"
        create_tickets.KIDS_BOLO_NAME = "kids_bolo"
        create_tickets.KIDS_BOLO_NAME_PLURAL = "kids_bolo_plural"
        create_tickets.KIDS_EXTRA_DISH_NAME = "kids_extra_dish"
        create_tickets.KIDS_EXTRA_DISH_NAME_PLURAL = "kids_extra_dish_plural"
        create_tickets.MAIN_STARTER_IMAGE = "main_starter_image"
        create_tickets.EXTRA_STARTER_IMAGE = "extra_starter_image"
        create_tickets.BOLO_IMAGE = "bolo_image"
        create_tickets.EXTRA_DISH_IMAGE = "extra_dish_image"
        create_tickets.DESSERT_IMAGE = "dessert_image"
        create_tickets.KIDS_BOLO_IMAGE = "kids_bolo_image"
        create_tickets.KIDS_EXTRA_DISH_IMAGE = "kids_extra_dish_image"
        cls.patched_payments = patch("storage.Payment")
        cls.patched_payments.__enter__().sum_payments.return_value = 0

    @classmethod
    def tearDownClass(cls):
        cls.patched_payments.__exit__(None, None, None)


class TestOneReservation(ConfiguredTestCase):
    R1 = make_reservation( # 3 starters + 3 outside_bolo menus + 4 outside_extra_dish + 11 desserts = 22.50 + 45 + 60 + 82.50 = 210.0
        cents_due=21000,
        places=8,
        outside_extra_starter=1, outside_main_starter=2,
        outside_bolo=3, outside_extra_dish=4,
        outside_dessert=11)

    E1 = expected_result_1()

    R2 = make_reservation( # 3 outside starters + 1 outside bolo + 1 outside extra dish + 1 bolo menu + 1 kids menu = 22.5 + 15 + 15 + 27 + 16 = 95.5
        name='other', date='2022-03-20',
        cents_due=9550,
        places=4,
        outside_extra_starter=1, outside_main_starter=2, outside_bolo=1, outside_extra_dish=1,
        inside_extra_starter=1, inside_bolo=1, kids_extra_dish=1)

    E2 = [(('div', 'class', 'no-print-page-break'),
           (('div', 'class', 'ticket-heading'), 'other', ': ', '4 places', ' le ', '2022-03-20'),
           ('div', 'Total dû: ', '95.50 €', ' pour ', '10 tickets', ': ',
            '0m+2c main_starter, 1m+1c extra_starter, 1m+1c bolo, 0m+1c extra_dish, 1m+0c kids_extra_dish, 2m+0c dessert', '.')),
          (('div', 'class', 'tickets'),
           *MAIN_STARTER, *MAIN_STARTER,
           *EXTRA_STARTER, *EXTRA_STARTER,
           *BOLO, *BOLO,
           *EXTRA_DISH, *KIDS_EXTRA_DISH,
           *DESSERT, *DESSERT)]

    def test_example0(self):
        connection = object()
        self.assertEqual(
            list(create_tickets.create_tickets_for_one_reservation(
                connection,
                make_reservation(places=1, cents_due=750, outside_extra_starter=1, name='one extra starter'))),
         [(('div', 'class', 'no-print-page-break'),
           (('div', 'class', 'ticket-heading'), 'one extra starter', ': ', '1 place', ' le ', '2022-03-19'),
           ('div', 'Total dû: ', '7.50 €', ' pour ', '1 ticket', ': ', '0m+1c extra_starter', '.')),
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
                extra_starter=3,
                main_starter=5,
                bolo=7,
                extra_dish=9,
                kids_bolo=3,
                kids_extra_dish=2,
                dessert=22)),
            [*TestOneReservation.E1,
             *TestOneReservation.E2,
             (('div', 'class', 'ticket-heading'), 'Vente libre'),
             ('div', 'main_starter=1, extra_starter=0, bolo=2, extra_dish=4, kids_bolo=3, kids_extra_dish=1, dessert=9'),
             (('div', 'class', 'tickets'),
              *MAIN_STARTER, *BOLO,
              *BOLO, *EXTRA_DISH,
              *EXTRA_DISH, *EXTRA_DISH, *EXTRA_DISH,
              *KIDS_BOLO, *KIDS_BOLO,
              *KIDS_BOLO, *KIDS_EXTRA_DISH,
              *DESSERT, *DESSERT,
              *DESSERT, *DESSERT,
              *DESSERT, *DESSERT,
              *DESSERT, *DESSERT,
              *DESSERT)])

    def test_example2(self):
        connection = object()
        with self.assertRaises(RuntimeError) as cm:
            # wrap in list to force all elements of the iterable
            list(create_tickets.create_full_ticket_list(
                connection,
                [TestOneReservation.R1, TestOneReservation.R2],
                extra_starter=3,
                main_starter=3,
                bolo=3,
                extra_dish=3,
                kids_bolo=0,
                kids_extra_dish=0,
                dessert=6))
        self.assertEqual(
            cm.exception.args,
            ('Not enough tickets: main_starter=1, extra_starter=2, bolo=0, extra_dish=-1, kids_bolo=0, kids_extra_dish=0, dessert=-5',))

    def test_reservations_without_tickets_elided(self):
        connection = object()
        self.assertEqual(
            list(create_tickets.create_full_ticket_list(
                connection,
                (make_reservation(name=f'user {idx}') for idx in range(3)),
                extra_starter=1,
                main_starter=2,
                bolo=1,
                extra_dish=2,
                kids_bolo=0,
                kids_extra_dish=0,
                dessert=3)),
            [(('div', 'class', 'ticket-heading'), 'Vente libre'),
             ('div', 'main_starter=2, extra_starter=1, bolo=1, extra_dish=2, kids_bolo=0, kids_extra_dish=0, dessert=3'),
             (('div', 'class', 'tickets'),
              *MAIN_STARTER, *MAIN_STARTER,
              *EXTRA_STARTER, *BOLO,
              *EXTRA_DISH, *EXTRA_DISH,
              *DESSERT, *DESSERT,
              *DESSERT)])
    

class UlForMenuDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.maxDiff = None
        create_tickets.BOLO_NAME = "bolo"
        create_tickets.BOLO_NAME_PLURAL = "bolos"
        create_tickets.EXTRA_DISH_NAME = "sampis"
        create_tickets.EXTRA_DISH_NAME_PLURAL = "sampis"
        create_tickets.MAIN_STARTER_NAME = "main_starter"
        create_tickets.MAIN_STARTER_NAME_PLURAL = "main_starter_plural"
        create_tickets.EXTRA_STARTER_NAME = "extra_starter"
        create_tickets.EXTRA_STARTER_NAME_PLURAL = "extra_starter_plural"
        create_tickets.BOLO_NAME = "bolo"
        create_tickets.BOLO_NAME_PLURAL = "bolo_plural"
        create_tickets.EXTRA_DISH_NAME = "extra_dish"
        create_tickets.EXTRA_DISH_NAME_PLURAL = "extra_dish_plural"
        create_tickets.DESSERT_NAME = "dessert"
        create_tickets.DESSERT_NAME_PLURAL = "dessert_plural"
        create_tickets.KIDS_BOLO_NAME = "kids_bolo"
        create_tickets.KIDS_BOLO_NAME_PLURAL = "kids_bolo_plural"
        create_tickets.KIDS_EXTRA_DISH_NAME = "kids_extra_dish"
        create_tickets.KIDS_EXTRA_DISH_NAME_PLURAL = "kids_extra_dish_plural"
        create_tickets.MAIN_STARTER_IMAGE = "main_starter_image"
        create_tickets.EXTRA_STARTER_IMAGE = "extra_starter_image"
        create_tickets.BOLO_IMAGE = "bolo_image"
        create_tickets.EXTRA_DISH_IMAGE = "extra_dish_image"
        create_tickets.DESSERT_IMAGE = "dessert_image"
        create_tickets.KIDS_BOLO_IMAGE = "kids_bolo_image"
        create_tickets.KIDS_EXTRA_DISH_IMAGE = "kids_extra_dish_image"

    def test_full_example(self):
        self.assertEqual(
            create_tickets.ul_for_menu_data(
                total_main_starter=1,
                total_extra_starter=2,
                total_bolo=3,
                total_extra_dish=4,
                total_kids_bolo=5,
                total_kids_extra_dish=0,
                total_dessert=7),
            ('ul',
             ('li', '1 main_starter'),
                ('li', '2 extra_starter_plural'),
                ('li', '3 bolo_plural'),
                ('li', '4 extra_dish_plural'),
                ('li', '5 kids_bolo_plural'),
                ('li', '0 kids_extra_dish_plural'),
                ('li', '7 dessert_plural')))


if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python3 test_create_tickets.py"
# End:
