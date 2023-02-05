import itertools

from pricing import (price_in_euros)
import config

_CONFIGURATION = config.get_configuration()

MAIN_STARTER_SHORT = _CONFIGURATION["main_starter_short"]
EXTRA_STARTER_SHORT = _CONFIGURATION["extra_starter_short"]
BOLO_SHORT = _CONFIGURATION["bolo_short"]
EXTRA_DISH_SHORT = _CONFIGURATION["extra_dish_short"]
KIDS_BOLO_SHORT = _CONFIGURATION["kids_bolo_short"]
KIDS_EXTRA_DISH_SHORT = _CONFIGURATION["kids_extra_dish_short"]
DESSERT_SHORT = _CONFIGURATION["dessert_short"]

def write_column_header_rows(writer):
    PLATS = (MAIN_STARTER_SHORT, EXTRA_STARTER_SHORT, BOLO_SHORT, EXTRA_DISH_SHORT, DESSERT_SHORT,)
    # Wrap iterator in `tuple' because we want to traverse it twice!
    DOTS = tuple(itertools.repeat('...', len(PLATS) - 1))
    KIDS_PLATS = (KIDS_BOLO_SHORT, KIDS_EXTRA_DISH_SHORT, DESSERT_SHORT,)
    KIDS_DOTS = tuple(itertools.repeat('...', len(KIDS_PLATS) - 1))
    writer.writerow(
        ('','',
         'Menu', *DOTS,
         'Enfants', *KIDS_DOTS,
         'À la carte', *DOTS,
         '','','','','','',))
    writer.writerow(
        ('Nom', 'Places',
         *PLATS,
         *KIDS_PLATS,
         *PLATS,
         'Total', 'Commentaire', 'Email', 'RGPD', 'Actif', 'Origine',))


def export_reservation(writer, x):
    if x.origin:
        comment = x.email
        email = ''
        gdpr_email = ''
    else:
        comment = ''
        email = x.email
        gdpr_email = x.email if x.gdpr_accepts_use else ''
    writer.writerow((
        x.name, x.places,
        x.inside_main_starter, x.inside_extra_starter,
        x.inside_bolo, x.inside_extra_dish,
        x.inside_dessert,
        x.kids_bolo, x.kids_extra_dish,
        x.kids_dessert,
        x.outside_main_starter, x.outside_extra_starter,
        x.outside_bolo, x.outside_extra_dish,
        x.outside_dessert,
        price_in_euros(x),
        comment, email, gdpr_email, x.active, x.origin
    ))
