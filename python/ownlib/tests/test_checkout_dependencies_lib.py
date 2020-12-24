import os
import unittest

import git

from .git_fixtures import (
    FakeCommit,
    test_repository,
    test_repository_with_remote,
)
from ..checkout_dependencies_lib import *


class FindByHexShaPrefixTests(unittest.TestCase):
    HUMAN_ID = 'h1'             # to find back test commit easily

    def setUp(self):
        self.repository_context = test_repository([
                FakeCommit({'data': 'one line\n'},
                           '1st commit',
                           self.HUMAN_ID,
                           None,
                           None,
                           None)])
        self.repository = self.repository_context.__enter__()

    def tearDown(self):
        self.repository_context.__exit__(None, None, None)

    def test_given_existing_hex_sha_when_calling_find_then_full_hex_sha_is_returned(self):
        expected_hex_sha = self.repository.human_id_mapping[self.HUMAN_ID]
        for hex_sha in (expected_hex_sha.lower(),
                        expected_hex_sha.upper(),
                        expected_hex_sha[:5].lower(),
                        expected_hex_sha[:5].upper()):
            with self.subTest(hex_sha=hex_sha):
                self.assertEqual(
                    find_by_hex_sha_prefix(self.repository, hex_sha),
                    expected_hex_sha)

    def test_given_unknown_hex_sha_when_calling_find_StopIteration_is_raised(self):
        expected_hex_sha = self.repository.human_id_mapping[self.HUMAN_ID]
        with self.assertRaises(StopIteration):
            find_by_hex_sha_prefix(self.repository, '0000000000000000')


