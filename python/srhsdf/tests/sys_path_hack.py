import contextlib
import os
import sys


@contextlib.contextmanager
def app_in_path():
    # Find code under test
    _d = next(x for x in sys.path if os.path.basename(os.path.dirname(x)) == 'srhsdf')
    sys.path = [os.path.join(os.path.dirname(_d), 'app')] + sys.path
    try:
        yield
    finally:
        sys.path.pop(0)
