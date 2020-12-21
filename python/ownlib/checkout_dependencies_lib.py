'''Library with functionality for checkout_dependencies.py script

Isolated in this library for easier testing'''

import itertools


def find_by_hex_sha_prefix(repo, commit_ish: str) -> str:
    commit_ish = commit_ish.lower()
    return next(commit.hexsha
                for commit in itertools.chain(
                        itertools.chain(*(
                            r.repo.iter_commits() for r in repo.remotes)),
                        repo.iter_commits())
                if commit.hexsha.lower().startswith(commit_ish))


def pull_ff_only(repo, branch: str):
    '''In `repo', switch to `branch' and pull, but only if fast-forward

    :param repo: repository

    :param branch: which branch to check out '''
    if repo.head != repo.branches[branch]:
        repo.branches[branch].checkout()
    repo.git.pull('--ff-only')


def pull_rebase(repo, branch):
    if repo.head != repo.branches[branch]:
        repo.branches[branch].checkout()
    repo.git.pull('--rebase=true')
