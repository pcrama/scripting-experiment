'''Library with functionality for checkout_dependencies.py script

Isolated in this library for easier testing'''

import contextlib
import itertools


def find_by_hexsha_prefix(repo, commit_ish: str) -> str:
    try:
        int(commit_ish, 16)
    except ValueError:
        # if we can't convert commit_ish to an integer in base 16, it is not a
        # valid HEX string, we fill certainly not find it, so don't go looking
        # at all.
        raise StopIteration()
    commit_ish = commit_ish.lower()
    return next(commit.hexsha
                for commit in itertools.chain(
                        itertools.chain(*(
                            r.repo.iter_commits() for r in repo.remotes)),
                        repo.iter_commits())
                if commit.hexsha.lower().startswith(commit_ish))


def do_not_pull(repo, branch):
    remotes_checked = remotes_ok = 0
    local_commit = repo.refs[branch].commit
    for remote in repo.remotes:
        try:
            remote_commit = remote.refs[branch].commit
        except IndexError:
            continue
        else:
            remotes_checked += 1
            if remote_commit != local_commit:
                print(f'Local {branch}={local_commit} does not match '
                      f'{remote.url}: {remote_commit}!')
            else:
                remotes_ok += 1


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
    def count_as_hexsha(self):
        return 0

    def do_fetch(self):
        for remote in self.repository.remotes:
            for fetch_info in remote.fetch():
                print(f'Updated {fetch_info.ref} to {fetch_info.commit}')
        return self


class Unknown(CommitIsh):
    def fetch_if_needed(self):
        # self.commit_ish was unknown so we certainly have to fetch:
        self.do_fetch()
        # check if self.commit_ish is known now:
        if self.commit_ish in self.repository.branches:
            # Branch was unknown, so there is nothing to pull anyway:
            return Branch(self.repository, self.commit_ish, 'no')
        elif self.commit_ish in self.repository.tags:
            # We have fetched already, no need to make the Tag believe it
            # could fetch again:
            return Tag(self.repository, self.commit_ish, False)
        else:
            try:
                return Hexsha(self.repository,
                              find_by_hexsha_prefix(self.repository,
                                                     self.commit_ish))
            except StopIteration:
                pass
            raise RuntimeError(f'Commit-ish {self.commit_ish} not found '
                               f'in {self.repository.git_dir}')

    @property
    def count_as_branch(self):
        raise NotImplementedError(
            'Unknown.count_as_branch is not meant to be used')

    @property
    def count_as_tag(self):
        raise NotImplementedError(
            'Unknown.count_as_tag is not meant to be used')

    @property
    def count_as_hexsha(self):
        raise NotImplementedError(
            'Unknown.count_as_hexsha is not meant to be used')

    @property
    def commit(self):
        raise NotImplementedError(
            'Unknown.commit is not meant to be used')


class HeadyCommitIsh(CommitIsh):
    @property
    def commit(self):
        return self.repository.head.commit


class Tag(HeadyCommitIsh):
    def __init__(self, repository, commit_ish, fetch_for_tags):
        super().__init__(repository, commit_ish)
        self.fetch_for_tags = fetch_for_tags

    @property
    def count_as_tag(self):
        return 1

    @property
    def head(self):
        return self.repository.tags[self.commit_ish]

    def fetch_if_needed(self):
        if self.fetch_for_tags:
            self.do_fetch()
        return self

    def checkout(self):
        self.repository.git.checkout(self.commit_ish)
        return self.commit


class Branch(HeadyCommitIsh):
    def __init__(self, repository, commit_ish, pull_for_branches):
        super().__init__(repository, commit_ish)
        self.pull_for_branches = self.PULL_STRATEGIES[pull_for_branches]

    @property
    def count_as_branch(self):
        return 1

    @property
    def head(self):
        return self.repository.branches[self.commit_ish]

    def fetch_if_needed(self):
        return self.do_fetch()

    def checkout(self):
        result = self.head.checkout()
        # when checking out a branch, if such a branch already exists locally,
        # checking out will not pull the most recent changes from the remote:
        # let the user decide what should be done (pull_ff_only is safe).
        if self.pull_for_branches is not None:
            self.pull_for_branches(self.repository, self.commit_ish)
        return self.repository.head

    PULL_STRATEGIES = {
        'ff-only': pull_ff_only,
        'merge': pull_merge,
        'no': do_not_pull,
        'rebase': pull_rebase,
    }


class Hexsha(CommitIsh):
    def __init__(self, repository, commit_ish):
        # If commit_ish is not made from hexadecimal digits alone, this will
        # raise a ValueError:
        validate_as_hex_string = int(commit_ish, 16)
        super().__init__(repository, commit_ish.strip().lower())

    @property
    def count_as_hexsha(self):
        return 1

    @property
    def commit(self):
        return next(commit
                    for commit in self.repository.iter_commits()
                    if commit.hexsha.startswith(self.commit_ish))

    def checkout(self):
        return self.repository.git.checkout(self.commit_ish)

    def fetch_if_needed(self):
        try:
            self.commit
        except StopIteration:
            self.do_fetch()
            self.commit # crash if the Hexsha is still unknown after fetching
        return self


@contextlib.contextmanager
def stashing(repository):
    print(f'Stashing {repository.working_tree_dir}')
    # `--all' instead of `--include-untracked' is much slower even on this
    # small repository.
    repository.git.stash(
        'push', '--keep-index', '--include-untracked', '--message', __name__)
    try:
        yield
    finally:
        repository.git.stash('pop', '--index')
        print(f'Popped stash in {repository.working_tree_dir}')
