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
           ('div', 'table n°'), ('div', 'serveur'), ('div', 'entrée:'), ('div', 'Fondus au fromage')),
          ('div', (('img', 'src', 'ticket-image.png'),)))

MAIN_STARTER = ((('div', 'class', 'ticket-left-col'),
                 ('div', 'table n°'), ('div', 'serveur'), ('div', 'entrée:'), ('div', 'Assiette italienne')),
                ('div', (('img', 'src', 'ticket-image.png'),)))

BOLO = ((('div', 'class', 'ticket-left-col'),
         ('div', 'table n°'), ('div', 'serveur'), ('div', 'plat:'), ('div', 'Spaghetti bolognaise')),
        ('div', (('img', 'src', 'ticket-image.png'),)))

EXTRA_DISH = ((('div', 'class', 'ticket-left-col'),
            ('div', 'table n°'), ('div', 'serveur'), ('div', 'plat:'), ('div', 'Spaghetti aux scampis')),
           ('div', (('img', 'src', 'ticket-image.png'),)))

DESSERT = ((('div', 'class', 'ticket-left-col'),
             ('div', 'table n°'), ('div', 'serveur'), ('div', 'dessert:'), ('div', 'Dessert')),
            ('div', (('img', 'src', 'ticket-image.png'),)))


class TestOneReservation(unittest.TestCase):
    R1 = make_reservation( # 3 starters + 3 outside_bolo menus + 4 outside_extra_dish + 11 desserts = 27 + 36 + 68 + 66 = 197
        places=8,
        outside_extra_starter=1, outside_main_starter=2,
        outside_bolo=3, outside_extra_dish=4,
        outside_dessert=11)

    R2 = make_reservation(
        name='other', date='2022-03-20',
        places=4,
        outside_extra_starter=1, outside_main_starter=2, outside_bolo=1, outside_extra_dish=1,
        inside_extra_starter=1, inside_bolo=1, kids_extra_dish=1)

    E1 = [(('div', 'class', 'no-print-page-break'),
           (('div', 'class', 'ticket-heading'), 'testing', ': ', '8 places', ' le ', '2022-03-19'),
           ('div', 'Total: ', '197.00 €', ' pour ', '21 tickets', ': ',
            '1+0m fondus, 2+0m assiettes, 3+0m bolos, 4+0m scampis, 11+0m tiramisus', '.')),
          (('div', 'class', 'tickets'),
           *EXTRA_STARTER, *MAIN_STARTER,
           *MAIN_STARTER, *BOLO,
           *BOLO, *BOLO,
           *EXTRA_DISH, *EXTRA_DISH,
           *EXTRA_DISH, *EXTRA_DISH,
           *DESSERT, *DESSERT,
           *DESSERT, *DESSERT,
           *DESSERT, *DESSERT,
           *DESSERT, *DESSERT,
           *DESSERT, *DESSERT,
           *DESSERT)]

    E2 = [(('div', 'class', 'no-print-page-break'),
           (('div', 'class', 'ticket-heading'), 'other', ': ', '4 places', ' le ', '2022-03-20'),
           ('div', 'Total: ', '102.00 €', ' pour ', '10 tickets', ': ',
            '1+1m fondus, 1+1m assiettes, 1+1m bolos, 1+1m scampis, 0+2m dessert', '.')),
          (('div', 'class', 'tickets'),
           *EXTRA_STARTER, *EXTRA_STARTER,
           *MAIN_STARTER, *MAIN_STARTER,
           *BOLO, *BOLO,
           *EXTRA_DISH, *EXTRA_DISH,
           *DESSERT, *DESSERT)]

    def test_example0(self):
        self.assertEqual(
            list(create_tickets.create_tickets_for_one_reservation(
                make_reservation(places=1, outside_extra_starter=1, name='one extra starter'))),
         [(('div', 'class', 'no-print-page-break'),
           (('div', 'class', 'ticket-heading'), 'one extra starter', ': ', '1 place', ' le ', '2022-03-19'),
           ('div', 'Total: ', '9.00 €', ' pour ', '1 ticket', ': ', '1+0m fondus', '.')),
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


class TestFullTicketList(unittest.TestCase):
    def test_example1(self):
        self.assertEqual(
            list(create_tickets.create_full_ticket_list(
                [TestOneReservation.R1, TestOneReservation.R2],
                extra_starter=3,
                main_starter=5,
                bolo=7,
                extra_dish=9,
                kids_bolo=0,
                kids_extra_dish=0,
                dessert=22)),
            [*TestOneReservation.E1,
             *TestOneReservation.E2,
             (('div', 'class', 'ticket-heading'), 'Vente libre'),
             ('div', 'fondus=0, assiettes=1, bolo=2, ', 'scampis=3, dessert=9'),
             (('div', 'class', 'tickets'),
              *MAIN_STARTER, *BOLO,
              *BOLO, *EXTRA_DISH,
              *EXTRA_DISH, *EXTRA_DISH,
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
            ('Not enough tickets: fondus=2, assiettes=1, bolo=0, scampis=-1, dessert=-5',))

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
             ('div', 'fondus=1, assiettes=2, bolo=1, ', 'scampis=2, dessert=3'),
             (('div', 'class', 'tickets'),
              *EXTRA_STARTER, *MAIN_STARTER,
              *MAIN_STARTER, *BOLO,
              *EXTRA_DISH, *EXTRA_DISH,
              *DESSERT, *DESSERT,
              *DESSERT)])
    

if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python3 test_create_tickets.py"
# End:
