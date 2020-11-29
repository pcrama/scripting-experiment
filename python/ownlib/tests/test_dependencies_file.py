import unittest
from ..dependencies_file import *


class DependenciesTestCases(unittest.TestCase):
    def test_Dependency(self):
        self.assertEqual(repr(Dependency('a', 'b', 'c', 'd')),
                         "Dependency('a', 'b', 'c', 'd')")


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


def assert_dependencies_are_equal(dependency, other):
    try:
        are_equal = (dependency.dependency_path == other.dependency_path and
                     dependency.commit_ish == other.commit_ish and
                     dependency.clone_url == other.clone_url)
    except Exception as e:
        raise AssertionError(
            f'{dependency!r} or {other!r} is not a Dependency: {e}')
    if are_equal:
        return True
    raise AssertionError(f'{dependency!r} != {other!r}')


class BuildDependenciesListTestCases(unittest.TestCase):
    def test_given_empty_dependencies_list__when_building_dependencies_list__then_return_empty_list(self):
        self.assert_dependencies_lists_are_equal(
            build_dependencies_list([]), [])

    def test_given_dependencies_list_without_dependency_specification__when_building_dependencies_list__then_return_empty_list(self):
        self.assert_dependencies_lists_are_equal(
            build_dependencies_list([
                CommentLine('# Comment 1'),
                AssignmentLine('#= <var> = value', 'var', 'value')]),
            [])

    def test_given_dependencies_list_with_dependency_specifications__when_building_dependencies_list__then_return_dependencies(self):
        x = build_dependencies_list([
                CommentLine('# Comment 1'),
                AssignmentLine('#= <var> = value', 'var', 'value'),
                DependencySpecification(
                    'name branch url', 'name', 'branch', 'url'),
                DependencySpecification(
                    'other branch url', 'other', 'branch', 'url')])
        self.assert_dependencies_lists_are_equal(
            x,
            [Dependency('name', 'branch', 'url', 'name branch url'),
             Dependency('other', 'branch', 'url', 'other branch url')])

    def test_given_dependencies_list_with_dependency_specifications_and_variables__when_building_dependencies_list__then_return_dependencies(self):
        self.assert_dependencies_lists_are_equal(
            build_dependencies_list([
                CommentLine('# Comment 1'),
                AssignmentLine('#= <var> = value', 'var', 'value'),
                DependencySpecification(
                    'name branch url', 'name', 'branch', 'url'),
                DependencySpecification(
                    'other branch <var>', 'other', 'branch', '<var>'),
                DependencySpecification(
                    'n<var> b<var> u<var>', 'n<var>', 'b<var>', 'u<var>')]),
            [Dependency('name', 'branch', 'url', 'name branch url'),
             Dependency('other', 'branch', 'value', 'other branch <var>'),
             Dependency('nvalue', 'bvalue', 'uvalue', 'n<var> b<var> u<var>')])

    def assert_dependencies_lists_are_equal(self, list1, list2):
        self.assertEqual(len(list1), len(list2))
        for x, y in zip(list1, list2):
            assert_dependencies_are_equal(x, y)


class ReplaceVariablesTestCases(unittest.TestCase):
    def test_examples(self):
        for (test_input, expected) in (
                (('<var>', {'var': '<foo>', 'foo': 'bar'}), '<foo>'),
                (('<foo><bar>', {'foo': 'FO<O', 'bar': 'B>AR', 'OB': '123'}),
                 'FO<OB>AR'),
                (('<var><var><var>', {'var': 'value'}), 'valuevaluevalue'),
                (('a<var>b>c', {'var': 'value'}), 'avalueb>c'),
                (('a<b<var>c', {'var': 'value'}), 'a<bvaluec'),
                (('t<var', {'var': 'value'}), 't<var'),
        ):
            with self.subTest(test_input=test_input):
                self.assertEqual(
                    replace_variables(*test_input),
                    expected)

    def test_variable_unknown(self):
        with self.assertRaises(KeyError):
            replace_variables('<var>', {})


class ParseDependencyLinesIteratorTests(unittest.TestCase):
    def test_example(self):
        COMMENT_LINE = '# comment'
        ASSIGNMENT_LINE = '#= <var>=value'
        DEPENDENCY_LINE = 'name tag url'
        lines = [dl for dl in parse_dependency_lines_iterator(
            'name',
            [COMMENT_LINE,
             ASSIGNMENT_LINE,
             DEPENDENCY_LINE])]
        self.assertEqual(len(lines), 3)
        self.assertIsInstance(lines[0], CommentLine)
        self.assertEqual(lines[0].line.strip(), COMMENT_LINE)
        self.assertIsInstance(lines[1], AssignmentLine)
        self.assertEqual(lines[1].line.strip(), ASSIGNMENT_LINE)
        self.assertIsInstance(lines[2], DependencySpecification)
        self.assertEqual(lines[2].line.strip(), DEPENDENCY_LINE)
        for (idx, dep_line) in enumerate(lines):
            self.assertEqual(dep_line.line.line_number, idx + 1)
            self.assertEqual(dep_line.line.file_name, 'name')
