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


class PriceInEurosTests(unittest.TestCase):
    def test_examples(self):
        for cents, euros in ((1, '0.01 €'),
                             (100, '1.00 €'),
                             (123, '1.23 €'),
                             (10120, '101.20 €'),
                             (9009, '90.09 €')):
            with self.subTest(cents=cents, euros=euros):
                self.assertEqual(
                    pricing.price_in_euros(make_reservation(assiettes=1), assiettes=cents),
                    euros)


class PriceInCentsTests(unittest.TestCase):
    def test_assiettes(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(assiettes=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(assiettes=1), assiettes=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(assiettes=2), assiettes=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(assiettes=3)), 2400)


    def test_fondus(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(fondus=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(fondus=1), fondus=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(fondus=2), fondus=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(fondus=3)), 2400)


    def test_bolo(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(bolo=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(bolo=1), bolo=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(bolo=2), bolo=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(bolo=3)), 4500)


    def test_scampis(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(scampis=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(scampis=1), scampis=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(scampis=2), scampis=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(scampis=3)), 5400)


    def test_pannacotta(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(pannacotta=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(pannacotta=1), pannacotta=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(pannacotta=2), pannacotta=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(pannacotta=3)), 1800)


    def test_tranches(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(tranches=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(tranches=1), tranches=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(tranches=2), tranches=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(tranches=3)), 1800)

    def test_combinations_but_no_full_menus(self):
        for combination, expected in (
                ({'assiettes': 3, 'bolo': 4}, 8400),
                ({'fondus': 1, 'assiettes': 2}, 2400),
                ({'fondus': 1, 'assiettes': 1, 'pannacotta': 1, 'tranches': 1}, 2800)):
            with self.subTest(**combination):
                self.assertEqual(pricing.price_in_cents(make_reservation(**combination)), expected)

    def test_simple_menus_pricing(self):
        for combination, expected in (
                ({'assiettes': 1, 'bolo': 1, 'tranches': 1}, 2500),
                ({'assiettes': 1, 'scampis': 1, 'tranches': 1}, 2800),
                ({'fondus': 2, 'scampis': 2, 'pannacotta': 2}, 5600)):
            with self.subTest(**combination):
                self.assertEqual(pricing.price_in_cents(make_reservation(**combination)), expected)


if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python test_pricing.py"
# End:
