import unittest

import sys_path_hack

with sys_path_hack.app_in_path():
    import pricing
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


class PriceInEurosTests(unittest.TestCase):
    def test_examples(self):
        for cents, euros in ((1, '0.01 €'),
                             (100, '1.00 €'),
                             (123, '1.23 €'),
                             (10120, '101.20 €'),
                             (9009, '90.09 €')):
            with self.subTest(cents=cents, euros=euros):
                self.assertEqual(
                    pricing.price_in_euros(make_reservation(outside_assiettes=1), outside_assiettes=cents),
                    euros)


class PriceInCentsTests(unittest.TestCase):
    def test_assiettes(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_assiettes=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_assiettes=1), outside_assiettes=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_assiettes=2), outside_assiettes=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_assiettes=3)), 2700)


    def test_fondus(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_fondus=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_fondus=1), outside_fondus=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_fondus=2), outside_fondus=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_fondus=3)), 2700)


    def test_bolo(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_bolo=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_bolo=1), outside_bolo=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_bolo=2), outside_bolo=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_bolo=3)), 3600)


    def test_scampis(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_scampis=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_scampis=1), outside_scampis=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_scampis=2), outside_scampis=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_scampis=3)), 5100)


    def test_tiramisu(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_tiramisu=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_tiramisu=1), outside_tiramisu=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_tiramisu=2), outside_tiramisu=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_tiramisu=3)), 1800)


    def test_tranches(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_tranches=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_tranches=1), outside_tranches=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_tranches=2), outside_tranches=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_tranches=3)), 1800)


    def test_inside_bolo(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_bolo=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_bolo=1), inside_bolo=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_bolo=2), inside_bolo=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_bolo=3)), 7500)


    def test_inside_scampis(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_scampis=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_scampis=1), inside_scampis=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_scampis=2), inside_scampis=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_scampis=3)), 9000)


    def test_combinations_pricing(self):
        for combination, expected in (
                ({'inside_bolo': 2, 'inside_scampis': 3}, 14000),
                ({'inside_bolo': 2, 'inside_scampis': 3, 'outside_bolo': 1}, 15200),
                ({'inside_bolo': 2, 'inside_scampis': 3, 'outside_tranches': 2, 'outside_bolo': 1}, 16400),
                ({'inside_bolo': 1, 'inside_scampis': 2, 'outside_assiettes': 1, 'outside_tranches': 2, 'outside_bolo': 1}, 11800),
                ({'outside_assiettes': 3, 'outside_bolo': 4}, 7500),
                ({'outside_fondus': 1, 'outside_assiettes': 2}, 2700),
                ({'outside_fondus': 1, 'outside_assiettes': 1, 'outside_tiramisu': 1, 'outside_tranches': 1}, 3000),
                ({'outside_assiettes': 1, 'outside_bolo': 1, 'outside_tranches': 1}, 2700),
                ({'outside_assiettes': 1, 'outside_scampis': 1, 'outside_tranches': 1}, 3200),
                ({'outside_fondus': 2, 'outside_scampis': 2, 'outside_tiramisu': 2}, 6400),
                ({'outside_fondus': 2, 'outside_scampis': 2, 'outside_bolo': 1, 'outside_tiramisu': 2}, 7600),
                ({'outside_fondus': 2, 'outside_scampis': 1, 'outside_bolo': 1, 'outside_tiramisu': 2, 'outside_tranches': 1}, 6500)):
            with self.subTest(**combination):
                self.assertEqual(pricing.price_in_cents(make_reservation(**combination)), expected)


if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python test_pricing.py"
# End:
