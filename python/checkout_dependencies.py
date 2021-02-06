'''Clone/Checkout Dependencies listed in a file

The dependencies file must be located inside a Git working directory (usually
but not necessarily in the same directory as the .git directory).  The script
automatically locates the project top-level (i.e. where the .git directory
is).  This is the reference directory for the rest of this explanation.

The file contains 3 columns: the name of a directory (located next to the
reference directory); a commit-ish (a tag or hexsha or a branch name) and a
repository URL.  See ownlib/dependencies_file.py for details about the file
format and its features.

For each line in the dependencies file:
1. if the directory does not exist, it will be cloned using the repository URL.
2. once the directory exists, the commit-ish will be checked out there.
   - if the commit-ish is unknown, the remote is fetched to learn the real
     type of the commit-ish.
   - if the commit-ish is a tag name, normally the remote is not fetched:
     tags are not supposed to be changed once they were published (see the
     --fetch-for-tags option for ways to override this behavior).
   - if the commit-ish is a hexsha, the remote is not fetched.
   - if the commit-ish is a branch name, the remote is fetched and the
     depending on the --merge-for-branches option, the changes of the remote
     branch are integrated in the local repository.

Fetching for tags already known locally: --fetch-for-tags
- no [default]: this is the safest choice and tags are not supposed to move
  anyway.
- prompt: for each dependency with a tag, prompt whether or not to fetch it.
  This is a safe option, too: Git will not fetch a remote tag that contradicts
  a local tag with the same name.  However, if a git fetch operation fails,
  the script will be interrupted.
- prompt_force: for each dependency with a tag, tries to fetch the tag.  If
  the fetch fails, the script offers to try again with the --force option.
- force: fetches the tag with --force unconditionally

Merging for branches already known in locally: --merge-for-branches
- ff-only [default]: the remote changes will be included in the local branch
  only they are a fast-forward from the local branch.  Otherwise, the script
  stops.
- merge: merge the remote branch into the local branch.  A failure to merge
  will stop the script.
- no: ignore remote branch, but fetching always happens for branches anyway.
  If the local branch is different from the remote branch, the script stops.
- rebase: the local changes will be rebased on top of the remote.  A failure
  to rebase will stop the script.
'''

import argparse
from configparser import DuplicateSectionError, NoOptionError, NoSectionError
import contextlib
import itertools
import os

import git  # type: ignore

import ownlib
from ownlib.checkout_dependencies_lib import (
    Branch,
    CommitIsh,
    Hexsha,
    Tag,
    Unknown,
    find_by_hexsha_prefix,
    get_branch_by_name,
    stashing,
)
from ownlib.utils import (
    pluralize,
    print_header,
)

def clone(main_project: git.Repo, dependency: ownlib.Dependency) -> git.Repo:
    '''Clone a dependency as sibling of the main project

    After the clone, these configuration options are copied from the main
    project into the dependency if they are not set there yet:
    - user.name
    - user.email
    - core.autocrlf

    :param main_project: git repository object.

    :param dependency: dependency information parsed from Dependencies.txt file

    :returns: the dependency git repository object.
    '''
    if dependency.clone_url is None:
        name = dependency.dependency_path
        location = dependency.dependency_file_line.location()
        raise RuntimeError(f'Unable to clone {name} because I could '
                           f'not get an URL from {location}')
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
                print(f'No {section} in main repository configuration to '
                      f'look up {option} value to copy to '
                      f'{dependency.dependency_path}')
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
            print('')          # separate previous dependency from next header
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

        branches += ref.count_as_branch
        tags += ref.count_as_tag
        hexshas += ref.count_as_hexsha

    print(f'{pluralize(len(dependencies), "dependency")}: '
          f'cloned {pluralize(cloned, "repository")}, '
          f'checked out {pluralize(branches, "branch")}, '
          f'{pluralize(hexshas, "Hexsha")}',
          f'and {pluralize(tags, "tag")}')


if __name__ == '__main__':
    DEFAULT_DEPENDENCIES_FILE = 'Dependencies.txt'
    parser = argparse.ArgumentParser(
        description='Clone/checkout dependencies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    parser.add_argument(
        'dependencies_file',
        type=argparse.FileType('r'),
        nargs='?',
        default=DEFAULT_DEPENDENCIES_FILE,
        help=('file with list of dependencies, '
              f'{DEFAULT_DEPENDENCIES_FILE} by default'))
    parser.add_argument(
        '--no-stash',
        # Wish I could use action=argparse.BooleanOptionalAction, but that is
        # Python 3.9
        action='store_true',
        default=False,
        help='omit stashing before checking out and popping afterwards')
    parser.add_argument(
        '--fetch-for-tags',
        choices=Tag.FETCH_VARIANTS.keys(),
        default=Tag.DEFAULT_FETCH_VARIANT,
        help=('fetch from remote even if commit-ish is a tag, '
              f'default: {Tag.DEFAULT_FETCH_VARIANT}'))
    parser.add_argument(
        '--merge-for-branches',
        choices=Branch.MERGE_VARIANTS.keys(),
        default=Branch.DEFAULT_MERGE_VARIANT,
        help=('if/how changes to upstream branches should be integrated '
              f'to local branches, default: {Branch.DEFAULT_MERGE_VARIANT}'))
    args = parser.parse_args()
    main(args)
