import argparse
from configparser import DuplicateSectionError, NoOptionError, NoSectionError
import contextlib
import itertools
import os

import git # type: ignore

import ownlib
from ownlib.checkout_dependencies_lib import (
    Branch,
    CommitIsh,
    Hexsha,
    Tag,
    Unknown,
    find_by_hexsha_prefix,
    get_branch_by_name,
    pluralize,
    stashing,
)


def clone(main_project: git.Repo, dependency: ownlib.Dependency) -> git.Repo:
    '''Clone a dependency as sibling of the main project

    After the clone, these configuration options are copied from the main
    project into the dependency if they are not set there yet:
    - user.name
    - user.email
    - core.autocrlf

    :param main_project: git repository object.

    :param dependency: dependency information parsed from the Dependencies.txt file

    :returns: the dependency git repository object.
    '''
    print(f'clone {dependency.dependency_path} from {dependency.clone_url}')
    cloned_repo = git.Repo.clone_from(
        dependency.clone_url,
        dependency.real_path(main_project))
    with main_project.config_reader() as main_config, \
         cloned_repo.config_writer() as repo_config:
        for (section, option) in (('user', 'name'),
                                  ('user', 'email'),
                                  ('core', 'autocrlf')):
            try:
                main_option_value = main_config.get(section, option)
            except NoOptionError:
                print(f'No value for {section}.{option} in main repository '
                      f'to copy to {dependency.dependency_path}')
                continue
            except NoSectionError:
                print(f'No {section} in main repository configuration to look up '
                      f'{option} value to copy to {dependency.dependency_path}')
                continue
            try:
                repo_config.add_section(section)
            except DuplicateSectionError:
                pass
            repo_config.set(section, option, main_option_value)
    return cloned_repo


@contextlib.contextmanager
def do_not_stash(repository):
    '''Context manager doing nothing'''
    # This is the counter part for the py:ref:`stashing` context manager.
    # This way, with a single ``if``, a context manager is selected that
    # handles local uncommitted changes instead of having two ``if`` to
    # push and pop depending on the args.do_not_stash option.
    yield


def print_header(s):
    '''Print a string with underlines below'''
    print(s)
    print('-' * len(s))


def main(args):
    try:
        dependencies = ownlib.build_dependencies_list(
            ownlib.parse_dependency_lines_iterator(
                args.dependencies_file.name, args.dependencies_file))
    finally:
        args.dependencies_file.close()
    main_project_dir = ownlib.find_git_root(args.dependencies_file.name)
    main_project = git.Repo(main_project_dir)
    siblings = {
        os.path.basename(os.path.dirname(repo_dir)): git.Repo(repo_dir)
        for repo_dir in ownlib.find_git_siblings(main_project_dir)}
    cloned = branches = tags = hexshas = 0

    for dependency in dependencies:
        if (cloned + branches + tags + hexshas) > 0:
            print('') # newline to separate previous dependency from next header
        print_header(dependency.dependency_path)
        # Make sure we have a repository to work on by cloning if needed
        try:
            repo = siblings[dependency.dependency_path]
        except KeyError:
            repo = clone(main_project, dependency)
            cloned += 1

        # See if the reference we need to check out already exists.
        # NB: git.repo.fun.name_to_object(r, dependency.commit_ish) is not
        # what we need here because we also want to know if the name is a Tag,
        # a Branch or a Hexsha.
        commit_ish = dependency.commit_ish
        if commit_ish in repo.tags:
            # Normally, tags are not supposed to move so we should not fetch,
            # but the user may override this on the command line.
            ref = Tag(repo, commit_ish, args.fetch_for_tags)
        elif get_branch_by_name(repo, commit_ish) is not None:
            ref = Branch(repo, commit_ish, args.merge_for_branches)
        else:
            try:
                ref = Hexsha(repo, find_by_hexsha_prefix(repo, commit_ish))
            except StopIteration:
                ref = Unknown(repo, commit_ish)

        # Allow reference to update itself in case fetching teaches us
        # something we don't know yet (i.e. ref is an Unknown but can become
        # e.g. a Tag).
        ref = ref.fetch_if_needed()

        # Check if dependency working tree is clean, maybe stashing is needed
        is_dirty = repo.is_dirty()
        untracked_files = repo.untracked_files
        if is_dirty or untracked_files:
            report = ' and '.join(
                partial_report
                for partial_report in (
                        'local changes' if is_dirty else '',
                        f'{pluralize(len(untracked_files), "untracked file")}'
                        if untracked_files else '')
                if partial_report)
            print(f'{repo.working_tree_dir} contains {report}')
            stasher = do_not_stash if args.no_stash else stashing
        else:
            stasher = do_not_stash

        with stasher(repo):
            ref.update_working_tree()

        target_commit = ref.commit
        real_commit = repo.head.commit
        if target_commit == real_commit:
            print(f'{repo.working_tree_dir} contains {target_commit}.')
        else:
            raise RuntimeError(
                f'On {real_commit.hexsha} instead of {target_commit.hexsha}')

        branches += ref.count_as_branch
        tags += ref.count_as_tag
        hexshas += ref.count_as_hexsha

    print(f'{pluralize(len(dependencies), "dependency")}: '
          f'cloned {pluralize(cloned, "repository")}, '
          f'checked out {pluralize(branches, "branch")}, '
          f'{pluralize(hexshas, "Hexsha")}',
          f'and {pluralize(tags, "tag")}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Clone/checkout dependencies')
    parser.add_argument(
        'dependencies_file',
        type=argparse.FileType('r'),
        nargs='?',
        default='Dependencies.txt',
        help='file with list of dependencies')
    parser.add_argument(
        '--no-stash',
        # Wish I could use action=argparse.BooleanOptionalAction, but that is Python 3.9
        action='store_true',
        default=False,
        help='omit stashing before checking out and popping afterwards')
    parser.add_argument(
        '--fetch-for-tags',
        action='store_true',
        default=False,
        help='fetch from remote even if commit-ish is a tag')
    parser.add_argument(
        '--merge-for-branches',
        choices=Branch.MERGE_VARIANTS.keys(),
        default='ff-only',
        help=('if/how changes to upstream branches should be integrated '
              'to local branches'))
    args = parser.parse_args()
    main(args)
