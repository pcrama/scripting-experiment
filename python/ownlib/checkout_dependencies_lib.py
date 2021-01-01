'''Library with functionality for checkout_dependencies.py script

Isolated in this library for easier testing'''

import contextlib
import itertools

import git # type: ignore

def find_by_hexsha_prefix(repo, commit_ish: str) -> str:
    try:
        int(commit_ish, 16)
    except ValueError:
        # if we can't convert commit_ish to an integer in base 16, it is not a
        # valid HEX string, we fill certainly not find it, so don't go looking
        # at all.
        raise StopIteration()
    try:
        return git.repo.fun.name_to_object(repo, commit_ish).hexsha
    except git.BadName:
        raise StopIteration()


def do_not_merge(repo, branch):
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
    if remotes_checked > 0 and remotes_checked != remotes_ok:
        has_have = 'has' if remotes_ok == 1 else 'have'
        raise RuntimeError(
            f'Checked {pluralize(remotes_checked, "remote repository")} but '
            f'only {pluralize(remotes_ok, "repository")} {has_have} the same '
            f'commit for {branch} in {repo.working_tree_dir}')


def validate_repo_and_branch_for_merge(repo, branch: str):
    '''Verify that `repo' has `branch' with a matching tracking branch checked out

    :param repo: repository

    :param branch: branch name'''
    active_branch = repo.active_branch.name
    if active_branch != branch:
        raise RuntimeError(f'Expected {repo.working_dir} to be on {branch} '
                           f'but found {active_branch}')
    tracking_branch = repo.active_branch.tracking_branch().name
    if not tracking_branch.endswith(branch):
        raise RuntimeError(f'{tracking_branch} does not match {branch}')


def merge_ff_only(repo, branch: str):
    '''In `repo', assume to be on `branch' and merge remote, but only if fast-forward

    :param repo: repository

    :param branch: branch name'''
    validate_repo_and_branch_for_merge(repo, branch)
    repo.git.merge(repo.active_branch.tracking_branch().name, '--ff-only')


def merge_rebase(repo, branch):
    '''In `repo', assume to be on `branch' and rebase on remote tracking branch

    :param repo: repository

    :param branch: branch name'''
    validate_repo_and_branch_for_merge(repo, branch)
    repo.git.rebase(repo.active_branch.tracking_branch().name)


def merge_without_option(repo, branch):
    '''In `repo', assume to be on `branch' and merge remote, but only if fast-forward

    :param repo: repository

    :param branch: branch name'''
    validate_repo_and_branch_for_merge(repo, branch)
    repo.git.merge(repo.active_branch.tracking_branch().name)


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

    @property
    def commit(self) -> git.Commit:
        return self.repository.commit(self.commit_ish)

    def do_fetch(self):
        '''Internal method for `fetch_if_needed`'''
        for remote in self.repository.remotes:
            for fetch_info in remote.fetch():
                print(f'Updated {fetch_info.ref} to {fetch_info.commit}')
        return self


class Unknown(CommitIsh):
    def fetch_if_needed(self):
        '''Ensure local view of remote reference corresponds to remote reference

        :returns: an instance of CommitIsh of the correct type: `Tag`, `Hexsha`
        or `Branch`.  The idea is that with information from the remote
        repository, the correct type can be inferred instead of `Unknown`.

        :raises RuntimeError: if after fetching, the commit-ish is still
        unknown.'''
        # self.commit_ish was unknown so we certainly have to fetch:
        self.do_fetch()
        # check if self.commit_ish is known now:
        if self.commit_ish in self.repository.branches:
            # Branch was unknown, so there is nothing to merge anyway:
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
    def commit(self) -> git.Commit:
        raise NotImplementedError(
            'Unknown.commit is not meant to be used')

    def update_working_tree(self):
        raise NotImplementedError(
            'Unknown.update_working_tree is not meant to be used')

class Tag(CommitIsh):
    def __init__(self, repository, commit_ish, fetch_for_tags):
        super().__init__(repository, commit_ish)
        self.fetch_for_tags = fetch_for_tags

    @property
    def count_as_tag(self):
        return 1

    def fetch_if_needed(self):
        '''Ensure local view of remote reference corresponds to remote reference

        Because tags are not supposed to change once they have been pushed to
        the server, by default this method does nothing except returning itself
        except if `fetch_for_tags` is ``True``.

        :returns: self'''
        if self.fetch_for_tags:
            self.do_fetch()
        return self

    def update_working_tree(self):
        self.repository.git.checkout(self.commit_ish)


class Branch(CommitIsh):
    def __init__(self, repository, commit_ish, merging_option):
        super().__init__(repository, commit_ish)
        self.merging_option = self.MERGE_VARIANTS[merging_option]

    @property
    def count_as_branch(self):
        return 1

    def fetch_if_needed(self):
        '''Always fetch from remote: never assume a Branch stays the same'''
        return self.do_fetch()

    def update_working_tree(self):
        self.repository.branches[self.commit_ish].checkout()
        # when checking out a branch, if such a branch already exists locally,
        # checking out will not pull the most recent changes from the remote:
        # let the user decide what should be done (merge_ff_only is safe).
        # Merging/Rebasing is sufficient because fetching is already done by
        # fetch_if_needed.
        if self.merging_option is not None:
            self.merging_option(self.repository, self.commit_ish)
        target_commit = next((
            b.commit
            for remote in self.repository.remotes
            for b in remote.refs
            if f'{remote.name}/{self.commit_ish}' == b.name),
                             None)
        if target_commit is not None:
            # There was a remote branch: double check that the remote commits
            # ended up in the local history (can be in different ways because
            # of --ff-only, rebase or normal merge).
            assert target_commit in self.repository.iter_commits()

    MERGE_VARIANTS = {
        'ff-only': merge_ff_only,
        'merge': merge_without_option,
        'no': do_not_merge,
        'rebase': merge_rebase,
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

    def update_working_tree(self):
        self.repository.git.checkout(self.commit_ish)

    def fetch_if_needed(self):
        '''Ensure local view of remote reference corresponds to remote reference

        :returns: self'''
        try:
            self.commit
        except git.BadName:
            # Normally, we should not get here because a Hexsha is only
            # instantiated if the hexsha exists in the repository.  If it does
            # not exist, an Unknown is instantiated and the
            # Unknown.fetch_if_needed will fetch, recognize the hexsha in the
            # newly fetched information and instantiate a Hexsha.  Still, to
            # be on the safe side, we include this exception handler.
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
