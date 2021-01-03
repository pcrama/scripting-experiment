#!/bin/sh
# Wrapper for checkout_dependencies.py to activate virtual environment (i.e. isolated Python dependencies)
# See checkout_dependencies.py for usage information and command line help
activation='C:\Users\cramaph1\private\scripting-experiment\python\virtualenv/bin/activate'
test -r "$activation" && source "$activation" && exec python3 "$(dirname "$0")/checkout_dependencies.py" "$@"
echo 'Please install the virtual environment in C:\Users\cramaph1\private\scripting-experiment\python\virtualenv and the required libraries yourself'
exit 1
