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
        'cgitb_display': 1,
        'info_email': 'nobody@example.com',
        'disabled': False,
        "main_starter_name": "Tomate Mozzarella",
        "main_starter_name_plural": "Tomates Mozzarella",
        "extra_starter_name": "Fondus au fromage",
        "extra_starter_name_plural": "Fondus au fromage",
        "bolo_name": "Spaghetti bolognaise",
        "bolo_name_plural": "Spathettis bolognaise",
        "extra_dish_name": "Spaghetti végétarien",
        "extra_dish_name_plural": "Spaghettis végétariens",
        "dessert_name": "3 mignardises",
        "dessert_name_plural": "3 mignardises",
        "kids_bolo_name": "Spag. bolognaise (enfants)",
        "kids_bolo_name_plural": "Spag. bolognaise (enfants)",
        "kids_extra_dish_name": "Spag. végétarien (enfants)",
        "kids_extra_dish_name_plural": "Spag. végétariens (enfants)",
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
