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
        # Super late import to avoid breaking doctests.
        from .utils import pluralize
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


def do_not_fetch(repo, tag):
    pass


def prompt_before_fetching(repo, tag):
    for remote in repo.remotes:
        while True:
            answer = input(
                f'Should I fetch from {remote.name} for {tag}? (y/N/q) ')
            if answer == '' or answer.lower() == 'n':
                break
            elif answer.lower() == 'y':
                _fetch_a_tag(remote, tag)
                break # out of while loop
            elif answer.lower() == 'q':
                return


def fetch_and_prompt_before_forcing(repo, tag):
    for remote in repo.remotes:
        try:
            fetch_info = _fetch_a_tag(remote, tag)
        except git.GitCommandError as e:
            print(f'Caught {e} while fetching {tag} from {remote.name}')
            answer = 'x'
            while answer != '' and answer.lower() not in 'yn':
                answer = input(
                    'Should I fetch --force from {remote.name} for {tag}? (y/N) ')
                if answer.lower() == 'y':
                    _fetch_a_tag(remote, tag, force=True)
                    return


def _fetch_a_tag(remote, tag, **kwargs):
    return remote.fetch(
        refspec=f'refs/tags/{tag}:refs/tags/{tag}', **kwargs)


def fetch_with_force(repo, tag):
    for remote in repo.remotes:
        _fetch_a_tag(remote, tag, force=True)


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
                print(f'Updated reference {fetch_info.ref} to {fetch_info.commit}')
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
            return Tag(self.repository, self.commit_ish, 'no')
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
    def __init__(self, repository, commit_ish, fetch_variant):
        super().__init__(repository, commit_ish)
        self.fetch_variant = self.FETCH_VARIANTS[fetch_variant]

    @property
    def count_as_tag(self):
        return 1

    def fetch_if_needed(self):
        '''Ensure local view of remote reference corresponds to remote reference

        Because tags are not supposed to change once they have been pushed to
        the server, the DEFAULT_FETCH_VARIANT is 'no'.

        :returns: self'''
        self.fetch_variant(self.repository, self.commit_ish)
        return self

    def update_working_tree(self):
        self.repository.git.checkout(self.commit_ish)
        assert_commit(self.repository, self.commit_ish, self.commit, 'Tag')

    DEFAULT_FETCH_VARIANT = 'no'

    FETCH_VARIANTS = {
        DEFAULT_FETCH_VARIANT: do_not_fetch,
        'prompt': prompt_before_fetching,
        'prompt_force': fetch_and_prompt_before_forcing,
        'force': fetch_with_force,
    }


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
        self.repository.git.checkout(self.commit_ish)
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

    DEFAULT_MERGE_VARIANT = 'ff-only'

    MERGE_VARIANTS = {
        DEFAULT_MERGE_VARIANT: merge_ff_only,
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
        assert_commit(self.repository, self.commit_ish, self.commit, 'Hexsha')

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


def get_branch_by_name(repository, name):
    '''Get reference to a branch from a ``repository`` (or its remotes) by its ``name``

    :param repository: a GitPython repository object

    :param name: a branch name

    :returns: None in case of failure or a GitPython reference object'''
    try:
        return repository.branches[name]
    except IndexError:
        for remote in repository.remotes:
            try:
                return remote.repo.refs[f'{remote.name}/{name}']
            except IndexError:
                pass
    # Failure:
    return None


def assert_commit(repo, commit_ish, expected_commit, ref_type):
    '''Raise exception unless repository's working directory has the expected commit checked out

    :param repo: GitPython repository object

    :param commit_ish: reference (a tag name or a hexsha)

    :param expected_commit: GitPython commit object

    :param ref_type: string, e.g. 'Tag' or 'Hexsha' to interpolate in the
    exception message'''
    real_commit = repo.head.commit
    if real_commit != expected_commit:
        raise RuntimeError(
            f'Tried to check out {ref_type} {commit_ish} in '
            f'{repo.working_dir}, got {real_commit.hexsha} '
            f'instead of {expected_commit.hexsha}.')
