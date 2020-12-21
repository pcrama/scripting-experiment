import os


GIT_DIR = '.git'
'''Directory containing git repository metadata'''


def find_git_root(current_dir=None):
    """Find .git repository containing the current director

    :param current_dir: directory to start from, defaults to `os.getcwd()'

    Walks upward in directory hierarchy until a .git/ directory is found.

    :returns: the .git/ directory"""
    d = os.getcwd() if current_dir is None else os.path.realpath(current_dir)
    while True:
        maybe_repo_dir = os.path.join(d, GIT_DIR)
        if os.path.exists(maybe_repo_dir):
            return maybe_repo_dir
        upper_dir = os.path.dirname(d)
        if upper_dir == d:
            break
        else:
            d = upper_dir
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


def get_dependency_real_path(main_project_git_dir, dependency_path):
    '''Get real path of a dependency given the main project's .git directory

    :param main_project_git_dir: .git directory of main project
    (presumably the main project also contained the Dependencies.txt
    file)

    :param dependency_path: path component of the dependencies_file.Dependency

    :returns: dependency's real path (not the .git dir)

    >>> get_dependency_real_path('a/b/c/.git', 'd').endswith('a/b/d')
    True'''
    solution = os.path.dirname(os.path.dirname(os.path.realpath(
        main_project_git_dir)))
    return os.path.join(solution, dependency_path)
