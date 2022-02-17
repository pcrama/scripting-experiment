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
        fondus=0,
        assiettes=0,
        bolo=0,
        scampis=0,
        pannacotta=0,
        tranches=0,
        gdpr_accepts_use=True,
        uuid='deadbeef',
        time=12345678.9,
        active=True,
        origin='unit tests')
    defaults.update(**overrides)
    return storage.Reservation(**defaults)


class TestOneReservation(unittest.TestCase):
    R1 = make_reservation( # 3 bolo menus + 4 scampis + 8 desserts = 60 + 60 + 40 = 160
        fondus=1, assiettes=2, bolo=3, scampis=4, pannacotta=5, tranches=6)

    R2 = make_reservation( # 2 starters + 1 bolo + 1 scampis = 16 + 10 + 15 = 41
        name='other', date='2022-03-20', fondus=1, assiettes=1, bolo=1, scampis=1)

    E1 = [(('div', 'class', 'no-print-page-break'),
           ('h3', 'testing', ' ', '2022-03-19'),
           ('p', 'Total: ', '160.00 €', ' pour ', '21 tickets', '.')),
          (('table', 'class', 'tickets'),
           ('tr',
            ('td', 'Fondus au fromage'), ('td', 'Charcuterie'), ('td', 'Charcuterie'), ('td', 'Spaghettis Bolognaise')),
           ('tr',
            ('td', 'Spaghettis Bolognaise'), ('td', 'Spaghettis Bolognaise'), ('td', 'Spaghettis aux scampis'), ('td', 'Spaghettis aux scampis')),
           ('tr',
            ('td', 'Spaghettis aux scampis'), ('td', 'Spaghettis aux scampis'), ('td', 'Pannacotta'), ('td', 'Pannacotta')),
           ('tr',
            ('td', 'Pannacotta'), ('td', 'Pannacotta'), ('td', 'Pannacotta'), ('td', 'Tranche Napolitaine')),
           ('tr',
            ('td', 'Tranche Napolitaine'), ('td', 'Tranche Napolitaine'), ('td', 'Tranche Napolitaine'), ('td', 'Tranche Napolitaine')),
           ('tr',
            ('td', 'Tranche Napolitaine'), ('td', '-x-x-'), ('td', '-x-x-'), ('td', '-x-x-')))]

    E2 = [(('div', 'class', 'no-print-page-break'),
           ('h3', 'other', ' ', '2022-03-20'),
           ('p', 'Total: ', '41.00 €', ' pour ', '4 tickets', '.')),
          (('table', 'class', 'tickets'),
           ('tr',
            ('td', 'Fondus au fromage'), ('td', 'Charcuterie'), ('td', 'Spaghettis Bolognaise'), ('td', 'Spaghettis aux scampis')))]

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
                pannacotta=10,
                tranches=12)),
            [*TestOneReservation.E1,
             *TestOneReservation.E2,
             ('h3', 'Vente libre'),
             ('p', 'fondus=1, assiettes=2, bolo=3, ', 'scampis=4, pannacotta=5, tranches=6'),
             (('table', 'class', 'tickets'),
              ('tr', ('td', 'Fondus au fromage'), ('td', 'Charcuterie'), ('td', 'Charcuterie'), ('td', 'Spaghettis Bolognaise')),
              ('tr', ('td', 'Spaghettis Bolognaise'), ('td', 'Spaghettis Bolognaise'), ('td', 'Spaghettis aux scampis'), ('td', 'Spaghettis aux scampis')),
              ('tr', ('td', 'Spaghettis aux scampis'), ('td', 'Spaghettis aux scampis'), ('td', 'Pannacotta'), ('td', 'Pannacotta')),
              ('tr', ('td', 'Pannacotta'), ('td', 'Pannacotta'), ('td', 'Pannacotta'), ('td', 'Tranche Napolitaine')),
              ('tr', ('td', 'Tranche Napolitaine'), ('td', 'Tranche Napolitaine'), ('td', 'Tranche Napolitaine'), ('td', 'Tranche Napolitaine')),
              ('tr', ('td', 'Tranche Napolitaine'), ('td', '-x-x-'), ('td', '-x-x-'), ('td', '-x-x-')))])

    def test_example2(self):
        with self.assertRaises(Exception) as cm:
            # wrap in list to force all elements of the iterable
            list(create_tickets.create_full_ticket_list(
                [TestOneReservation.R1, TestOneReservation.R2],
                fondus=3,
                assiettes=3,
                bolo=3,
                scampis=3,
                pannacotta=3,
                tranches=3))
        self.assertEqual(
            cm.exception.args,
            ('Not enough tickets: fondus=2, assiettes=1, bolo=0, scampis=-1, pannacotta=-2, tranches=-3',))

    def test_reservations_without_tickets_elided(self):
        self.assertEqual(
            list(create_tickets.create_full_ticket_list(
                (make_reservation(name=f'user {idx}') for idx in range(3)),
                fondus=1,
                assiettes=2,
                bolo=1,
                scampis=2,
                pannacotta=1,
                tranches=2)),
            [('h3', 'Vente libre'),
             ('p', 'fondus=1, assiettes=2, bolo=1, ', 'scampis=2, pannacotta=1, tranches=2'),
             (('table', 'class', 'tickets'),
              ('tr', ('td', 'Fondus au fromage'), ('td', 'Charcuterie'), ('td', 'Charcuterie'), ('td', 'Spaghettis Bolognaise')),
              ('tr', ('td', 'Spaghettis aux scampis'), ('td', 'Spaghettis aux scampis'), ('td', 'Pannacotta'), ('td', 'Tranche Napolitaine')),
              ('tr', ('td', 'Tranche Napolitaine'), ('td', '-x-x-'), ('td', '-x-x-'), ('td', '-x-x-')))])
    

if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python test_create_tickets.py"
# End:
