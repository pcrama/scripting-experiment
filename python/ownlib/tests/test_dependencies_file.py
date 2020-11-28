import unittest
from ..dependencies_file import *


class CommentLineTestCases(unittest.TestCase):
    def test_CommentLine(self):
        x = CommentLine(1)
        self.assertEqual(repr(x), 'CommentLine(1)')


class InputLineTestCases(unittest.TestCase):
    def test_given_InputLine__when_calling_strip__then_no_whitespace_at_extremities(self):
        x = InputLine(' \ttest \n', 1)
        self.assertEqual(x.strip(), 'test')

    def test_given_InputLine__when_no_filename__then_repr_shows_only_2_parameters(self):
        x = InputLine('a', 2)
        self.assertEqual(repr(x), "InputLine('a', 2)")

    def test_given_InputLine__when_filename__then_repr_shows_3_parameters(self):
        x = InputLine('a', 3, 'f')
        self.assertEqual(repr(x), "InputLine('a', 3, 'f')")