class PullTests(unittest.TestCase):
    branches = []
    '''List of branches in the class level local and remote repositories that test instances may use'''

    OTHER_BRANCH = f'otherbranch'
    REMOTE_COMMIT = FakeCommit(
                {'data': 'line 1\n'}, '2nd commit', 'h2', 'h1', None, None)

    @classmethod
    def setUpClass(cls):
        '''Create local and remote repository only once to speed up tests'''
        common_commits = [
            FakeCommit(
                {'data': 'one line\n'}, '1st commit', 'h1', None, None, None),
            FakeCommit(
                {'data': 'data\n'}, 'other commit', None, None, None, cls.OTHER_BRANCH),
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
        for human_id, hex_sha in cls.remote.human_id_mapping.items():
            cls.local.human_id_mapping[human_id] = hex_sha
        # Create new commit in remote but do not advance its branches yet,
        # otherwise tests are going to interfere with each other.
        for commit in remote_commits:
            commit.create(cls.remote)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.remote_context.__exit__(None, None, None)
        finally:
            cls.local_context.__exit__(None, None, None)

    def setUp(self):
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
        assert initial_head_commit in self.local.head.commit.parents
        assert self.local.branches[self.BRANCH].commit == self.local.head.commit
        # The local commit is unknown in the remote repository.
        assert self.local.head.commit not in self.remote.iter_commits()
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
        # The local commit is unknown in the remote repository.
        assert self.local.head.commit not in self.remote.iter_commits()
        # But they both have the same parent.
        assert (self.local.head.commit.parents ==
                self.remote.branches[self.BRANCH].commit.parents)

    def test_given_no_local_changes_but_on_other_branch_when_calling_pull_ff_only_no_error_is_raised(self):
        # Given: Check out other local branch to check that pull_ff_only sets
        # up the correct branch.
        self.local.git.checkout(self.OTHER_BRANCH)
        # When
        pull_ff_only(self.local, self.BRANCH)
        # Then
        self.assertEqual(self.local.head.commit,
                         self.remote.branches[self.BRANCH].commit)

    def test_given_no_local_changes_and_on_same_branch_when_calling_pull_ff_only_no_error_is_raised(self):
        # Given
        assert self.local.head.commit == self.local.branches[self.BRANCH].commit
        # When
        pull_ff_only(self.local, self.BRANCH)
        # Then
        self.assertEqual(self.local.head.commit,
                         self.remote.branches[self.BRANCH].commit)

    def test_given_branch_diverged_when_calling_pull_ff_only_an_error_is_raised(self):
        # Given
        self.setup_diverging_branch_without_conflict()
        # When
        with self.assertRaises(git.exc.GitCommandError) as cm:
            pull_ff_only(self.local, self.BRANCH)
        # Then
        self.assertTrue('Not possible to fast-forward' in cm.exception.stderr)

    def test_given_no_local_changes_but_on_other_branch_when_calling_pull_rebase_no_error_is_raised(self):
        # Given: Check out other local branch to check that pull_rebase sets
        # up the correct branch.
        self.local.git.checkout(self.OTHER_BRANCH)
        # When
        pull_rebase(self.local, self.BRANCH)
        # Then
        self.assertEqual(self.local.head.commit,
                         self.remote.branches[self.BRANCH].commit)

    def test_given_no_local_changes_and_on_same_branch_when_calling_pull_rebase_no_error_is_raised(self):
        # Given
        assert self.local.head.commit == self.local.branches[self.BRANCH].commit
        # When
        pull_rebase(self.local, self.BRANCH)
        # Then
        self.assertEqual(self.local.head.commit,
                         self.remote.branches[self.BRANCH].commit)

    def test_given_branch_diverged_without_conflict_when_calling_pull_rebase_no_error_is_raised(self):
        # Given
        self.setup_diverging_branch_without_conflict()
        # When
        pull_rebase(self.local, self.BRANCH)
        # Then
        self.assertEqual(self.local.head.commit.parents[0],
                         self.remote.branches[self.BRANCH].commit)

    def test_given_branch_diverged_with_conflict_when_calling_pull_rebase_error_is_raised(self):
        # Given
        self.setup_diverging_branch_with_conflict()
        # When
        self.needs_rebase_abort = True
        with self.assertRaises(git.exc.GitCommandError) as cm:
            pull_rebase(self.local, self.BRANCH)
        # Then
        self.assertTrue('conflict' in cm.exception.stderr)
        self.assertTrue('Could not apply' in cm.exception.stderr)

    def test_given_no_local_changes_but_on_other_branch_when_calling_pull_merge_no_error_is_raised(self):
        # Given: Check out other local branch to check that pull_merge sets
        # up the correct branch.
        self.local.git.checkout(self.OTHER_BRANCH)
        # When
        pull_merge(self.local, self.BRANCH)
        # Then
        self.assertEqual(self.local.head.commit,
                         self.remote.branches[self.BRANCH].commit)

    def test_given_no_local_changes_and_on_same_branch_when_calling_pull_merge_no_error_is_raised(self):
        # Given
        assert self.local.head.commit == self.local.branches[self.BRANCH].commit
        # When
        pull_merge(self.local, self.BRANCH)
        # Then
        self.assertEqual(self.local.head.commit,
                         self.remote.branches[self.BRANCH].commit)

    def test_given_branch_diverged_without_conflict_when_calling_pull_merge_no_error_is_raised(self):
        # Given
        self.setup_diverging_branch_without_conflict()
        previous_local_head_commit = self.local.head.commit
        # When
        pull_merge(self.local, self.BRANCH)
        # Then
        self.assertEqual(len(self.local.head.commit.parents), 2)
        self.assertIn(
            self.remote.branches[self.BRANCH].commit,
            self.local.head.commit.parents)
        self.assertIn(
            previous_local_head_commit,
            self.local.head.commit.parents)

    def test_given_branch_diverged_with_conflict_when_calling_pull_merge_error_is_raised(self):
        # Given
        self.setup_diverging_branch_with_conflict()
        # When
        self.needs_merge_abort = True
        with self.assertRaises(git.exc.GitCommandError) as cm:
            pull_merge(self.local, self.BRANCH)
        # Then
        self.assertTrue('conflict' in cm.exception.stdout)
        self.assertTrue('Automatic merge failed' in cm.exception.stdout)


class CommitIshTests(unittest.TestCase):
    def setUp(self):
        # The tests are so superficial that fake data is sufficient.
        self.sut = CommitIsh(
            'should be a real Repo object',
            'should be a reference: branch or tag name or hex SHA')

    def test_count_as_tag(self):
        self.assertEqual(self.sut.count_as_tag, 0)

    def test_count_as_branch(self):
        self.assertEqual(self.sut.count_as_branch, 0)

    def test_count_as_hex_sha(self):
        self.assertEqual(self.sut.count_as_hex_sha, 0)
