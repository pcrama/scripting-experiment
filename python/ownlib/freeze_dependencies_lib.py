import os
from typing import Iterator, List

import git


def align_columns(pattern_prefix, pattern, columns):
    '''Align columns with given pattern if possible

    >>> align_columns('# ', 'ab cd ef', ['ab', 'c', 'ef'])
    'ab   c  ef'
    >>> align_columns('# ', 'ab cd ef', ['ab', 'cdcdcd', 'ef'])
    'ab   cdcdcd ef'
    >>> align_columns('# ', 'ab     cd     ef', ['ab', 'c', 'ef'])
    'ab       c      ef'
    >>> align_columns('# ', 'ab     cd     ef', ['ab', 'cdcdcd', 'ef'])
    'ab       cdcdcd ef'
    >>> align_columns('# ', 'ab     cd  ef', ['ab', 'cdcdcd', 'ef'])
    'ab       cdcdcd ef'
    >>> align_columns('# ', 'ab     cd     ef', ['ab', 'cdcdcd', 'ef', 'gh', 'ijk'])
    'ab       cdcdcd ef gh ijk'
    >>> align_columns('# ', 'ab     cd     ef', ['ab', 'cdcdcd'])
    'ab       cdcdcd'
    >>> align_columns('# ', '   ab  cd     ef', ['ab', 'c', 'ef'])
    '     ab  c      ef'
    '''
    target_columns = []
    for column in get_target_columns(pattern):
        if column == 0:
            target_columns.append(0)
        else:
            target_columns.append(column + len(pattern_prefix))
    result = ''
    for data in columns:
        try:
            target = target_columns.pop(0)
        except IndexError:
            target = 0
        if result == '' and target == 0:
            result = data
            continue
        target = max(
            target,
            len(result) + 1 # at least one space between columns
        )
        result += ' ' * (target - len(result)) + data
    return result


def get_target_columns(pattern):
    '''List all indices where a new column start in a commented out line

    >>> get_target_columns('a    bc   def')
    [0, 5, 10]
    >>> get_target_columns('  a bc  def')
    [2, 4, 8]
    '''
    result = []
    idx = 0
    last_was_space = True
    while idx < len(pattern):
        if pattern[idx] in ' \t':
            last_was_space = True
        else:
            if last_was_space:
                result.append(idx)
            last_was_space = False
        idx += 1
    return result


def freeze_dependencies_list(
        main_project_dir: str,
        file_content: Iterator['DependencyFileLine'],
        allow_branches: bool) -> Iterator[str]:
    '''Loop through the file_content and return an equivalent file with hexshas

    :param main_project_dir: path name of the main project

    :param file_content: an iterator of DependencyFileLine, see
    py:func:`dependencies_file.parse_dependency_file`
    '''
    # Very late import to avoid issues with running doctests, see e.g.
    # https://github.com/pytest-dev/pytest/issues/1927 that I am not alone with
    # the problem.  This function has no doctests so I don't care.
    from . import dependencies_file
    from . import filesystem
    from . import utils
    dependencies = dependencies_file.build_dependencies_list(file_content)
    main_project = git.Repo(main_project_dir)
    siblings = {
        os.path.basename(os.path.dirname(repo_dir)): git.Repo(repo_dir)
        for repo_dir in filesystem.find_git_siblings(main_project_dir)}
    PREFIX = '# '
    cloned = branches = tags = hexshas = 0
    for file_line in file_content:
        if not (dependencies
                and dependencies[0].dependency_file_line is file_line.line):
            yield file_line.line.line
            continue

        # If we get here, we have a dependency line: freeze it.
        dependency = dependencies.pop(0)
        if (cloned + branches + tags + hexshas) > 0:
            print('')          # separate previous dependency from next header
        utils.print_header(dependency.dependency_path)
        try:
            repo = siblings[dependency.dependency_path]
        except KeyError:
            name = dependency.dependency_path
            full_path = os.path.join(os.path.dirname(main_project_dir), name)
            raise RuntimeError(
                f'{name} not found: clone it into {full_path} first.')
        if repo.is_dirty() or repo.untracked_files:
            raise RuntimeError(
                f'{repo.working_dir} is dirty or contains untracked files')
        head_commit = repo.head.commit
        try:
            as_tag = repo.tags[dependency.commit_ish].commit
        except IndexError:
            try:
                as_branch = repo.branches[dependency.commit_ish].commit
            except IndexError:
                as_hexsha = git.repo.fun.name_to_object(
                    repo, dependency.commit_ish)
                expected = as_hexsha
                hexshas += 1
                reference_type = 'hexsha'
            else:
                expected = as_branch
                branches += 1
                reference_type = 'branch'
                if not allow_branches:
                    raise RuntimeError(
                        f'{dependency.commit_ish} in {repo.working_dir} '
                        'is a branch')
        else:
            expected = as_tag
            tags += 1
            reference_type = 'tag'
        if head_commit != expected:
            raise RuntimeError(
                f'{repo.working_dir} should be at {reference_type} '
                f'{dependency.commit_ish} ({expected.hexsha}) but '
                f'found {head_commit.hexsha}')
        if dependency.commit_ish == expected.hexsha:
            # No change necessary in dependencies file: reference is already
            # unambiguous because it contained a full hexsha
            yield dependency.dependency_file_line.line
        else:
            # Rewrite tag name, branch name or partial hexsha as full hexsha:
            yield f'{PREFIX}{dependency.dependency_file_line.line}'
            columns = [dependency.dependency_path, expected.hexsha]
            if dependency.clone_url:
                columns.append(dependency.clone_url)
            yield align_columns(PREFIX,
                                dependency.dependency_file_line.line,
                                columns)
        print(f'The {reference_type} {dependency.commit_ish} is {expected.hexsha}.')
    print('')
    utils.print_header('Summary')
    print(f'{utils.pluralize(branches + tags + hexshas, "dependency")}: '
      f'{utils.pluralize(branches, "branch")}, '
      f'{utils.pluralize(hexshas, "hexsha")}',
      f'and {utils.pluralize(tags, "tag")}')
