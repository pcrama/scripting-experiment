import unittest

import sys_path_hack
from conftest import make_reservation

with sys_path_hack.app_in_path():
    import htmlgen
    import pricing
    import storage


class PriceInEurosTests(unittest.TestCase):
    def test_examples(self):
        for cents, euros in ((0, '0.00'),
                             (1, '0.01'),
                             (100, '1.00'),
                             (123, '1.23'),
                             (10120, '101.20'),
                             (9009, '90.09')):
            with self.subTest(cents=cents, euros=euros):
                self.assertEqual(htmlgen.cents_to_euro(cents), euros)


class PriceInCentsTests(unittest.TestCase):
    def test_main_starter(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_main_starter=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_main_starter=1), outside_main_starter=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_main_starter=2), outside_main_starter=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_main_starter=3)), 2250)


    def test_extra_starter(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_extra_starter=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_extra_starter=1), outside_extra_starter=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_extra_starter=2), outside_extra_starter=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_extra_starter=3)), 2250)


    def test_bolo(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_bolo=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_bolo=1), outside_bolo=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_bolo=2), outside_bolo=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_bolo=3)), 4500)


    def test_extra_dish(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_extra_dish=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_extra_dish=1), outside_extra_dish=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_extra_dish=2), outside_extra_dish=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_extra_dish=3)), 4500)


    def test_dessert(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_dessert=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_dessert=1), outside_dessert=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_dessert=2), outside_dessert=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_dessert=3)), 2250)


    def test_inside_bolo(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_bolo=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_bolo=1), inside_bolo=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_bolo=2), inside_bolo=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_bolo=3)), 8100)


    def test_inside_extra_dish(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_extra_dish=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_extra_dish=1), inside_extra_dish=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_extra_dish=2), inside_extra_dish=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_extra_dish=3)), 8100)


    def test_combinations_pricing(self):
        for combination, expected in (
                ({'inside_bolo': 2, 'inside_extra_dish': 3}, 13500),
                ({'inside_bolo': 2, 'inside_extra_dish': 3, 'outside_bolo': 1}, 15000),
                ({'inside_bolo': 2, 'inside_extra_dish': 3, 'outside_dessert': 2, 'outside_bolo': 1}, 16500),
                ({'inside_bolo': 1, 'inside_extra_dish': 2, 'outside_main_starter': 1, 'outside_dessert': 2, 'outside_bolo': 1}, 11850),
                ({'outside_main_starter': 3, 'outside_bolo': 4}, 8250),
                ({'outside_extra_starter': 1, 'outside_main_starter': 2}, 2250),
                ({'outside_extra_starter': 1, 'outside_main_starter': 1, 'outside_dessert': 2}, 3000),
                ({'outside_main_starter': 1, 'outside_bolo': 1, 'outside_dessert': 1}, 3000),
                ({'outside_main_starter': 1, 'outside_extra_dish': 1, 'outside_dessert': 1}, 3000),
                ({'outside_extra_starter': 2, 'outside_extra_dish': 2, 'outside_dessert': 2}, 6000),
                ({'outside_extra_starter': 2, 'outside_extra_dish': 2, 'outside_bolo': 1, 'outside_dessert': 2}, 7500),
                ({'outside_extra_starter': 2, 'outside_extra_dish': 1, 'outside_bolo': 1, 'outside_dessert': 3}, 6750)):
            with self.subTest(**combination):
                self.assertEqual(pricing.price_in_cents(make_reservation(**combination)), expected)


if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python3 test_pricing.py"
# End:
