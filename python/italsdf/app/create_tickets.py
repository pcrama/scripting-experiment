# -*- coding: utf-8 -*-
import itertools
import pricing
from htmlgen import (pluriel_naif)
import config

_CONFIGURATION = config.get_configuration()

MAIN_STARTER_NAME = _CONFIGURATION["main_starter_name"]
MAIN_STARTER_NAME_PLURAL = _CONFIGURATION["main_starter_name_plural"]
EXTRA_STARTER_NAME = _CONFIGURATION["extra_starter_name"]
EXTRA_STARTER_NAME_PLURAL = _CONFIGURATION["extra_starter_name_plural"]
BOLO_NAME = _CONFIGURATION["bolo_name"]
BOLO_NAME_PLURAL = _CONFIGURATION["bolo_name_plural"]
EXTRA_DISH_NAME = _CONFIGURATION["extra_dish_name"]
EXTRA_DISH_NAME_PLURAL = _CONFIGURATION["extra_dish_name_plural"]
DESSERT_NAME = _CONFIGURATION["dessert_name"]
DESSERT_NAME_PLURAL = _CONFIGURATION["dessert_name_plural"]
KIDS_BOLO_NAME = _CONFIGURATION["kids_bolo_name"]
KIDS_BOLO_NAME_PLURAL = _CONFIGURATION["kids_bolo_name_plural"]
KIDS_EXTRA_DISH_NAME = _CONFIGURATION["kids_extra_dish_name"]
KIDS_EXTRA_DISH_NAME_PLURAL = _CONFIGURATION["kids_extra_dish_name_plural"]
MAIN_STARTER_IMAGE = _CONFIGURATION["main_starter_image"]
EXTRA_STARTER_IMAGE = _CONFIGURATION["extra_starter_image"]
BOLO_IMAGE = _CONFIGURATION["bolo_image"]
EXTRA_DISH_IMAGE = _CONFIGURATION["extra_dish_image"]
DESSERT_IMAGE = _CONFIGURATION["dessert_image"]
KIDS_BOLO_IMAGE = _CONFIGURATION["kids_bolo_image"]
KIDS_EXTRA_DISH_IMAGE = _CONFIGURATION["kids_extra_dish_image"]

def _make_order(kind, plate, ticket_image):
    return ((('div', 'class', 'ticket-left-col'),
             ('div', 'table n°'), ('div', 'serveur'), ('div', kind), ('div', plate)),
            ('div', (('img', 'src', ticket_image),)))


def _ticket_table(main_starter, extra_starter, bolo, extra_dish, kids_bolo, kids_extra_dish, dessert):
    return (('div', 'class', 'tickets'),
            *itertools.chain(
                *itertools.chain(
                    *(x
                      for x in (
                              itertools.repeat(_make_order(kind, plate, ticket_image), quantity)
                              for kind, plate, quantity, ticket_image
                              in (('entrée:', MAIN_STARTER_NAME, main_starter, MAIN_STARTER_IMAGE),
                                  ('entrée:', EXTRA_STARTER_NAME, extra_starter, EXTRA_STARTER_IMAGE),
                                  ('plat:', BOLO_NAME, bolo, BOLO_IMAGE),
                                  ('plat:', EXTRA_DISH_NAME, extra_dish, EXTRA_DISH_IMAGE),
                                  ('plat enfant:', KIDS_BOLO_NAME, kids_bolo, KIDS_BOLO_IMAGE),
                                  ('plat enfant:', KIDS_EXTRA_DISH_NAME, kids_extra_dish, KIDS_EXTRA_DISH_IMAGE),
                                  ('dessert:', DESSERT_NAME, dessert, DESSERT_IMAGE)))))))


def _heading(*content):
    return (('div', 'class', 'ticket-heading'), *content)


