import os


GIT_DIR = '.git'
'''Directory containing git repository metadata'''


def find_git_root(current_dir=None):
    """Find .git repository containing the current director

    :param current_dir: directory to start from, defaults to `os.getcwd()'

    Walks upward in directory hierarchy until a .git/ directory is found.

    :returns: the .git/ directory"""
    d = os.getcwd() if current_dir is None else os.path.realpath(current_dir)
    while d is not None and len(d) > 2:
        maybe_repo_dir = os.path.join(d, GIT_DIR)
        if os.path.exists(maybe_repo_dir):
            return maybe_repo_dir
        d = os.path.dirname(d)
    raise RuntimeError('Not inside a Git repository')


def find_git_siblings(project):
    '''Find all projects next to the input project.

    :param project: assumed to be a .git/ directory or its direct parent.

    :returns: a list of <sibling>/.git directories'''
    if os.path.basename(project) == '':
        # remove trailing directory separator
        project = os.path.dirname(project)
    if project.endswith(GIT_DIR):
        project = os.path.dirname(project)
    project_container = os.path.dirname(project)
    return [fullpath
            for fullpath in (os.path.join(project_container, d, GIT_DIR)
                             for d in os.listdir(project_container))
            if os.path.exists(fullpath)]
