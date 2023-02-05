# -*- coding: utf-8 -*-
import itertools
import unittest

import sys_path_hack

with sys_path_hack.app_in_path():
    import create_tickets
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


class ConfiguredTestCase(unittest.TestCase):
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


class TestOneReservation(ConfiguredTestCase):
    R1 = make_reservation( # 3 starters + 3 outside_bolo menus + 4 outside_extra_dish + 11 desserts = 22.50 + 45 + 60 + 82.50 = 210.0
        places=8,
        outside_extra_starter=1, outside_main_starter=2,
        outside_bolo=3, outside_extra_dish=4,
        outside_dessert=11)

    E1 = [(('div', 'class', 'no-print-page-break'),
           (('div', 'class', 'ticket-heading'), 'testing', ': ', '8 places', ' le ', '2022-03-19'),
           ('div', 'Total: ', '210.00 €', ' pour ', '21 tickets', ': ',
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

    R2 = make_reservation( # 3 outside starters + 1 outside bolo + 1 outside extra dish + 1 bolo menu + 1 kids menu = 22.5 + 15 + 15 + 27 + 16 = 95.5
        name='other', date='2022-03-20',
        places=4,
        outside_extra_starter=1, outside_main_starter=2, outside_bolo=1, outside_extra_dish=1,
        inside_extra_starter=1, inside_bolo=1, kids_extra_dish=1)

    E2 = [(('div', 'class', 'no-print-page-break'),
           (('div', 'class', 'ticket-heading'), 'other', ': ', '4 places', ' le ', '2022-03-20'),
           ('div', 'Total: ', '95.50 €', ' pour ', '10 tickets', ': ',
            '0m+2c main_starter, 1m+1c extra_starter, 1m+1c bolo, 0m+1c extra_dish, 1m+0c kids_extra_dish, 2m+0c dessert', '.')),
          (('div', 'class', 'tickets'),
           *MAIN_STARTER, *MAIN_STARTER,
           *EXTRA_STARTER, *EXTRA_STARTER,
           *BOLO, *BOLO,
           *EXTRA_DISH, *KIDS_EXTRA_DISH,
           *DESSERT, *DESSERT)]

    def test_example0(self):
        self.assertEqual(
            list(create_tickets.create_tickets_for_one_reservation(
                make_reservation(places=1, outside_extra_starter=1, name='one extra starter'))),
         [(('div', 'class', 'no-print-page-break'),
           (('div', 'class', 'ticket-heading'), 'one extra starter', ': ', '1 place', ' le ', '2022-03-19'),
           ('div', 'Total: ', '7.50 €', ' pour ', '1 ticket', ': ', '0m+1c extra_starter', '.')),
          (('div', 'class', 'tickets'),
           *EXTRA_STARTER)])

    def test_example1(self):
        self.assertEqual(
            list(create_tickets.create_tickets_for_one_reservation(self.R1)),
            self.E1)

    def test_example2(self):
        self.assertEqual(
            list(create_tickets.create_tickets_for_one_reservation(self.R2)),
            self.E2)


class TestFullTicketList(ConfiguredTestCase):
    def test_example1(self):
        self.assertEqual(
            list(create_tickets.create_full_ticket_list(
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
        with self.assertRaises(RuntimeError) as cm:
            # wrap in list to force all elements of the iterable
            list(create_tickets.create_full_ticket_list(
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
        self.assertEqual(
            list(create_tickets.create_full_ticket_list(
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
    

if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python3 test_create_tickets.py"
# End:
