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
                             (9009, '90.09'),
                             (-3360, '-33.60')):
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
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_main_starter=3)), 2700)


    def test_extra_starter(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_extra_starter=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_extra_starter=1), outside_extra_starter=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_extra_starter=2), outside_extra_starter=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_extra_starter=3)), 2700)


    def test_main_dish(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_main_dish=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_main_dish=1), outside_main_dish=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_main_dish=2), outside_main_dish=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_main_dish=3)), 3600)


    def test_extra_dish(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_extra_dish=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_extra_dish=1), outside_extra_dish=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_extra_dish=2), outside_extra_dish=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_extra_dish=3)), 5100)


    def test_third_dish(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_third_dish=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_third_dish=1), outside_third_dish=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_third_dish=2), outside_third_dish=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_third_dish=3)), 3600)


    def test_dessert(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_main_dessert=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_main_dessert=1), outside_dessert=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_extra_dessert=2), outside_dessert=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(outside_main_dessert=1, outside_extra_dessert=2)), 1800)


    def test_inside_main_dish(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_main_dish=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_main_dish=1), inside_main_dish=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_main_dish=2), inside_main_dish=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_main_dish=3)), 7500)


    def test_inside_extra_dish(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_extra_dish=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_extra_dish=1), inside_extra_dish=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_extra_dish=2), inside_extra_dish=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_extra_dish=3)), 9000)


    def test_inside_third_dish(self):
        with self.subTest(count=0):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_third_dish=0)), 0)
        with self.subTest(count=1):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_third_dish=1), inside_third_dish=6), 6)
        with self.subTest(count=2):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_third_dish=2), inside_third_dish=6), 12)
        with self.subTest(count=3):
            self.assertEqual(pricing.price_in_cents(make_reservation(inside_third_dish=3)), 7500)


    def test_kids_menu(self):
        self.assertEqual(pricing.price_in_cents(make_reservation(
            kids_main_dish=1, kids_extra_dish=2, kids_third_dish=6, kids_main_dessert=4, kids_extra_dessert=5), kids_main_dish=1, kids_extra_dish=100, kids_third_dish=10000),
                         60201)


    def test_combinations_pricing(self):
        for combination, expected in (
                ({'inside_main_starter': 4, 'inside_extra_starter': 1,
                  'inside_main_dish': 2, 'inside_extra_dish': 3,
                  'inside_main_dessert': 0, 'inside_extra_dessert': 5}, 14000),
                ({'inside_main_starter': 1, 'inside_extra_starter': 4,
                  'inside_main_dish': 1, 'inside_extra_dish': 3, 'inside_third_dish': 1,
                  'outside_main_dish': 1,
                  'inside_main_dessert': 4, 'inside_extra_dessert': 1}, 15200),
                ({'inside_main_starter': 1, 'inside_extra_starter': 4,
                  'inside_main_dish': 0, 'inside_extra_dish': 3, 'inside_third_dish': 2,
                  'outside_third_dish': 1,
                  'outside_main_dessert': 1, 'outside_extra_dessert': 1,
                  'inside_main_dessert': 3, 'inside_extra_dessert': 2}, 16400),
                ({'inside_extra_starter': 1, 'inside_third_dish': 1, 'inside_extra_dessert': 1,
                  'outside_main_starter': 1, 'outside_main_dish': 1, 'outside_main_dessert': 2}, 5800),
                ({'outside_main_starter': 3, 'outside_main_dish': 4}, 7500),
                ({'outside_main_starter': 3, 'outside_main_dish': 4,
                  'kids_main_dish': 1, 'kids_main_dessert': 1}, 9100),
                ({'outside_extra_starter': 1, 'outside_main_starter': 2,
                  'kids_third_dish': 2, 'kids_extra_dessert': 2}, 5900),
                ({'outside_extra_starter': 1, 'outside_main_starter': 1, 'outside_extra_dessert': 2}, 3000),
                ({'outside_main_starter': 1, 'outside_main_dish': 1, 'outside_main_dessert': 1,
                  'kids_extra_dish': 1, 'kids_main_dessert': 1}, 4800),
                ({'outside_main_starter': 1, 'outside_extra_dish': 1, 'outside_extra_dessert': 1}, 3200),
                ({'outside_extra_starter': 1, 'outside_third_dish': 1, 'outside_extra_dessert': 1}, 2700),
                ({'outside_extra_starter': 2, 'outside_extra_dish': 2, 'outside_main_dessert': 2}, 6400),
                ({'outside_extra_starter': 2, 'outside_extra_dish': 2, 'outside_main_dish': 1, 'outside_extra_dessert': 2}, 7600),
                ({'outside_extra_starter': 2, 'outside_extra_dish': 1, 'outside_main_dish': 1, 'outside_main_dessert': 3}, 6500)):
            with self.subTest(**combination):
                reservation = make_reservation(**combination)
                self.assertEqual(reservation.validate(), [])
                self.assertEqual(pricing.price_in_cents(make_reservation(**combination)), expected)


if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python3 test_pricing.py"
# End:
