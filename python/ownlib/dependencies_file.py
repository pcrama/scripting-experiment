'''Support for parsing a Dependencies.txt file

A Dependencies.txt lists dependencies to clone/checkout at a given commit-ish_
from a repository.  It supports comments, any line starting with ``#`` and
variable definition and substitution.

A dependency is specified like this:

::

    awesome_lib    version/1.0.0.0    https://example.com/awesome_lib.git

This would mean that ``awesome_lib`` must be cloned from
``https://example.com/awesome_lib.git`` if necessary and checked out (detached
HEAD) at tag ``version/1.0.0.0``.

Variable definition is a special case of a comment, it is introduced by ``#=``:

::

    #= <variable_name> = new value

This creates (or overrides an existing variable) named ``variable_name`` and
assigns it the value ``new value``.  Whitespace at the end of a line is
ignored.

Variable substitution can be used to factor out common parts in the dependency
specifications.  Variable substitution is *not* recursive, i.e. after

::
    #= <a> = foo
    #= <b> = <a><a>

``b`` is ``<a><a>``, not ``foofoo``.

It is meant to avoid repeating e.g. the git repository host:

::
    #= <githost> = https://example.com
    awesome_lib    version/1.0.0.0    <githost>/awesome_lib.git
    cool_lib       version/2.3.4      <githost>/cool_lib.git

is equivalent to

::
    awesome_lib    version/1.0.0.0    https://example.com/awesome_lib.git
    cool_lib       version/2.3.4      https://example.com/cool_lib.git

.. commit-ish_: https://git-scm.com/docs/gitglossary#Documentation/gitglossary.txt-aiddefcommit-ishacommit-ishalsocommittish

'''

import re

from typing import Dict, Iterator, List, Optional, TypeVar


class Dependency:
    '''Information about a repository to clone as a dependency'''
    def __init__(
            self,
            dependency_path,
            commit_ish,
            clone_url,
            dependency_file_line):
        self.dependency_path = dependency_path
        self.commit_ish = commit_ish
        self.clone_url = clone_url
        self.dependency_file_line = dependency_file_line

    def __repr__(self):
        return (f'Dependency({self.dependency_path!r}, {self.commit_ish!r}, '
                f'{self.clone_url!r}, {self.dependency_file_line!r})')

    def real_path(self, main_project):
        '''Get the real path where this dependency should be cloned/checked out

        :param main_project: git directory or git.Repo object of the main
        project (i.e. the container of Dependecies.txt)

        :returns: the real path (no .git at the end)'''
        try:
            git_dir = main_project.git_dir
        except AttributeError:
            # assume main_project is a string
            git_dir = main_project

        from . import get_dependency_real_path
        return get_dependency_real_path(git_dir, self.dependency_path)


def parse_dependency_file(
        dependency_file: str) -> Iterator["DependencyFileLine"]:
    '''Yield successive parsed lines of a Dependencies.txt file

    See :py:func:`parse_line` & :py:func:`parse_dependency_lines_iterator`'''
    with open(dependency_file, 'r') as file:
        for line in parse_dependency_lines_iterator(dependency_file, file):
            yield line


def parse_dependency_lines_iterator(
        name: str, dependency_lines: Iterator[str]
) -> Iterator["DependencyFileLine"]:
    '''Yield successive parsed lines of an iterator

    :param name: name of file from which lines are pulled

    :param dependency_lines: lines iterator

    See also :py:func:`parse_line`'''
    for (line_number, line) in enumerate(dependency_lines, start=1):
        yield parse_line(InputLine(line, line_number, name))


def replace_variables(s: str, variables: Dict[str, str]) -> str:
    '''Replace <var> in the input string with the values in the variables dict

    >>> replace_variables('var', { 'var': 'value' })
    'var'
    >>> replace_variables('<var>', { 'var': 'value' })
    'value'
    >>> replace_variables('<foo>baz<bar>', { 'foo': 'boo', 'bar': 'car' })
    'boobazcar'
    '''
    result: List[str] = []
    idx = 0
    while True:
        next_angle_bracket = s.find('<', idx)
        if next_angle_bracket < 0:
            return ''.join(result) + s[idx:]
        result.append(s[idx:next_angle_bracket])
        idx = next_angle_bracket + 1
        closing_bracket = s.find('>', idx)
        if closing_bracket < 0:
            return ''.join(result) + s[idx-1:]
        next_angle_bracket = s.find('<', idx)
        if closing_bracket < next_angle_bracket or next_angle_bracket < 0:
            variable_name = s[idx:closing_bracket]
            idx = closing_bracket + 1
            result.append(variables[variable_name])
        elif next_angle_bracket > 0:
            result.append(s[next_angle_bracket])


def build_dependencies_list(lines) -> List[Dependency]:
    '''Go through lines of dependencies and build py:ref:`Dependency` list'''
    result: List[Dependency] = []
    variables: Dict[str, str] = {}
    for dependency_line in lines:
        try:
            result.append(dependency_line.to_dependency(variables))
        except AttributeError:
            try:
                dependency_line.update_variables(variables)
            except AttributeError:
                pass
    return result


class ParseError(Exception):
    '''Error raised during parsing of a Dependencies.txt file'''
    def __init__(self, message, line):
        super().__init__(message)
        self.line = line

    @property
    def message(self):
        return self.args[0]

    def __repr__(self):
        return f'ParseError({self.message!r}, {self.line!r})'

    def __str__(self):
        try:
            location = self.line.location()
        except Exception:
            location = repr(self.line)
        return f'Parse error: {self.message} in {location}.'


class InputLine:
    def __init__(self, line, line_number, file_name=None):
        self.line = line
        self.line_number = line_number
        self.file_name = file_name

    def __repr__(self):
        last_param = '' if self.file_name is None else f', {self.file_name!r}'
        return f'InputLine({self.line!r}, {self.line_number!r}{last_param})'

    def strip(self):
        return self.line.strip()

    def location(self):
        '''Format the InputLine's location for display (e.g. in error messages)

        >>> InputLine('a', 1).location()
        "line 1: 'a'"
        >>> InputLine('b', 2, 'Dependencies.txt').location()
        "Dependencies.txt(2): 'b'"
        '''
        if self.file_name is None:
            return f'line {self.line_number}: {self.line!r}'
        else:
            return f'{self.file_name}({self.line_number}): {self.line!r}'


class DependencyFileLine:
    def __init__(self, line):
        self.line = line


class CommentLine(DependencyFileLine):
    PREFIX = '#'

    def __repr__(self):
        return f'CommentLine({self.line!r})'


class AssignmentLine(DependencyFileLine):
    PREFIX = CommentLine.PREFIX + '='
    REGEXP = re.compile(
        # Wrap characters of PREFIX in `[]' to make single-character classes,
        # effectively quoting them (the `#' in PREFIX would otherwise
        # introduce a comment, see re.VERBOSE)
        ''.join(f'[{c}]' for c in PREFIX) +
        r'''\s*                      # any number of spaces
            <(?P<variable_name>\w+)> # named group of >0 alphanumeric
            \s*                      # any number of spaces
            =
            \s*                      # any number of spaces
            (?P<value>.*\S)          # named group: anything w/ final non-space
            \s*                      # any number of space
            ''',
        flags=re.ASCII | re.VERBOSE)

    def __init__(self, line, variable_name, value):
        super().__init__(line)
        self.variable_name = variable_name
        self.value = value

    def __repr__(self):
        return (f'AssignmentLine({self.line!r}, '
                f'{self.variable_name!r}, {self.value!r})')

    @classmethod
    def parse(cls, line):
        '''Parse input line into an AssignmentLine

        :param line: input line, must have a ``.strip()`` method

        >>> AssignmentLine.parse(InputLine('#= <v> = x', 3))
        AssignmentLine(InputLine('#= <v> = x', 3), 'v', 'x')
        >>> AssignmentLine.parse(InputLine('#= vx', 3))
        Traceback (most recent call last):
            ...
        dependencies_file.ParseError: Parse error: Invalid assignment syntax, expected '#= <var> = value' in line 3: '#= vx'.
        '''
        match = re.fullmatch(cls.REGEXP, line.strip())
        if match:
            return cls(line, *match.group('variable_name', 'value'))
        else:
            raise ParseError(
                f'Invalid assignment syntax, expected '
                f"'{cls.PREFIX} <var> = value'",
                line)

    def update_variables(self, variables):
        variables[self.variable_name] = self.value


class DependencySpecification(DependencyFileLine):
    def __init__(self, line, dependency, commit_ish, clone_url):
        super().__init__(line)
        self.dependency = dependency
        self.commit_ish = commit_ish
        self.clone_url = clone_url

    def __repr__(self):
        return (f'DependencySpecification({self.line!r}, '
                f'{self.dependency!r}, {self.commit_ish!r}, '
                f'{self.clone_url!r})')

    @classmethod
    def parse(cls, line, parts):
        '''Parse line split into 1, 2 or 3 parts into DependencySpecification

        :param line: input line
        :param parts: list of parts, assumed to contain 1, 2 or 3 elements

        >>> DependencySpecification.parse('name', ['name'])
        DependencySpecification('name', 'name', None, None)
        >>> DependencySpecification.parse('name tag', ['name', 'tag'])
        DependencySpecification('name tag', 'name', 'tag', None)
        >>> DependencySpecification.parse('a b c', ['a', 'b', 'c'])
        DependencySpecification('a b c', 'a', 'b', 'c')
        '''
        return cls(line, *(cls.safe_parts_index(parts, idx)
                           for idx in range(3)))

    def to_dependency(self, variables):
        return Dependency(
            replace_variables(self.dependency, variables),
            replace_variables(self.commit_ish, variables),
            replace_variables(self.clone_url, variables),
            self.line)

    T = TypeVar('T')

    @staticmethod
    def safe_parts_index(parts: List[T], idx: int) -> Optional[T]:
        '''Return list element at given index, None if out of bounds.'''
        if 0 <= idx < len(parts):
            return parts[idx]
        else:
            return None


def parse_line(line) -> DependencyFileLine:
    '''Parse a `line' from a dependencies file

    :param line: input line with ``strip()`` method returning the line's string
    without leading & trailing whitespace

    :returns: an instance of a sub-class of `DependencyFileLine'

    :raises ParseError: when parsing fails.

    >>> parse_line('# comment')
    CommentLine('# comment')
    >>> parse_line(' ')
    CommentLine(' ')
    >>> parse_line('#= <var> = value')
    AssignmentLine('#= <var> = value', 'var', 'value')
    >>> parse_line('name tag')
    DependencySpecification('name tag', 'name', 'tag', None)
    >>> parse_line(InputLine('name tag url', 2))
    DependencySpecification(InputLine('name tag url', 2), 'name', 'tag', 'url')
    '''
    stripped = line.strip()
    # order of tests matters because CommentLine.PREFIX is a prefix of
    # Assignmentline.PREFIX:
    if stripped.startswith(AssignmentLine.PREFIX):
        return AssignmentLine.parse(line)
    elif stripped == '' or stripped.startswith(CommentLine.PREFIX):
        return CommentLine(line)
    else:
        parts = stripped.split()
        if 0 < len(parts) < 4:
            return DependencySpecification.parse(line, parts)
        else:
            raise ParseError(f"Can't parse '{line}'", line)
