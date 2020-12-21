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
    BRANCH = 'test'
    OTHER_BRANCH = f'other{BRANCH}'
    REMOTE_COMMIT = FakeCommit(
                {'data': 'line 1\n'}, '2nd commit', 'h2', 'h1', None, None)

    def setUp(self):
        common_commits = [
            FakeCommit(
                {'data': 'one line\n'}, '1st commit', 'h1', None, None, self.BRANCH),
            FakeCommit(
                {'data': 'data\n'}, 'other commit', None, None, None, self.OTHER_BRANCH),
        ]
        remote_commits = [self.REMOTE_COMMIT]
        self.remote_context = test_repository(common_commits)
        self.remote = self.remote_context.__enter__()
        self.local_context = test_repository_with_remote(self.remote)
        self.local = self.local_context.__enter__()
        self.local.remotes.origin.fetch()
        # Set up tracking of remote BRANCH.
        self.local.git.checkout(self.BRANCH)
        for commit in remote_commits:
            commit.create(self.remote)
        self.remote.branches[self.BRANCH].set_commit(self.remote.human_id_mapping['h2'])

    def tearDown(self):
        try:
            self.remote_context.__exit__(None, None, None)
        finally:
            self.local_context.__exit__(None, None, None)

    def setup_diverging_branch_without_conflict(self):
        assert self.local.head.commit == self.local.branches[self.BRANCH].commit
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
        # The local commit is unknown in the remote repository.
        assert self.local.head.commit not in self.remote.iter_commits()
        # But they both have the same parent.
        assert (self.local.head.commit.parents ==
                self.remote.head.commit.parents)

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
                self.remote.head.commit.parents)


class PullFfOnlyTests(PullTests):
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


class PullRebaseTests(PullTests):
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
        with self.assertRaises(git.exc.GitCommandError) as cm:
            pull_rebase(self.local, self.BRANCH)
        # Then
        self.assertTrue('conflict' in cm.exception.stderr)
        self.assertTrue('Could not apply' in cm.exception.stderr)
