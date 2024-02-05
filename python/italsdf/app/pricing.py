# -*- coding: utf-8 -*-
from storage import Reservation

CENTS_STARTER = 900
CENTS_THIRD_DISH = CENTS_MAIN_DISH = 1200
CENTS_EXTRA_DISH = CENTS_MAIN_DISH + 500
CENTS_DESSERT = 600
CENTS_MENU_MAIN_DISH = CENTS_MENU_THIRD_DISH = CENTS_STARTER + CENTS_MAIN_DISH + CENTS_DESSERT - 200
CENTS_MENU_EXTRA_DISH = CENTS_STARTER + CENTS_EXTRA_DISH + CENTS_DESSERT - 200
CENTS_KIDS_MENU_MAIN_DISH = CENTS_KIDS_MENU_THIRD_DISH = 1600
CENTS_KIDS_MENU_EXTRA_DISH = CENTS_KIDS_MENU_MAIN_DISH + (CENTS_EXTRA_DISH - CENTS_MAIN_DISH)

def price_in_cents(r: Reservation,
                   outside_extra_starter: int = CENTS_STARTER,
                   outside_main_starter: int = CENTS_STARTER,
                   outside_main_dish: int = CENTS_MAIN_DISH,
                   outside_extra_dish: int = CENTS_EXTRA_DISH,
                   outside_third_dish: int = CENTS_THIRD_DISH,
                   outside_dessert: int = CENTS_DESSERT,
                   inside_main_dish: int = CENTS_MENU_MAIN_DISH,
                   inside_extra_dish: int = CENTS_MENU_EXTRA_DISH,
                   inside_third_dish: int = CENTS_MENU_THIRD_DISH,
                   kids_main_dish: int = CENTS_KIDS_MENU_MAIN_DISH,
                   kids_extra_dish: int = CENTS_KIDS_MENU_EXTRA_DISH,
                   kids_third_dish: int = CENTS_KIDS_MENU_THIRD_DISH,
                   ):
    return (
        r.outside.extra_starter * outside_extra_starter
        + r.outside.main_starter * outside_main_starter
        + r.outside.main_dish * outside_main_dish
        + r.outside.extra_dish * outside_extra_dish
        + r.outside.third_dish * outside_third_dish
        + (r.outside.main_dessert + r.outside.extra_dessert) * outside_dessert
        + r.inside.main_dish * inside_main_dish
        + r.inside.extra_dish * inside_extra_dish
        + r.inside.third_dish * inside_third_dish
        + r.kids.main_dish * kids_main_dish
        + r.kids.extra_dish * kids_extra_dish
        + r.kids.third_dish * kids_third_dish)


# def price_in_euros(r, **kwargs):
#     cents = price_in_cents(r, **kwargs)
#     return htmlgen.cents_to_euro(cents) + " €"
