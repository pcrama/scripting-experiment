import os
import unittest

from ..filesystem import *


class FindGitRootTests(unittest.TestCase):
    def test_given_no_explicit_current_dir__when_find_git_root__then_same_as_for_getcwd(self):
        no_explicit = find_git_root()
        explicit = find_git_root(os.getcwd())
        if no_explicit is None:
            self.assertIsNone(explicit)
        else:
            self.assertEqual(no_explicit, explicit)

    def test_given_no_explicit_current_dir__when_find_git_root__then_works(self):
        x = find_git_root()
        self.assertTrue(os.path.exists(x))
        self.assertTrue(x.endswith('.git') or x.endswith('.git/'))
        self.assertTrue(
            os.path.realpath(__file__).startswith(os.path.dirname(x)))
