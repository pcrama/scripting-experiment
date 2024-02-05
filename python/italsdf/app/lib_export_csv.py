import itertools

from htmlgen import (cents_to_euro)
import config
from storage import Reservation

_CONFIGURATION = config.get_configuration()

MAIN_STARTER_SHORT = _CONFIGURATION["main_starter_short"]
EXTRA_STARTER_SHORT = _CONFIGURATION["extra_starter_short"]
MAIN_DISH_SHORT = _CONFIGURATION["main_dish_short"]
EXTRA_DISH_SHORT = _CONFIGURATION["extra_dish_short"]
THIRD_DISH_SHORT = _CONFIGURATION["third_dish_short"]
KIDS_MAIN_DISH_SHORT = _CONFIGURATION["kids_main_dish_short"]
KIDS_EXTRA_DISH_SHORT = _CONFIGURATION["kids_extra_dish_short"]
KIDS_THIRD_DISH_SHORT = _CONFIGURATION["kids_third_dish_short"]
MAIN_DESSERT_SHORT = _CONFIGURATION["main_dessert_short"]
EXTRA_DESSERT_SHORT = _CONFIGURATION["extra_dessert_short"]

def write_column_header_rows(writer):
    PLATS = (MAIN_STARTER_SHORT, EXTRA_STARTER_SHORT, MAIN_DISH_SHORT, EXTRA_DISH_SHORT, THIRD_DISH_SHORT, MAIN_DESSERT_SHORT, EXTRA_DESSERT_SHORT)
    # Wrap iterator in `tuple' because we want to traverse it twice!
    DOTS = tuple(itertools.repeat('...', len(PLATS) - 1))
    KIDS_PLATS = (KIDS_MAIN_DISH_SHORT, KIDS_EXTRA_DISH_SHORT, KIDS_THIRD_DISH_SHORT, MAIN_DESSERT_SHORT, EXTRA_DESSERT_SHORT,)
    KIDS_DOTS = tuple(itertools.repeat('...', len(KIDS_PLATS) - 1))
    row1 = ('','',
         'Menu', *DOTS,
         'Enfants', *KIDS_DOTS,
         'À la carte', *DOTS,
         '','','','','','','',)
    row2 = ('Nom', 'Places',
         *PLATS,
         *KIDS_PLATS,
         *PLATS,
         'Total', 'Dû', 'Commentaire', 'Email', 'RGPD', 'Actif', 'Origine',)
    writer.writerow(row1)
    writer.writerow(row2)


def export_reservation(writer, connection, x: Reservation) -> None:
    if x.origin:
        email = ''
        gdpr_email = ''
    else:
        email = x.email
        gdpr_email = x.email if x.gdpr_accepts_use else ''
    writer.writerow((
        x.name, x.places,
        x.inside.main_starter, x.inside.extra_starter,
        x.inside.main_dish, x.inside.extra_dish, x.inside.third_dish,
        x.inside.main_dessert,x.inside.extra_dessert,
        x.kids.main_dish, x.kids.extra_dish, x.kids.third_dish,
        x.kids.main_dessert, x.kids.extra_dessert,
        x.outside.main_starter, x.outside.extra_starter,
        x.outside.main_dish, x.outside.extra_dish, x.outside.third_dish,
        x.outside.main_dessert, x.outside.extra_dessert,
        _with_euro_sign(x.cents_due),
        _with_euro_sign(x.remaining_amount_due_in_cents(connection)),
        x.extra_comment, email, gdpr_email, x.active, x.origin
    ))


def _with_euro_sign(cents: int) -> str:
    return cents_to_euro(cents) + " €"
