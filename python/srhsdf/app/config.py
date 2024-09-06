import json
import os

SCRIPT_DIR = os.getenv('CONFIGURATION_JSON_DIR')
if not SCRIPT_DIR:
    try:
        SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
    except NameError:
        SCRIPT_DIR = os.path.realpath(os.getcwd())


def get_configuration():
    CONFIGURATION_DEFAULTS = {
        'logdir': os.getenv('TEMP', SCRIPT_DIR),
        'dbdir': os.getenv('TEMP', SCRIPT_DIR),
        'cgitb_display': 1,
        'paying_seat_cents': 500,
        'bank_account': 'BExx XXXX YYYY ZZZZ',
        'organizer_name': "name of organizer's bank account",
        "organizer_bic": "GABBBEBB",
        'info_email': 'nobody@example.com',
        "full_payment_confirmation_template": '<p>Hi,</p><p>Thank you for your payment for <a href="%reservation_url%">your reservation</a>.</p><p>Greetings,<br>--&nbsp;<br>Signature</p>',
        "partial_payment_confirmation_template": '<p>Hi,</p><p>Thank you for your payment for <a href="%reservation_url%">your reservation</a>.</p><p>You can wire the remaining %remaining_amount_in_euro% € to %organizer_name% (%bank_account%, %organizer_bic%) with the communication <pre>%formatted_bank_id%</pre>.</p><p>Greetings,<br>--&nbsp;<br>Signature</p>',
    }
    try:
        with open(os.path.join(SCRIPT_DIR, 'configuration.json')) as f:
            configuration = json.load(f)
    except Exception:
        configuration = dict()
    for k, v in CONFIGURATION_DEFAULTS.items():
        configuration.setdefault(k, v)
    return configuration
