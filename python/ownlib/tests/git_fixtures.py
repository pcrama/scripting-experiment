'''Fixtures for tests involving usage of the git Python library'''

import contextlib
import os
import pathlib
import shutil
import stat
import tempfile

import git


class FakeRepo(git.Repo):
    def __init__(self, *args, **kwargs):
        self.human_id_mapping = {}
        super().__init__(*args, **kwargs)

    @classmethod
    def create_temporary_repository(cls):
        # I would prefer to use TemporaryDirectory, but it gave me 'Access
        # denied errors' so I had to use the lower level mkdtemp.
        temp_dir = tempfile.mkdtemp()
        result = cls(git.Repo.init(temp_dir).git_dir)
        result.temp_dir = temp_dir
        return result

    def cleanup(self):
        def error_handler(function, path, excinfo):
            if isinstance(excinfo[1], PermissionError):
                os.chmod(path, stat.S_IWRITE)
                function(path)  # retry the deletion
            else:
                raise excinfo
        # ^^^^ end of local function `error_handler' ^^^^
        try:
            shutil.rmtree(self.temp_dir, onerror=error_handler)
        except AttributeError:
            pass


@contextlib.contextmanager
def test_repository(fake_commits):
    '''Context manager to create a test repository with the given commits'''
    repository = FakeRepo.create_temporary_repository()
    for commit in fake_commits:
        commit.create(repository)
    try:
        yield repository
    finally:
        repository.cleanup()


@contextlib.contextmanager
def test_repository_with_remote(remote_repository):
    '''Context manager to init empty repository with given remote repository'''
    repository = FakeRepo.create_temporary_repository()
    repository.create_remote('origin', remote_repository.working_tree_dir)
    try:
        yield repository
    finally:
        repository.cleanup()


class FakeCommit:
    '''Commit data to add to py:ref:`FakeRepo` (see py:ref:`test_repository`)

    An instance has a py:ref:`FakeCommit.create` method to create the commit
    in a py:ref:`FakeRepo`.  These commits can be chained together via their
    `human_id` (to name them while ignoring their hex_sha) and parent (the
    `human_id` of the commit to checkout before writing the data).'''
    def __init__(self, data, message, human_id, parent, tag, branch):
        self.data = data
        '''Input data: {'dir': {'file1: 'line1\nline2\n'}}'''
        self.message = message
        '''Commit message'''
        self.human_id = human_id
        '''Name fake commit so that parent can refer to it'''
        self.parent = parent
        '''human_id of parent of this FakeCommit'''
        self.tag = tag
        '''If not None, assign this tag to the FakeCommit'''
        self.branch = branch
        '''If not None, create this branch name pointing to this FakeCommit'''

    def create(self, fake_repo):
        if self.parent is not None:
            fake_repo.git.checkout(fake_repo.human_id_mapping[self.parent])
        # Remove everything except .git/ dir
        removed = []
        for x in os.scandir(fake_repo.working_tree_dir):
            if x.is_dir() and x.name == '.git':
                continue
            removed.append(x.path)
            if x.is_dir():
                shutil.rmtree(x.path)
            else:
                os.unlink(x.path)
        if removed:
            fake_repo.index.remove(removed)
        # Create new data adding it to the index at the same time
        self._create_dir(fake_repo, fake_repo.working_tree_dir, self.data)
        # And commit it
        fake_repo.index.commit(self.message)
        if self.human_id is not None:
            fake_repo.human_id_mapping[self.human_id] = fake_repo.head.commit.hexsha
        # create tag if needed
        if self.tag is not None:
            fake_repo.create_tag(self.tag)
        # create branch if needed
        if self.branch is not None:
            fake_repo.create_head(self.branch)

    def _create_dir(self, fake_repo, own_name, own_content):
        os.makedirs(own_name, exist_ok=True)
        for name, content in own_content.items():
            path = os.path.join(own_name, name)
            if hasattr(content, 'items'):
                self._create_dir(fake_repo, path, content)
            else:
                with open(path, 'w') as f:
                    f.write(content)
                fake_repo.index.add([path])
