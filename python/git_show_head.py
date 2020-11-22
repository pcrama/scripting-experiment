import git

import ownlib

parser = ownlib.initialize_default_parser('Show HEAD commit message')
args = parser.parse_args()

repo = git.Repo(ownlib.find_git_root(args.starting_directory))
print(repo.head.commit.message)
