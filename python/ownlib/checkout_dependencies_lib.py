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


def pull_merge(repo, branch):
    if repo.head != repo.branches[branch]:
        repo.branches[branch].checkout()
    repo.git.pull('--rebase=false')


def pluralize(n, s):
    '''Concatenate a number and word turned to plural

    >>> pluralize(0, 'repository')
    '0 repositories'
    >>> pluralize(2, 'branch')
    '2 branches'
    >>> pluralize(3, 'tag')
    '3 tags'
    '''
    if n == 1:
        return f'1 {s}'
    else:
        if s.endswith('y'):
            plural = s[:-1] + 'ies'
        elif s.endswith('ch'):
            plural = s + 'es'
        else:
            plural = s + 's'
        return f'{n} {plural}'


class CommitIsh:
    def __init__(self, repository, commit_ish):
        self.repository = repository
        self.commit_ish = commit_ish

    @property
    def count_as_tag(self):
        return 0

    @property
    def count_as_branch(self):
        return 0

    @property
    def count_as_hex_sha(self):
        return 0

    def do_fetch(self):
        for remote in self.repository.remotes:
            for fetch_info in remote.fetch():
                print(f'Updated {fetch_info.ref} to {fetch_info.commit}')
        return self
