# -*- coding: utf-8 -*-
import htmlgen

CENTS_STARTER = 750
CENTS_BOLO = 1500
CENTS_EXTRA_DISH = CENTS_BOLO
CENTS_DESSERT = 750
CENTS_MENU_BOLO = CENTS_STARTER + CENTS_BOLO + CENTS_DESSERT - 300
CENTS_MENU_EXTRA_DISH = CENTS_STARTER + CENTS_EXTRA_DISH + CENTS_DESSERT - 300
CENTS_KIDS_MENU_BOLO = 1600
CENTS_KIDS_MENU_EXTRA_DISH = CENTS_KIDS_MENU_BOLO

def price_in_cents(r,
                   outside_extra_starter=CENTS_STARTER,
                   outside_main_starter=CENTS_STARTER,
                   outside_bolo=CENTS_BOLO,
                   outside_extra_dish=CENTS_EXTRA_DISH,
                   outside_dessert=CENTS_DESSERT,
                   inside_bolo=CENTS_MENU_BOLO,
                   inside_extra_dish=CENTS_MENU_EXTRA_DISH,
                   kids_bolo=CENTS_KIDS_MENU_BOLO,
                   kids_extra_dish=CENTS_KIDS_MENU_EXTRA_DISH):
    # complete_menus = min([r.outside_extra_starter + r.outside_main_starter, r.outside_bolo + r.outside_extra_dish, r.outside_tiramisu + r.outside_tranches])
    # if complete_menus == 0:
    #     correction = 0
    # elif menu_bolo - outside_bolo == menu_extra_dish - outside_extra_dish and outside_extra_starter == outside_main_starter and outside_tiramisu == outside_tranches:
    #     correction = (outside_extra_starter + outside_bolo + outside_tiramisu - menu_bolo) * complete_menus
    # else:
    #     raise Exception("Unable to compute best price")
    return (
        r.outside_extra_starter * outside_extra_starter
        + r.outside_main_starter * outside_main_starter
        + r.outside_bolo * outside_bolo
        + r.outside_extra_dish * outside_extra_dish
        + r.outside_dessert * outside_dessert
        + r.inside_bolo * inside_bolo
        + r.inside_extra_dish * inside_extra_dish
        + r.kids_bolo * kids_bolo
        + r.kids_extra_dish * kids_extra_dish)


def price_in_euros(r, **kwargs):
    cents = price_in_cents(r, **kwargs)
    return htmlgen.cents_to_euro(cents) + " €"
