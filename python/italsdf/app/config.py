import json
import os


try:
    SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
except NameError:
    SCRIPT_DIR = os.path.realpath(os.getcwd())


def get_configuration():
    CONFIGURATION_DEFAULTS = {
        'logdir': os.getenv('TEMP', SCRIPT_DIR),
        'dbdir': os.getenv('TEMP', SCRIPT_DIR),
        'cgitb_display': 1,
        'info_email': 'nobody@example.com',
    }
    try:
        with open(os.path.join(SCRIPT_DIR, 'configuration.json')) as f:
            configuration = json.load(f)
    except Exception:
        configuration = dict()
    for k, v in CONFIGURATION_DEFAULTS.items():
        configuration.setdefault(k, v)
    return configuration
