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
        'bank_account': 'BE-numero-de-compte',
        'cgitb_display': 1,
        'info_email': 'nobody@example.com',
        'disabled': False,
        "main_starter_short": "TomMozz",
        "main_starter_name": "Tomate Mozzarella",
        "main_starter_name_plural": "Tomates Mozzarella",
        "extra_starter_short": "Fondu",
        "extra_starter_name": "Croquettes au fromage",
        "extra_starter_name_plural": "Croquettes au fromage",
        "bolo_short": "Bolo",
        "bolo_name": "Spaghetti bolognaise",
        "bolo_name_plural": "Spaghettis bolognaise",
        "extra_dish_short": "Veg",
        "extra_dish_name": "Spaghetti aux légumes",
        "extra_dish_name_plural": "Spaghettis aux légumes",
        "dessert_short": "Dessert",
        "dessert_name": "Assiette de 3 Mignardises",
        "dessert_name_plural": "Assiettes de 3 Mignardises",
        "kids_bolo_short": "BoloEnf",
        "kids_bolo_name": "Spag. bolognaise (enfants)",
        "kids_bolo_name_plural": "Spag. bolognaise (enfants)",
        "kids_extra_dish_short": "VegEnf",
        "kids_extra_dish_name": "Spag. aux légumes (enfants)",
        "kids_extra_dish_name_plural": "Spag. aux légumes (enfants)",
        "main_starter_image": TICKET_IMAGE,
        "extra_starter_image": TICKET_IMAGE,
        "bolo_image": TICKET_IMAGE,
        "extra_dish_image": TICKET_IMAGE,
        "dessert_image": TICKET_IMAGE,
        "kids_bolo_image": TICKET_IMAGE,
        "kids_extra_dish_image": TICKET_IMAGE,
    }
    try:
        with open(os.path.join(SCRIPT_DIR, 'configuration.json')) as f:
            configuration = json.load(f)
    except Exception:
        configuration = dict()
    for k, v in CONFIGURATION_DEFAULTS.items():
        configuration.setdefault(k, v)
    return configuration
