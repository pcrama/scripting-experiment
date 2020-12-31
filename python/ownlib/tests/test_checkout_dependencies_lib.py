import io
import os
import unittest
from unittest import mock
import git

from .git_fixtures import (
    FakeCommit,
    test_repository,
    test_repository_with_remote,
)
from ..checkout_dependencies_lib import *


class FindByHexshaPrefixTests(unittest.TestCase):
    HUMAN_IDS = ['h1', 'h2']    # to find back test commits easily

    @classmethod
    def setUpClass(cls):
        # Two commits on separate branches: there used to be a bug in
        # find_by_hexsha_prefix where only the current branch was searched.
        cls.repository_context = test_repository([
            FakeCommit({'data': 'one line\n'},
                       '1st commit',
                       cls.HUMAN_IDS[0],
                       None,
                       None,
                       None),
            FakeCommit({'data': 'other line\n'},
                       'other commit',
                       cls.HUMAN_IDS[1],
                       None,
                       None,
                       None)])
        cls.repository = cls.repository_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.repository_context.__exit__(None, None, None)

    def test_given_existing_hexsha_when_calling_find_then_full_hexsha_is_returned(self):
        self.repository.git.checkout(self.repository.human_id_mapping[self.HUMAN_IDS[0]])
        hexshas = None
        for human_id in self.HUMAN_IDS:
            expected_hexsha = self.repository.human_id_mapping[human_id]
            if hexshas is None:
                hexshas = (expected_hexsha.lower(),
                           expected_hexsha.upper(),
                           expected_hexsha[:5].lower(),
                           expected_hexsha[:5].upper())
            else:
                hexshas = (expected_hexsha,)
            for hexsha in hexshas:
                with self.subTest(hexsha=hexsha, human_id=human_id):
                    self.assertEqual(
                        find_by_hexsha_prefix(self.repository, hexsha),
                        expected_hexsha)

    def test_given_unknown_hexsha_when_calling_find_StopIteration_is_raised(self):
        with self.assertRaises(StopIteration):
            find_by_hexsha_prefix(self.repository, '0000000000000000')

    def test_given_invalid_hexsha_when_calling_find_then_StopIteration_is_raised(self):
        with self.assertRaises(StopIteration):
            find_by_hexsha_prefix(self.repository, 'this is not a valid hex sha')


class TestsWithRealRepositories(unittest.TestCase):
    '''Set up temporary local and remote repositories to run git related tests

    These tests are slower than the rest and their setup is about 25% of the
    spent run time, so the repositories are setup only once and reused.  This
    is also the reason why this class mixes tests for different parts of
    checkout_dependencies_lib.

    To avoid interference between different test runs, many ``branches`` are
    created, all pointing to the same commits and each test run pops one
    branch from the list of commits.'''

    branches = []
    '''List of branches in the class level local and remote repositories that test instances may use'''

    TAG = 'someTag'
    OTHER_BRANCH = 'otherbranch'
    REMOTE_COMMIT = FakeCommit(
                {'data': 'line 1\n'}, '2nd commit', 'h2', 'h1', None, None)

    @classmethod
    def setUpClass(cls):
        '''Create local and remote repository only once to speed up tests'''
        common_commits = [
            FakeCommit(
                {'data': 'one line\n'}, '1st commit', 'h1', None, None, None),
            FakeCommit(
                {'data': 'data\n'}, 'other commit', None, None, cls.TAG, cls.OTHER_BRANCH),
        ]
        remote_commits = [cls.REMOTE_COMMIT]
        cls.remote_context = test_repository(common_commits)
        cls.remote = cls.remote_context.__enter__()
        # Set up branches, all pointing to commit 'h1' so that each test can
        # pop off one branch and work from that:
        for branch_number in range(30):
            cls.branches.append(f'test_{branch_number:02}')
            cls.remote.create_head(
                cls.branches[-1], cls.remote.human_id_mapping['h1'])
        cls.local_context = test_repository_with_remote(cls.remote)
        cls.local = cls.local_context.__enter__()
        cls.local.remotes.origin.fetch()
        # Now that we have fetched, the local repository has the same commits
        # available as the remote repository, so copy the mappings to the
        # local repository.
        for human_id, hexsha in cls.remote.human_id_mapping.items():
            cls.local.human_id_mapping[human_id] = hexsha
        # Create new commit in remote but do not advance its branches yet,
        # otherwise tests are going to interfere with each other.
        for commit in remote_commits:
            commit.create(cls.remote)
        for branch in cls.branches:
            assert cls.remote.branches[branch].commit.hexsha == \
                cls.remote.human_id_mapping['h1']

    @classmethod
    def tearDownClass(cls):
        try:
            cls.remote_context.__exit__(None, None, None)
        finally:
            cls.local_context.__exit__(None, None, None)

    def setUp(self):
        super().setUp()
        # Hint: Increase the number of pre-made branches if the next statement
        # raises an exception.
        self.BRANCH = self.branches.pop()
        # Set up tracking of remote BRANCH.
        self.local.git.checkout(self.BRANCH)
        self.local.head.reset(index=True, working_tree=True)
        self.needs_merge_abort = False
        self.needs_rebase_abort = False
        # Setup remote branch to its new commit only now to avoid the
        # pull/fetch of prior test cases interfering:
        self.remote.branches[self.BRANCH].set_commit(
            self.remote.human_id_mapping['h2'])
        # Check that the remote advanced, leaving local behind
        assert self.local.branches[self.BRANCH].commit != \
            self.remote.branches[self.BRANCH].commit
        # Check that local has not even fetched
        assert self.local.remotes.origin.refs[self.BRANCH].commit != \
            self.remote.branches[self.BRANCH].commit

    def tearDown(self):
        if self.needs_merge_abort:
            self.local.git.merge('--abort') # clean up for future test
        if self.needs_rebase_abort:
            self.local.git.rebase('--abort') # clean up for future test
        super().tearDown()

    def setup_diverging_branch_without_conflict(self):
        initial_head_commit = self.local.head.commit
        # Check we are on the right branch
        assert initial_head_commit == self.local.branches[self.BRANCH].commit
        # This also advances the local BRANCH to point at the newly created
        # commit, effectively diverging from the remote:
        FakeCommit(
            {'other_file': 'local\n', **self.REMOTE_COMMIT.data},
            'local',
            'diverge',
            None,
            None,
            None
        ).create(self.local)
        self.fetch_in_local()
        assert initial_head_commit in self.local.head.commit.parents
        assert self.local.branches[self.BRANCH].commit == self.local.head.commit
        # The local commit is unknown in the remote repository.
        try:
            git.repo.fun.name_to_object(self.remote, self.local.head.commit.hexsha)
        except Exception:
            pass
        else:
            raise RuntimeError(
                "Couldn't setup_diverging_branch_without_conflict properly")
        # But they both have the same parent.
        assert (self.local.head.commit.parents ==
                self.remote.branches[self.BRANCH].commit.parents)

    def setup_diverging_branch_with_conflict(self):
        assert self.local.head.commit == self.local.branches[self.BRANCH].commit
        # This also advances the local BRANCH to point at the newly created
        # commit, effectively diverging from the remote:
        file_name, file_content = next(
            (k, v)
            for (k, v) in self.REMOTE_COMMIT.data.items()
            if isinstance(v, str))
        FakeCommit(
            {file_name: '\n'.join(
                f'changed {x}' for x in file_content.split('\n'))},
            'local',
            'diverge',
            None,
            None,
            None
        ).create(self.local)
        self.fetch_in_local()
        # The local commit is unknown in the remote repository.
        try:
            git.repo.fun.name_to_object(self.remote, self.local.head.commit.hexsha)
        except Exception:
            pass
        else:
            raise RuntimeError(
                "Couldn't setup_diverging_branch_with_conflict properly")
        # But they both have the same parent.
        assert (self.local.head.commit.parents ==
                self.remote.branches[self.BRANCH].commit.parents)

    def fetch_in_local(self):
        for remote in self.local.remotes:
            remote.fetch()

    def test_given_no_local_changes_when_calling_merge_ff_only_no_error_is_raised(self):
        # Given
        self.fetch_in_local()
        assert self.local.head.commit == self.local.branches[self.BRANCH].commit
        # When
        merge_ff_only(self.local, self.BRANCH)
        # Then
        self.assertEqual(self.local.head.commit,
                         self.remote.branches[self.BRANCH].commit)

    def test_given_branch_diverged_when_calling_merge_ff_only_an_error_is_raised(self):
        # Given
        self.setup_diverging_branch_without_conflict()
        # When
        with self.assertRaises(git.exc.GitCommandError) as cm:
            merge_ff_only(self.local, self.BRANCH)
        # Then
        self.assertTrue('Not possible to fast-forward' in cm.exception.stderr)

    def test_given_no_local_changes_but_on_other_branch_when_calling_validate_repo_and_branch_for_merge_then_error_is_raised(self):
        # Given: Check out other local branch
        self.local.git.checkout(self.OTHER_BRANCH)
        with self.assertRaises(RuntimeError) as cm:
            # When
            validate_repo_and_branch_for_merge(self.local, self.BRANCH)
        # Then
        self.assertIn(self.local.working_dir, cm.exception.args[0])
        self.assertIn(self.BRANCH, cm.exception.args[0])
        self.assertIn(self.OTHER_BRANCH, cm.exception.args[0])

    def test_given_no_local_changes_when_calling_merge_rebase_no_error_is_raised(self):
        # Given
        self.fetch_in_local()
        assert self.local.head.commit == self.local.branches[self.BRANCH].commit
        # When
        merge_rebase(self.local, self.BRANCH)
        # Then
        self.assertEqual(self.local.head.commit,
                         self.remote.branches[self.BRANCH].commit)

    def test_given_branch_diverged_without_conflict_when_calling_merge_rebase_no_error_is_raised(self):
        # Given
        self.setup_diverging_branch_without_conflict()
        # When
        merge_rebase(self.local, self.BRANCH)
        # Then
        self.assertEqual(self.local.head.commit.parents[0],
                         self.remote.branches[self.BRANCH].commit)

    def test_given_branch_diverged_with_conflict_when_calling_merge_rebase_error_is_raised(self):
        # Given
        self.setup_diverging_branch_with_conflict()
        # When
        self.needs_rebase_abort = True
        with self.assertRaises(git.exc.GitCommandError) as cm:
            merge_rebase(self.local, self.BRANCH)
        # Then
        self.assertTrue('conflict' in cm.exception.stderr)
        self.assertTrue('Could not apply' in cm.exception.stderr)

    def test_given_no_local_changes_when_calling_merge_without_option_no_error_is_raised(self):
        # Given
        self.fetch_in_local()
        assert self.local.head.commit == self.local.branches[self.BRANCH].commit
        # When
        merge_without_option(self.local, self.BRANCH)
        # Then
        self.assertEqual(self.local.head.commit,
                         self.remote.branches[self.BRANCH].commit)

    def test_given_branch_diverged_without_conflict_when_calling_merge_without_option_no_error_is_raised(self):
        # Given
        self.setup_diverging_branch_without_conflict()
        previous_local_head_commit = self.local.head.commit
        # When
        merge_without_option(self.local, self.BRANCH)
        # Then
        self.assertEqual(len(self.local.head.commit.parents), 2)
        self.assertIn(
            self.remote.branches[self.BRANCH].commit,
            self.local.head.commit.parents)
        self.assertIn(
            previous_local_head_commit,
            self.local.head.commit.parents)

    def test_given_branch_diverged_with_conflict_when_calling_merge_without_option_error_is_raised(self):
        # Given
        self.setup_diverging_branch_with_conflict()
        # When
        self.needs_merge_abort = True
        with self.assertRaises(git.exc.GitCommandError) as cm:
            merge_without_option(self.local, self.BRANCH)
        # Then
        self.assertTrue('conflict' in cm.exception.stdout)
        self.assertTrue('Automatic merge failed' in cm.exception.stdout)

    def test_given_repository_with_tag_when_calling_checkout_then_tag_is_checked_out(self):
        # Given
        assert self.local.head.commit != self.local.tags[self.TAG].commit
        sut = Tag(self.local, self.TAG, False)
        # When
        result = sut.update_working_tree()
        # Then
        self.assertIsNone(result)
        self.assertEqual(self.local.head.commit, self.local.tags[self.TAG].commit)

    def test_given_repository_with_commit_ish_not_checked_out_when_getting_commit_ish_then_commit_is_same_as_commit_ish(self):
        # Given
        sut_commit = self.local.tags[self.TAG].commit
        local_head_commit = self.local.head.commit
        assert local_head_commit  != sut_commit
        assert self.local.branches[self.OTHER_BRANCH].commit == sut_commit
        for sut in (Tag(self.local, self.TAG, False),
                    Branch(self.local, self.OTHER_BRANCH, 'ff-only'),
                    Hexsha(self.local, sut_commit.hexsha[:8])):
            with self.subTest(sut=sut):
                # When
                result = sut.commit
                # Then
                self.assertEqual(result, sut_commit)
                self.assertEqual( # no checking out as side effect
                    self.local.head.commit, local_head_commit)

    def test_given_repository_with_branch_when_calling_checkout_then_branch_is_checked_out(self):
        # Given
        assert self.local.head.commit == self.local.branches[self.BRANCH].commit
        sut = Branch(self.local, self.OTHER_BRANCH, 'ff-only')
        # When
        result = sut.update_working_tree()
        # Then
        self.assertIsNone(result)
        self.assertEqual(self.local.head.commit, self.remote.branches[self.OTHER_BRANCH].commit)

    def test_given_repository_with_hexsha_when_calling_checkout_then_hexsha_is_checked_out(self):
        # Given
        assert self.local.head.commit == self.local.branches[self.BRANCH].commit
        hexsha = self.local.remotes.origin.refs[self.OTHER_BRANCH].commit.hexsha
        sut = Hexsha(self.local, hexsha)
        # When
        result = sut.update_working_tree()
        # Then
        self.assertIsNone(result)
        self.assertEqual(self.local.head.commit.hexsha, hexsha)


class CommitIshTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        # The tests are so superficial that fake data is sufficient.
        self.mock_repo = mock.MagicMock(spec=['remotes'])
        self.mock_repo.remotes = [mock.MagicMock(spec=['fetch'])]
        self.mock_repo.remotes[0].fetch = mock.MagicMock(return_value=[])
        self.sut = CommitIsh(
            self.mock_repo,
            'should be a reference: branch or tag name or hex SHA')

    def test_count_as_tag(self):
        self.assertEqual(self.sut.count_as_tag, 0)

    def test_count_as_branch(self):
        self.assertEqual(self.sut.count_as_branch, 0)

    def test_count_as_hexsha(self):
        self.assertEqual(self.sut.count_as_hexsha, 0)

    def test_do_fetch(self):
        # When
        self.sut.do_fetch()
        # Then
        self.mock_repo.remotes[0].fetch.assert_called_once_with()


class UnknownTests(unittest.TestCase):
    COMMIT_ISH_NAME = 'AbcDef'

    def setUp(self):
        super().setUp()
        self.mock_repo = mock.NonCallableMagicMock(
            spec=['remotes', 'branches', 'tags'])
        self.mock_repo.remotes = []
        self.mock_repo.branches = []
        self.mock_repo.tags = []
        self.sut = Unknown(self.mock_repo, self.COMMIT_ISH_NAME)

    def test_commit(self):
        with self.assertRaises(NotImplementedError):
            self.sut.commit()

    def test_count_as_tag(self):
        with self.assertRaises(NotImplementedError):
            self.sut.count_as_tag

    def test_count_as_branch(self):
        with self.assertRaises(NotImplementedError):
            self.sut.count_as_branch

    def test_count_as_hexsha(self):
        with self.assertRaises(NotImplementedError):
            self.sut.count_as_hexsha

    def test_given_is_a_branch_when_calling_fetch_if_needed_then_fetches_and_returns_Branch(self):
        # Given
        self.mock_repo.branches.append(self.COMMIT_ISH_NAME)
        # When
        result = self.sut.fetch_if_needed()
        # Then
        self.assertIsInstance(result, Branch)
        self.assertIs(result.repository, self.mock_repo)
        self.assertIs(result.commit_ish, self.COMMIT_ISH_NAME)
        # Do not pull/fetch twice for unknown commit-ishs:
        self.assertIs(result.merging_option, do_not_merge)

    def test_given_is_a_tag_when_calling_fetch_if_needed_then_fetches_and_returns_Tag(self):
        # Given
        self.mock_repo.tags.append(self.COMMIT_ISH_NAME)
        # When
        result = self.sut.fetch_if_needed()
        # Then
        self.assertIsInstance(result, Tag)
        self.assertIs(result.repository, self.mock_repo)
        self.assertIs(result.commit_ish, self.COMMIT_ISH_NAME)
        # Do not pull/fetch twice for unknown commit-ishs:
        self.assertFalse(result.fetch_for_tags)

    @mock.patch('ownlib.checkout_dependencies_lib.find_by_hexsha_prefix')
    def test_given_is_a_hexsha_when_calling_fetch_if_needed_then_fetches_and_returns_Hexsha(
            self, find_by_hexsha_prefix_mock):
        # Given
        find_by_hexsha_prefix_mock.return_value = self.COMMIT_ISH_NAME
        # When
        result = self.sut.fetch_if_needed()
        # Then
        self.assertIsInstance(result, Hexsha)
        self.assertIs(result.repository, self.mock_repo)
        # Hexsha normalizes its input, so the expected value must be
        # normalized, too:
        self.assertEqual(result.commit_ish, self.COMMIT_ISH_NAME.lower())


