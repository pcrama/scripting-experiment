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


class TestOneReservation(unittest.TestCase):
    R1 = make_reservation( # 3 starters + 3 outside_bolo menus + 4 outside_scampis + 11 desserts = 27 + 36 + 68 + 66 = 197
        outside_fondus=1, outside_assiettes=2, outside_bolo=3, outside_scampis=4, outside_tiramisu=5, outside_tranches=6)

    R2 = make_reservation( # 2 starters + 1 outside_bolo + 1 outside_scampis + menu bolo + menu scampis = 18 + 12 + 17 + 25 + 30 = 47
        name='other', date='2022-03-20',
        outside_fondus=1, outside_assiettes=1, outside_bolo=1, outside_scampis=1,
        inside_fondus=1, inside_assiettes=1, inside_bolo=1, inside_scampis=1, inside_tiramisu=2)

    E1 = [(('div', 'class', 'no-print-page-break'),
           ('h3', 'testing', ' ', '2022-03-19'),
           ('p', 'Total: ', '197.00 €', ' pour ', '21 tickets', '.')),
          (('table', 'class', 'tickets'),
           ('tr',
            ('td', 'Fondus au fromage'), ('td', 'Charcuterie'), ('td', 'Charcuterie'), ('td', 'Spaghettis Bolognaise')),
           ('tr',
            ('td', 'Spaghettis Bolognaise'), ('td', 'Spaghettis Bolognaise'), ('td', 'Spaghettis aux scampis'), ('td', 'Spaghettis aux scampis')),
           ('tr',
            ('td', 'Spaghettis aux scampis'), ('td', 'Spaghettis aux scampis'), ('td', 'Tiramisu'), ('td', 'Tiramisu')),
           ('tr',
            ('td', 'Tiramisu'), ('td', 'Tiramisu'), ('td', 'Tiramisu'), ('td', 'Tranche Napolitaine')),
           ('tr',
            ('td', 'Tranche Napolitaine'), ('td', 'Tranche Napolitaine'), ('td', 'Tranche Napolitaine'), ('td', 'Tranche Napolitaine')),
           ('tr',
            ('td', 'Tranche Napolitaine'), ('td', '-x-x-'), ('td', '-x-x-'), ('td', '-x-x-')))]

    E2 = [(('div', 'class', 'no-print-page-break'),
           ('h3', 'other', ' ', '2022-03-20'),
           ('p', 'Total: ', '102.00 €', ' pour ', '10 tickets', '.')),
          (('table', 'class', 'tickets'),
           ('tr',
            ('td', 'Fondus au fromage'), ('td', 'Fondus au fromage'), ('td', 'Charcuterie'), ('td', 'Charcuterie')),
           ('tr',
            ('td', 'Spaghettis Bolognaise'), ('td', 'Spaghettis Bolognaise'), ('td', 'Spaghettis aux scampis'), ('td', 'Spaghettis aux scampis')),
           ('tr',
            ('td', 'Tiramisu'), ('td', 'Tiramisu'), ('td', '-x-x-'), ('td', '-x-x-')))]

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
                fondus=3,
                assiettes=5,
                bolo=7,
                scampis=9,
                tiramisu=10,
                tranches=12)),
            [*TestOneReservation.E1,
             *TestOneReservation.E2,
             ('h3', 'Vente libre'),
             ('p', 'fondus=0, assiettes=1, bolo=2, ', 'scampis=3, tiramisu=3, tranches=6'),
             (('table', 'class', 'tickets'),
              ('tr', ('td', 'Charcuterie'), ('td', 'Spaghettis Bolognaise'), ('td', 'Spaghettis Bolognaise'), ('td', 'Spaghettis aux scampis')),
              ('tr', ('td', 'Spaghettis aux scampis'), ('td', 'Spaghettis aux scampis'), ('td', 'Tiramisu'), ('td', 'Tiramisu')),
              ('tr', ('td', 'Tiramisu'), ('td', 'Tranche Napolitaine'), ('td', 'Tranche Napolitaine'), ('td', 'Tranche Napolitaine')),
              ('tr', ('td', 'Tranche Napolitaine'), ('td', 'Tranche Napolitaine'), ('td', 'Tranche Napolitaine'), ('td', '-x-x-')))])

    def test_example2(self):
        with self.assertRaises(Exception) as cm:
            # wrap in list to force all elements of the iterable
            list(create_tickets.create_full_ticket_list(
                [TestOneReservation.R1, TestOneReservation.R2],
                fondus=3,
                assiettes=3,
                bolo=3,
                scampis=3,
                tiramisu=3,
                tranches=3))
        self.assertEqual(
            cm.exception.args,
            ('Not enough tickets: fondus=2, assiettes=1, bolo=0, scampis=-1, tiramisu=-2, tranches=-3',))

    def test_reservations_without_tickets_elided(self):
        self.assertEqual(
            list(create_tickets.create_full_ticket_list(
                (make_reservation(name=f'user {idx}') for idx in range(3)),
                fondus=1,
                assiettes=2,
                bolo=1,
                scampis=2,
                tiramisu=1,
                tranches=2)),
            [('h3', 'Vente libre'),
             ('p', 'fondus=1, assiettes=2, bolo=1, ', 'scampis=2, tiramisu=1, tranches=2'),
             (('table', 'class', 'tickets'),
              ('tr', ('td', 'Fondus au fromage'), ('td', 'Charcuterie'), ('td', 'Charcuterie'), ('td', 'Spaghettis Bolognaise')),
              ('tr', ('td', 'Spaghettis aux scampis'), ('td', 'Spaghettis aux scampis'), ('td', 'Tiramisu'), ('td', 'Tranche Napolitaine')),
              ('tr', ('td', 'Tranche Napolitaine'), ('td', '-x-x-'), ('td', '-x-x-'), ('td', '-x-x-')))])
    

if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python test_create_tickets.py"
# End:
