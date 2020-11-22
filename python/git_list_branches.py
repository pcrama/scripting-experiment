import git

import ownlib

parser = ownlib.initialize_default_parser('List branches')
args = parser.parse_args()

repo = git.Repo(ownlib.find_git_root(args.starting_directory))
for branch in repo.heads:
    print(branch.name)