class BranchTestsWithMockRepository(unittest.TestCase):
    NAME = 'TestBranch'

    def setUp(self):
        super().setUp()
        self.mock_repo = mock.NonCallableMagicMock(
            spec=['remotes', 'branches'])
        self.mock_remote = mock.NonCallableMagicMock(spec=['fetch'])
        self.mock_repo.remotes = [self.mock_remote]
        self.mock_repo.branches = [self.NAME, 'someOtherBranchWeWillNotUse']

    def makeSut(self, merge_option):
        self.sut = Branch(self.mock_repo, self.NAME, merge_option)
        return self.sut

    def test_count_as_tag(self):
        self.assertEqual(self.makeSut('rebase').count_as_tag, 0)

    def test_count_as_branch(self):
        self.assertEqual(self.makeSut('rebase').count_as_branch, 1)

    def test_count_as_hexsha(self):
        self.assertEqual(self.makeSut('rebase').count_as_hexsha, 0)

    def test_fetch_if_needed(self):
        # When
        result = self.makeSut('rebase').fetch_if_needed()
        # Then
        self.assertIs(result, self.sut)
        self.mock_remote.fetch.assert_called_once_with()


class HexshaTestsWithMockRepository(unittest.TestCase):
    HEXSHA = 'AbcDef'

    def setUp(self):
        super().setUp()
        self.mock_repo = mock.NonCallableMagicMock(
            spec=['remotes', 'commit'])
        self.mock_remote = mock.NonCallableMagicMock(spec=['fetch'])
        self.mock_repo.remotes = [self.mock_remote]

    def makeSut(self, exists_locally, exists_remotely):
        existing_commit = mock.NonCallableMagicMock()
        # Hex SHAs in git.Repo objects are always lower case:
        existing_commit.hexsha = self.HEXSHA.lower()
        other_commit = mock.NonCallableMagicMock()
        other_commit.hexsha = '01' * 20
        if exists_remotely:
            def side_effect(*args, **kwargs):
                self.mock_repo.commit = mock.MagicMock(
                    return_value=existing_commit)
                return []
            self.mock_remote.fetch = mock.MagicMock(side_effect=side_effect)
        self.mock_repo.commit = (
            mock.MagicMock(return_value=existing_commit)
            if exists_locally
            else mock.MagicMock(side_effect=git.BadName('fake')))
        self.sut = Hexsha(self.mock_repo, self.HEXSHA)
        return self.sut

    def test_count_as_tag(self):
        self.assertEqual(self.makeSut(True, True).count_as_tag, 0)

    def test_count_as_branch(self):
        self.assertEqual(self.makeSut(True, True).count_as_branch, 0)

    def test_count_as_hexsha(self):
        self.assertEqual(self.makeSut(True, True).count_as_hexsha, 1)

    def test_given_hexsha_not_in_repository_when_fetch_if_needed_then_fetches(self):
        # Given
        self.makeSut(False, True)
        # When
        result = self.sut.fetch_if_needed()
        # Then
        self.mock_remote.fetch.assert_called_once_with()
        self.assertIs(result, self.sut)

    def test_given_hexsha_not_in_repository_when_fetch_if_needed_then_nothing_happens(self):
        # Given
        self.makeSut(True, True)
        # When
        result = self.sut.fetch_if_needed()
        # Then
        self.mock_remote.fetch.assert_not_called()
        self.assertIs(result, self.sut)


class TagTestsWithMockRepository(unittest.TestCase):
    NAME = 'TestTag'

    def setUp(self):
        super().setUp()
        self.mock_repo = mock.NonCallableMagicMock(
            spec=['remotes', 'tags'])
        self.mock_remote = mock.NonCallableMagicMock(spec=['fetch'])
        self.mock_repo.remotes = [self.mock_remote]
        self.mock_repo.tags = [self.NAME, 'someOtherTagWeWillNotUse']

    def makeSut(self, fetch_for_tags):
        self.sut = Tag(self.mock_repo, self.NAME, fetch_for_tags)
        return self.sut

    def test_count_as_tag(self):
        self.assertEqual(self.makeSut(False).count_as_tag, 1)

    def test_count_as_branch(self):
        self.assertEqual(self.makeSut(False).count_as_branch, 0)

    def test_count_as_hexsha(self):
        self.assertEqual(self.makeSut(False).count_as_hexsha, 0)


@mock.patch('sys.stdout', new_callable=io.StringIO)
class StashingTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.repository = mock.MagicMock(spec=['git', 'working_tree_dir'])
        self.git = mock.MagicMock(spec='stash')
        self.stash = mock.MagicMock(return_value=None)
        self.git.stash = self.stash
        self.repository.git = self.git

    def test_entering_context_manager_stashes(self, sys_stdout):
        # Given
        context_manager = stashing(self.repository)
        # When
        return_value = context_manager.__enter__()
        # Then
        self.assertIsNone(return_value)
        self.assertEqual(len(self.stash.mock_calls), 1)
        self.assertEqual(self.stash.mock_calls[0].args[0], 'push')
        self.assertIn('stashing', sys_stdout.getvalue().lower())

    def test_exiting_context_manager_pops_stash(self, sys_stdout):
        # Given
        context_manager = stashing(self.repository)
        # When
        with context_manager:
            # clear all state in mocks accumulated from entering the context:
            sys_stdout.truncate(0)
            self.stash.reset_mock()
        # Then
        self.assertEqual(len(self.stash.mock_calls), 1) # 1 for entering & 1 for exiting
        self.assertEqual(self.stash.mock_calls[0].args[0], 'pop')
        self.assertIn('popped stash', sys_stdout.getvalue().lower())
