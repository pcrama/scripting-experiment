import json
import os


try:
    SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
except NameError:
    SCRIPT_DIR = os.path.realpath(os.getcwd())


def get_configuration():
    TICKET_IMAGE = 'ticket-image.png'
    CONFIGURATION_DEFAULTS = {
        'logdir': os.getenv('TEMP', SCRIPT_DIR),
        'dbdir': os.getenv('TEMP', SCRIPT_DIR),
        "organizer_name": "Organizer name",
        "organizer_bic": "GABBBEBB",
        'bank_account': "BE00 0000 0000 0000",
        "full_payment_confirmation_template": '<p>Hi,</p><p>Thank you for your payment for <a href="%reservation_url%">your reservation</a>.</p><p>Greetings,<br>--&nbsp;<br>Signature</p>',
        "partial_payment_confirmation_template": '<p>Hi,</p><p>Thank you for your payment for <a href="%reservation_url%">your reservation</a>.</p><p>You can wire the remaining %remaining_amount_in_euro% € to %organizer_name% (%bank_account%, organizer_bic%) with the communication <pre>%formatted_bank_id%</pre>.</p><p>Greetings,<br>--&nbsp;<br>Signature</p>',
        'cgitb_display': 1,
        'info_email': 'nobody@example.com',
        'disabled': False,
        "main_starter_short": "TomMozz",
        "main_starter_name": "Tomate Mozzarella",
        "main_starter_name_plural": "Tomates Mozzarella",
        "extra_starter_short": "Fondu",
        "extra_starter_name": "Croquettes au fromage",
        "extra_starter_name_plural": "Croquettes au fromage",
        "main_dish_short": "Bolo",
        "main_dish_name": "Spaghetti bolognaise",
        "main_dish_name_plural": "Spaghettis bolognaise",
        "extra_dish_short": "Sca",
        "extra_dish_name": "Spaghetti aux scampis",
        "extra_dish_name_plural": "Spaghettis aux scampis",
        "third_dish_short": "Veg",
        "third_dish_name": "Spaghetti aux légumes",
        "third_dish_name_plural": "Spaghettis aux légumes",
        "main_dessert_short": "Fondu",
        "main_dessert_name": "Fondu au chocolat",
        "main_dessert_name_plural": "Fondus au chocolat",
        "extra_dessert_short": "Glace",
        "extra_dessert_name": "Portion de glace",
        "extra_dessert_name_plural": "Portions de glace",
        "kids_main_dish_short": "BoloEnf",
        "kids_main_dish_name": "Spag. bolognaise (enfants)",
        "kids_main_dish_name_plural": "Spag. bolognaise (enfants)",
        "kids_extra_dish_short": "ScaEnf",
        "kids_extra_dish_name": "Spag. aux scampis (enfants)",
        "kids_extra_dish_name_plural": "Spag. aux scampis (enfants)",
        "kids_third_dish_short": "VegEnf",
        "kids_third_dish_name": "Spag. aux légumes (enfants)",
        "kids_third_dish_name_plural": "Spag. aux légumes (enfants)",
        "main_starter_image": TICKET_IMAGE,
        "extra_starter_image": TICKET_IMAGE,
        "main_dish_image": TICKET_IMAGE,
        "extra_dish_image": TICKET_IMAGE,
        "third_dish_image": TICKET_IMAGE,
        "main_dessert_image": TICKET_IMAGE,
        "extra_dessert_image": TICKET_IMAGE,
        "kids_main_dish_image": TICKET_IMAGE,
        "kids_extra_dish_image": TICKET_IMAGE,
        "kids_third_dish_image": TICKET_IMAGE,
    }
    try:
        with open(os.path.join(SCRIPT_DIR, 'configuration.json')) as f:
            configuration = json.load(f)
    except Exception:
        configuration = dict()
    for k, v in CONFIGURATION_DEFAULTS.items():
        configuration.setdefault(k, v)
    return configuration
