import os

def find_git_root(current_dir=None):
    """Find .git repository containing the current director

    :param current_dir: directory to start from, defaults to `os.getcwd()'

    Walks upward in directory hierarchy until a .git/ directory is found."""
    d = os.getcwd() if current_dir is None else os.path.realpath(current_dir)
    while d is not None and len(d) > 2:
        maybe_repo_dir = os.path.join(d, '.git')
        if os.path.exists(maybe_repo_dir):
            return maybe_repo_dir
        d = os.path.dirname(d)
    raise RuntimeError('Not inside a Git repository')
