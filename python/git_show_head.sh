#!/bin/sh
# Wrapper for git_show_head.py to activate virtual environment (i.e. isolated Python dependencies)
# See git_show_head.py for usage information and command line help
activation='C:\Users\cramaph1\private\scripting-experiment\python\virtualenv/bin/activate'
test -r "$activation" && source "$activation" && exec python3 "$(dirname "$0")/git_show_head.py" "$@"
echo 'Please install the virtual environment in C:\Users\cramaph1\private\scripting-experiment\python\virtualenv and the required libraries yourself'
exit 1
