import argparse

import git

import ownlib

parser = argparse.ArgumentParser(description='Show HEAD commit message')
parser.add_argument('starting_directory', type=str, nargs='?')
args = parser.parse_args()

repo = git.Repo(ownlib.find_git_root(args.starting_directory))
print(repo.head.commit.message)
