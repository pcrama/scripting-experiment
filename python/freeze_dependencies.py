'''Freeze dependencies list

See `checkout_dependencies.py --help` for a description of the file format.

For each dependency in the file

- Check if the dependency directory is not dirty (no untracked or modified
  files present).  Only 'clean' repositories can be frozen.

- Check if the commit-ish is a branch and raise an exception unless the
  --allow-branches option was used.  Normally branches should not be used in
  dependencies files because they do not represent a stable reference.

- Raise an exception if the HEAD commit of the repository does not correspond
  to the commit-ish.

- If all checks pass, output the initial line with a `# ` prefix to make it
  a comment and copy it below, replacing the commit-ish with the equivalent
  full hexsha:

    # dependency_name    tag_name                                   clone_url
    dependency_name      0123456789012345678901234567890123456789   URL
'''

import argparse
import os
import shutil
import sys

import ownlib
from ownlib.freeze_dependencies_lib import (
    align_columns,
    freeze_dependencies_list,
)
from ownlib.utils import print_header


def main(args):
    original_file = args.dependencies_file.name
    try:
        file_content = list(ownlib.parse_dependency_lines_iterator(
                original_file, args.dependencies_file))
    finally:
        args.dependencies_file.close()
    main_project_dir = ownlib.find_git_root(original_file)
    output = []
    try:
        for ll in freeze_dependencies_list(
                main_project_dir, file_content, args.allow_branches):
            output.append(ll)
    except RuntimeError as e:
        print(f'Error: {e}', file=sys.stderr)
        return 1
    backup_file = f'{original_file}.bak'
    try:
        os.unlink(backup_file)
    except Exception as e:
        print(f'Ignoring {e} trying to delete {backup_file}', file=sys.stderr)
    print(f'Could not back up {original_file} to {backup_file}.  '
          f'Aborting... new {original_file} starts here:',
          file=sys.stderr)
    print('\n'.join(output), file=sys.stderr)
    print(f'Could not back up {original_file} to {backup_file}.  '
          f'Aborting... new {original_file} stops here.',
          file=sys.stderr)

    try:
        os.rename(original_file, backup_file)
    except Exception as e:
        print(f'Could not back up {original_file} to {backup_file}.  '
              f'Aborting... new {original_file} starts here:')
        print('\n'.join(output))
        print(f'Could not back up {original_file} to {backup_file}.  '
              f'Aborting... new {original_file} stops here.')
        return 2
    with open(original_file, mode='w', newline=os.linesep) as f:
        f.writelines(f'{line.rstrip()}\n' for line in output)
    return 0

if __name__ == '__main__':
    DEFAULT_DEPENDENCIES_FILE = 'Dependencies.txt'
    parser = argparse.ArgumentParser(
        description='Freeze dependencies',
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
        '--allow-branches',
        # Wish I could use action=argparse.BooleanOptionalAction, but that is
        # Python 3.9
        action='store_true',
        default=False,
        help='do not raise an error if one of the dependencies is a branch')
    args = parser.parse_args()
    result = main(args)
    if result != 0:
        sys.exit(result)
