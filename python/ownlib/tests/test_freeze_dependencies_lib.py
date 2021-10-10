import io
from operator import attrgetter
from os import path
import unittest
from unittest import mock

import ownlib

from ownlib.freeze_dependencies_lib import *

from .git_fixtures import (
    FakeCommit,
    test_repository,
)


class TestsWithRealRepositories(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.names = ['repo1', 'repo2', 'repo3']
        cls.tags = [f'tag-{name}' for name in cls.names]
        cls.branches = [f'branch-{name}' for name in cls.names]
        cls.fake_commits = [
            [FakeCommit(
                {'data': f'repo {name}'}, 'commit 0', 'h0', None, None, None),
             FakeCommit(
                {'data': f'name {name}'}, 'commit 1', 'h1', 'h0', tag, branch)]
            for (name, (tag, branch))
            in zip(cls.names, zip(cls.tags, cls.branches))]
        cls.contexts = [
            test_repository(fake_commit) for fake_commit in cls.fake_commits]
        cls.repositories = [ctxt.__enter__() for ctxt in cls.contexts]
        for repo in cls.repositories:
            assert repo.head.commit.hexsha == repo.human_id_mapping['h1']

    @classmethod
    def tearDownClass(cls):
        for ctxt in cls.contexts:
            try:
                ctxt.__exit__(None, None, None)
            except Exception:
                pass

    def make_frozen_line(self, idx, get_references, url=None):
        repo = self.repositories[idx]
        # Abuse the fact that the test case instance and the git repository
        # instance both have the same attribute names that matter (tags or
        # branches): if get_references == attrgetter('tags'), this is like
        # hexsha = repo.tags[self.tags[idx]].commit.hexsha
        hexsha = get_references(repo)[get_references(self)[idx]].commit.hexsha
        return (
            f'{path.basename(repo.working_dir)}   {hexsha}'
            if url is None
            else f'{path.basename(repo.working_dir)}   {hexsha} {url}')

    def test_given_clean_repository_when_calling_freeze_then_frozen(self):
        # Given
        main_project = self.repositories[0]
        dependencies_lines = [
            '# Dependencies.txt',
            path.basename(self.repositories[1].working_dir) + ' ' + self.tags[1],
            path.basename(self.repositories[2].working_dir) + ' ' + self.tags[2]]
        dependencies_file = list(ownlib.parse_dependency_lines_iterator(
            'test_dependencies.txt', dependencies_lines))
        # When
        with mock.patch('sys.stdout', new_callable=io.StringIO) as sys_stdout:
            output = list(freeze_dependencies_list(
                main_project.working_dir, dependencies_file, False))
        # Then
        self.assertEqual(
            output,
            ['# Dependencies.txt',
             f'# {dependencies_lines[1]}',
             self.make_frozen_line(1, attrgetter('tags')),
             f'# {dependencies_lines[2]}',
             self.make_frozen_line(2, attrgetter('tags'))])
        for idx in [1, 2]:
            self.assertIn(
                path.basename(self.repositories[idx].working_dir),
                sys_stdout.getvalue())
        for part in ('Summary', '2 dependencies', '2 tags', '0 branches', '0 hexshas'):
            self.assertIn(part, sys_stdout.getvalue())

    def test_given_clean_repository_when_calling_freeze_then_frozen_but_hexsha_lines_untouched(self):
        # Given
        URL = 'https://example.com/url.git'
        main_project = self.repositories[0]
        dependencies_lines = [
            '# Dependencies.txt',
            path.basename(self.repositories[1].working_dir)
            + ' ' + self.repositories[1].tags[self.tags[1]].commit.hexsha[:8]
            + ' ' + URL,
            path.basename(self.repositories[2].working_dir)
            + ' ' + self.repositories[2].tags[self.tags[2]].commit.hexsha
            + ' ' + URL]
        dependencies_file = list(ownlib.parse_dependency_lines_iterator(
            'test_dependencies.txt', dependencies_lines))
        # When
        with mock.patch('sys.stdout', new_callable=io.StringIO) as sys_stdout:
            output = list(freeze_dependencies_list(
                main_project.working_dir, dependencies_file, False))
        # Then
        self.assertEqual(
            output,
            ['# Dependencies.txt',
             # Partial hexsha gets written out fully, preceded by comment
             # with original line.
             f'# {dependencies_lines[1]}',
             # Full hexsha remains untouched, there is nothing to do.
             self.make_frozen_line(1, attrgetter('tags'), URL),
             dependencies_lines[2]])
        for idx in [1, 2]:
            self.assertIn(
                path.basename(self.repositories[idx].working_dir),
                sys_stdout.getvalue())
        for part in ('Summary', '2 dependencies', '0 tags', '0 branches', '2 hexshas'):
            self.assertIn(part, sys_stdout.getvalue())

    def run_test_with_dirty_repository_expecting_exception(self):
        # Given
        main_project = self.repositories[0]
        dependencies_lines = [
            '# Dependencies.txt',
            path.basename(self.repositories[1].working_dir) + ' ' + self.tags[1],
            path.basename(self.repositories[2].working_dir) + ' ' + self.tags[2]]
        dependencies_file = list(ownlib.parse_dependency_lines_iterator(
            'test_dependencies.txt', dependencies_lines))
        # When
        with self.assertRaises(RuntimeError) as cm, \
             mock.patch('sys.stdout', new_callable=io.StringIO) as sys_stdout:
            output = list(freeze_dependencies_list(
                main_project.working_dir, dependencies_file, False))
        # Then
        self.assertIn(
            'dirty or contains untracked files', cm.exception.args[0])
        return sys_stdout.getvalue()

    def test_given_repository_with_untracked_when_calling_freeze_then_raises_exception(self):
        untracked_file = path.join(self.repositories[1].working_dir, 'extra_file')
        with open(untracked_file, 'w') as f:
            f.write('dirty file')
        try:
            sys_stdout = self.run_test_with_dirty_repository_expecting_exception()
        finally:
            os.unlink(untracked_file)
        self.assertIn(
            path.basename(self.repositories[1].working_dir),
            sys_stdout)
        self.assertNotIn(
            path.basename(self.repositories[2].working_dir),
            sys_stdout)
        self.assertNotIn('Summary', sys_stdout)

    def test_given_repository_with_modified_when_calling_freeze_then_raises_exception(self):
        os.unlink(path.join(self.repositories[2].working_dir, 'data'))
        try:
            sys_stdout = self.run_test_with_dirty_repository_expecting_exception()
        finally:
            self.repositories[2].git.restore('.')
        # Then
        for idx in [1, 2]:
            self.assertIn(
                path.basename(self.repositories[idx].working_dir),
                sys_stdout)
        self.assertNotIn('Summary', sys_stdout)

    def test_given_dependency_file_with_branches_when_calling_freeze_then_raises_exception(self):
        # Given
        main_project = self.repositories[0]
        dependencies_lines = [
            '# Dependencies.txt',
            path.basename(self.repositories[1].working_dir) + ' ' + self.branches[1],
            path.basename(self.repositories[2].working_dir) + ' ' + self.tags[2]]
        dependencies_file = list(ownlib.parse_dependency_lines_iterator(
            'test_dependencies.txt', dependencies_lines))
        # When
        with self.assertRaises(RuntimeError) as cm, \
             mock.patch('sys.stdout', new_callable=io.StringIO) as sys_stdout:
            output = list(freeze_dependencies_list(
                main_project.working_dir, dependencies_file, False))
        # Then
        for fragment in (self.branches[1],
                         'is a branch',
                         self.repositories[1].working_dir):
            self.assertIn(fragment, cm.exception.args[0])
        self.assertNotIn(self.repositories[2].working_dir, sys_stdout.getvalue())

    def test_given_dependency_file_with_branches_allowed_when_calling_freeze_then_frozen(self):
        # Given
        main_project = self.repositories[0]
        dependencies_lines = [
            '# Dependencies.txt',
            path.basename(self.repositories[1].working_dir) + ' ' + self.branches[1],
            path.basename(self.repositories[2].working_dir) + ' ' + self.tags[2]]
        dependencies_file = list(ownlib.parse_dependency_lines_iterator(
            'test_dependencies.txt', dependencies_lines))
        # When
        with mock.patch('sys.stdout', new_callable=io.StringIO) as sys_stdout:
            output = list(freeze_dependencies_list(
                main_project.working_dir, dependencies_file, True))
        # Then
        self.assertEqual(
            output,
            ['# Dependencies.txt',
             f'# {dependencies_lines[1]}',
             self.make_frozen_line(1, attrgetter('branches')),
             f'# {dependencies_lines[2]}',
             self.make_frozen_line(2, attrgetter('tags'))])
        for idx in [1, 2]:
            self.assertIn(
                path.basename(self.repositories[idx].working_dir),
                sys_stdout.getvalue())
        for part in ('Summary', '2 dependencies', '1 tag', '1 branch', '0 hexshas'):
            self.assertIn(part, sys_stdout.getvalue())

    def test_given_dependency_not_up_to_date_when_calling_freeze_then_raises_exception(self):
        # Given
        repo_1_hexsha = self.repositories[1].human_id_mapping['h0']
        main_project = self.repositories[0]
        dependencies_lines = [
            '# Dependencies.txt',
            path.basename(self.repositories[1].working_dir) + ' ' + repo_1_hexsha,
            path.basename(self.repositories[2].working_dir) + ' ' + self.tags[2]]
        dependencies_file = list(ownlib.parse_dependency_lines_iterator(
            'test_dependencies.txt', dependencies_lines))
        # When
        with self.assertRaises(RuntimeError) as cm, \
             mock.patch('sys.stdout', new_callable=io.StringIO) as sys_stdout:
            output = list(freeze_dependencies_list(
                main_project.working_dir, dependencies_file, True))
        # Then
        for fragment in (f'hexsha {repo_1_hexsha} ({repo_1_hexsha})',
                         f'found {self.repositories[1].human_id_mapping["h1"]}',
                         self.repositories[1].working_dir):
            self.assertIn(fragment, cm.exception.args[0])
        self.assertNotIn(self.repositories[2].working_dir, sys_stdout.getvalue())