def create_tickets_for_one_reservation(r):
    total_tickets = (
        r.outside_extra_starter + r.inside_extra_starter +
        r.outside_main_starter + r.inside_main_starter +
        r.outside_bolo + r.inside_bolo +
        r.outside_extra_dish + r.inside_extra_dish +
        r.kids_bolo + r.kids_extra_dish +
        r.outside_dessert + r.inside_dessert + r.kids_dessert)
    ticket_details = ', '.join(
        f'{inside}m+{outside}c {kind}' for
        outside, inside, kind in (
            (r.outside_main_starter, r.inside_main_starter, MAIN_STARTER_NAME),
            (r.outside_extra_starter, r.inside_extra_starter, EXTRA_STARTER_NAME),
            (r.outside_bolo, r.inside_bolo, BOLO_NAME),
            (r.outside_extra_dish, r.inside_extra_dish, EXTRA_DISH_NAME),
            (0, r.kids_bolo, KIDS_BOLO_NAME),
            (0, r.kids_extra_dish, KIDS_EXTRA_DISH_NAME),
            (r.outside_dessert, r.inside_dessert + r.kids_dessert, DESSERT_NAME))
        if inside !=0 or outside != 0)
    return (
        ()
        if total_tickets == 0
        else ((('div', 'class', 'no-print-page-break'),
               _heading(r.name, ': ', pluriel_naif(r.places, 'place'), ' le ', r.date),
               ('div', 'Total: ', pricing.price_in_euros(r), ' pour ',
                pluriel_naif(total_tickets, 'ticket'), ': ', ticket_details, '.')),
              _ticket_table(
                  main_starter=r.outside_main_starter + r.inside_main_starter,
                  extra_starter=r.outside_extra_starter + r.inside_extra_starter,
                  bolo=r.outside_bolo + r.inside_bolo,
                  extra_dish=r.outside_extra_dish + r.inside_extra_dish,
                  kids_bolo=r.kids_bolo,
                  kids_extra_dish=r.kids_extra_dish,
                  dessert=r.outside_dessert + r.inside_dessert + r.kids_dessert)))


def create_full_ticket_list(rs, main_starter, extra_starter, bolo, extra_dish, kids_bolo, kids_extra_dish, dessert):
    for r in rs:
        extra_starter -= r.outside_extra_starter + r.inside_extra_starter
        main_starter -= r.outside_main_starter + r.inside_main_starter
        bolo -= r.outside_bolo + r.inside_bolo
        kids_bolo -= r.kids_bolo
        kids_extra_dish -= r.kids_extra_dish
        extra_dish -= r.outside_extra_dish + r.inside_extra_dish
        dessert -= r.outside_dessert + r.inside_dessert + r.kids_dessert
        if extra_starter < 0 or main_starter < 0 or bolo < 0 or extra_dish < 0 or dessert < 0 or kids_bolo < 0 or kids_extra_dish < 0:
            raise RuntimeError(
                'Not enough tickets: ' + ', '.join('='.join((n, str(v))) for n, v in (
                    (MAIN_STARTER_NAME, main_starter),
                    (EXTRA_STARTER_NAME, extra_starter),
                    (BOLO_NAME, bolo),
                    (EXTRA_DISH_NAME, extra_dish),
                    (KIDS_BOLO_NAME, kids_bolo),
                    (KIDS_EXTRA_DISH_NAME, kids_extra_dish),
                    (DESSERT_NAME, dessert))))
        for e in create_tickets_for_one_reservation(r):
            yield e
    
    yield _heading('Vente libre')
    yield ('div',
           ', '.join('='.join((n, str(v))) for n, v in (
                    (MAIN_STARTER_NAME, main_starter),
                    (EXTRA_STARTER_NAME, extra_starter),
                    (BOLO_NAME, bolo),
                    (EXTRA_DISH_NAME, extra_dish),
                    (KIDS_BOLO_NAME, kids_bolo),
                    (KIDS_EXTRA_DISH_NAME, kids_extra_dish),
                    (DESSERT_NAME, dessert))))
    yield _ticket_table(
        main_starter=main_starter,
        extra_starter=extra_starter,
        bolo=bolo,
        extra_dish=extra_dish,
        kids_bolo=kids_bolo,
        kids_extra_dish=kids_extra_dish,
        dessert=dessert)


def ul_for_menu_data(total_main_starter, total_extra_starter, total_bolo, total_extra_dish, total_dessert):
    return ('ul',
            *(('li', pluriel_naif(count, (singular_name, plural_name)))
              for (count, singular_name, plural_name) in (
                      (total_main_starter, MAIN_STARTER_NAME, MAIN_STARTER_NAME_PLURAL),
                      (total_extra_starer, EXTRA_STARER_NAME, EXTRA_STARER_NAME_PLURAL),
                      (total_bolo, BOLO_NAME, BOLO_NAME_PLURAL),
                      (total_extra_dish, EXTRA_DISH_NAME, EXTRA_DISH_NAME_PLURAL),
                      (total_kids_bolo, KIDS_BOLO_NAME, KIDS_BOLO_NAME_PLURAL),
                      (total_kids_extra_dish, KIDS_EXTRA_DISH_NAME, KIDS_EXTRA_DISH_NAME_PLURAL),
                      (total_dessert, DESSERT_NAME, DESSERT_NAME_PLURAL))))
