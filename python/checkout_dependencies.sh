#!/bin/sh
# Wrapper for checkout_dependencies.py to activate virtual environment (i.e. isolated Python dependencies)
# See checkout_dependencies.py for usage information and command line help
mydir="$(realpath "$(dirname "$0")")"
virtualenv="$mydir/virtualenv"
activation="$virtualenv/bin/activate"
test -r "$activation" && source "$activation" && exec python3 "$mydir/checkout_dependencies.py" "$@"
echo "Please install the virtual environment in $virtualenv and the required libraries yourself"
exit 1
