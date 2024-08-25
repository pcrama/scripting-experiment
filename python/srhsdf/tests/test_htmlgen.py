# -*- coding: utf-8 -*-
import time
import unittest
from unittest.mock import patch

import conftest


try:
    import app.htmlgen as htmlgen
except ImportError:
    import sys_path_hack
    with sys_path_hack.app_in_path():
        import htmlgen

class FormatBankId(unittest.TestCase):
    def test_with_valid_bank_id(self):
        self.assertEqual(htmlgen.format_bank_id('123456789012'), '+++123/4567/89012+++')
        self.assertEqual(htmlgen.format_bank_id(htmlgen.format_bank_id('123456789012')), '+++123/4567/89012+++')

    def test_with_invalid_bank_id(self):
        self.assertEqual(htmlgen.format_bank_id('invalid'), 'invalid')


class PlurielNaif(unittest.TestCase):
    def test_with_1_simple_plural(self):
        self.assertEqual(htmlgen.pluriel_naif(1, 'pomme'), '1 pomme')

    def test_with_0_simple_plural(self):
        self.assertEqual(htmlgen.pluriel_naif(0, 'pomme'), '0 pommes')

    def test_with_2_simple_plural(self):
        self.assertEqual(htmlgen.pluriel_naif(2, 'pomme'), '2 pommes')

    def test_with_1_complex_plural(self):
        self.assertEqual(htmlgen.pluriel_naif(1, ['bocal', 'bocaux']), '1 bocal')

    def test_with_0_complex_plural(self):
        self.assertEqual(htmlgen.pluriel_naif(0, ['bocal', 'bocaux']), '0 bocaux')

    def test_with_2_complex_plural(self):
        self.assertEqual(htmlgen.pluriel_naif(2, ['bocal', 'bocaux']), '2 bocaux')


class CentsToEuro(unittest.TestCase):
    def test_examples(self):
        for (cents, expected) in [(100, '1.00'), (123, '1.23'), (20, '0.20'), (3, '0.03'), (3001, '30.01'),
                                  (-1, '-0.01'), (-19, '-0.19'), (-99, '-0.99'), (-12345, '-123.45')]:
            with self.subTest(cents=cents, expected=expected):
                self.assertEqual(htmlgen.cents_to_euro(cents), expected)


# Local Variables:
# compile-command: "python3 test_htmlgen.py"
# End:
