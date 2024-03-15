# -*- coding: utf-8 -*-
import itertools
from typing import Iterable
from htmlgen import (cents_to_euro, pluriel_naif)
import config
from storage import Reservation

_CONFIGURATION = config.get_configuration()

MAIN_STARTER_NAME = _CONFIGURATION["main_starter_name"]
MAIN_STARTER_TICKET = _CONFIGURATION.get("main_starter_ticket", MAIN_STARTER_NAME)
MAIN_STARTER_NAME_PLURAL = _CONFIGURATION["main_starter_name_plural"]
EXTRA_STARTER_NAME = _CONFIGURATION["extra_starter_name"]
EXTRA_STARTER_TICKET = _CONFIGURATION.get("extra_starter_ticket", EXTRA_STARTER_NAME)
EXTRA_STARTER_NAME_PLURAL = _CONFIGURATION["extra_starter_name_plural"]
MAIN_DISH_NAME = _CONFIGURATION["main_dish_name"]
MAIN_DISH_TICKET = _CONFIGURATION.get("main_dish_ticket", MAIN_DISH_NAME)
MAIN_DISH_NAME_PLURAL = _CONFIGURATION["main_dish_name_plural"]
EXTRA_DISH_NAME = _CONFIGURATION["extra_dish_name"]
EXTRA_DISH_TICKET = _CONFIGURATION.get("extra_dish_ticket", EXTRA_DISH_NAME)
EXTRA_DISH_NAME_PLURAL = _CONFIGURATION["extra_dish_name_plural"]
THIRD_DISH_NAME = _CONFIGURATION["third_dish_name"]
THIRD_DISH_TICKET = _CONFIGURATION.get("third_dish_ticket", THIRD_DISH_NAME)
THIRD_DISH_NAME_PLURAL = _CONFIGURATION["third_dish_name_plural"]
MAIN_DESSERT_NAME = _CONFIGURATION["main_dessert_name"]
MAIN_DESSERT_TICKET = _CONFIGURATION.get("main_dessert_ticket", MAIN_DESSERT_NAME)
MAIN_DESSERT_NAME_PLURAL = _CONFIGURATION["main_dessert_name_plural"]
EXTRA_DESSERT_NAME = _CONFIGURATION["extra_dessert_name"]
EXTRA_DESSERT_TICKET = _CONFIGURATION.get("extra_dessert_ticket", EXTRA_DESSERT_NAME)
EXTRA_DESSERT_NAME_PLURAL = _CONFIGURATION["extra_dessert_name_plural"]
KIDS_MAIN_DISH_NAME = _CONFIGURATION["kids_main_dish_name"]
KIDS_MAIN_DISH_TICKET = _CONFIGURATION.get("kids_main_dish_ticket", KIDS_MAIN_DISH_NAME)
KIDS_MAIN_DISH_NAME_PLURAL = _CONFIGURATION["kids_main_dish_name_plural"]
KIDS_EXTRA_DISH_NAME = _CONFIGURATION["kids_extra_dish_name"]
KIDS_EXTRA_DISH_TICKET = _CONFIGURATION.get("kids_extra_dish_ticket", KIDS_EXTRA_DISH_NAME)
KIDS_EXTRA_DISH_NAME_PLURAL = _CONFIGURATION["kids_extra_dish_name_plural"]
KIDS_THIRD_DISH_NAME = _CONFIGURATION["kids_third_dish_name"]
KIDS_THIRD_DISH_TICKET = _CONFIGURATION.get("kids_third_dish_ticket", KIDS_THIRD_DISH_NAME)
KIDS_THIRD_DISH_NAME_PLURAL = _CONFIGURATION["kids_third_dish_name_plural"]
MAIN_STARTER_IMAGE = _CONFIGURATION["main_starter_image"]
EXTRA_STARTER_IMAGE = _CONFIGURATION["extra_starter_image"]
MAIN_DISH_IMAGE = _CONFIGURATION["main_dish_image"]
EXTRA_DISH_IMAGE = _CONFIGURATION["extra_dish_image"]
THIRD_DISH_IMAGE = _CONFIGURATION["third_dish_image"]
MAIN_DESSERT_IMAGE = _CONFIGURATION["main_dessert_image"]
EXTRA_DESSERT_IMAGE = _CONFIGURATION["extra_dessert_image"]
KIDS_MAIN_DISH_IMAGE = _CONFIGURATION["kids_main_dish_image"]
KIDS_EXTRA_DISH_IMAGE = _CONFIGURATION["kids_extra_dish_image"]
KIDS_THIRD_DISH_IMAGE = _CONFIGURATION["kids_third_dish_image"]

def _make_order(kind, plate, ticket_image):
    return ((('div', 'class', 'ticket-left-col'),
             ('div', 'table n°'), ('div', 'serveur'), ('div', kind), ('div', plate)),
            ('div', (('img', 'src', ticket_image),)))


def _ticket_table(main_starter, extra_starter, main_dish, extra_dish, third_dish, kids_main_dish, kids_extra_dish, kids_third_dish, main_dessert, extra_dessert):
    return (('div', 'class', 'tickets'),
            *itertools.chain(
                *itertools.chain(
                    *(x
                      for x in (
                              itertools.repeat(_make_order(kind, plate, ticket_image), quantity)
                              for kind, plate, quantity, ticket_image
                              in (('entrée:', MAIN_STARTER_TICKET, main_starter, MAIN_STARTER_IMAGE),
                                  ('entrée:', EXTRA_STARTER_TICKET, extra_starter, EXTRA_STARTER_IMAGE),
                                  ('plat:', MAIN_DISH_TICKET, main_dish, MAIN_DISH_IMAGE),
                                  ('plat:', EXTRA_DISH_TICKET, extra_dish, EXTRA_DISH_IMAGE),
                                  ('plat:', THIRD_DISH_TICKET, third_dish, THIRD_DISH_IMAGE),
                                  ('plat enfant:', KIDS_MAIN_DISH_TICKET, kids_main_dish, KIDS_MAIN_DISH_IMAGE),
                                  ('plat enfant:', KIDS_EXTRA_DISH_TICKET, kids_extra_dish, KIDS_EXTRA_DISH_IMAGE),
                                  ('plat enfant:', KIDS_THIRD_DISH_TICKET, kids_third_dish, KIDS_THIRD_DISH_IMAGE),
                                  ('dessert:', MAIN_DESSERT_TICKET, main_dessert, MAIN_DESSERT_IMAGE),
                                  ('dessert:', EXTRA_DESSERT_TICKET, extra_dessert, EXTRA_DESSERT_IMAGE)))))))


def _heading(*content):
    return (('div', 'class', 'ticket-heading'), *content)


def create_tickets_for_one_reservation(connection, r: Reservation):
    total_tickets = (
        r.outside.extra_starter + r.inside.extra_starter +
        r.outside.main_starter + r.inside.main_starter +
        r.outside.main_dish + r.inside.main_dish +
        r.outside.extra_dish + r.inside.extra_dish +
        r.outside.third_dish + r.inside.third_dish +
        r.kids.main_dish + r.kids.extra_dish + r.kids.third_dish +
        r.outside.main_dessert + r.inside.main_dessert + r.kids.main_dessert +
        r.outside.extra_dessert + r.inside.extra_dessert + r.kids.extra_dessert)
    ticket_details = ', '.join(
        f'{inside}m+{outside}c {kind}' for
        outside, inside, kind in (
            (r.outside.main_starter, r.inside.main_starter, MAIN_STARTER_NAME),
            (r.outside.extra_starter, r.inside.extra_starter, EXTRA_STARTER_NAME),
            (r.outside.main_dish, r.inside.main_dish, MAIN_DISH_NAME),
            (r.outside.extra_dish, r.inside.extra_dish, EXTRA_DISH_NAME),
            (r.outside.third_dish, r.inside.third_dish, THIRD_DISH_NAME),
            (0, r.kids.main_dish, KIDS_MAIN_DISH_NAME),
            (0, r.kids.extra_dish, KIDS_EXTRA_DISH_NAME),
            (0, r.kids.third_dish, KIDS_THIRD_DISH_NAME),
            (r.outside.main_dessert, r.inside.main_dessert + r.kids.main_dessert, MAIN_DESSERT_NAME),
            (r.outside.extra_dessert, r.inside.extra_dessert + r.kids.extra_dessert, EXTRA_DESSERT_NAME))
        if inside !=0 or outside != 0)
    return (
        ()
        if total_tickets == 0
        else ((('div', 'class', 'no-print-page-break'),
               _heading(r.name, ': ', pluriel_naif(r.places, 'place'), ' le ', r.date),
               ('div', 'Total dû: ', cents_to_euro(r.remaining_amount_due_in_cents(connection)) + " €", ' pour ',
                pluriel_naif(total_tickets, 'ticket'), ': ', ticket_details, '.')),
              _ticket_table(
                  main_starter=r.outside.main_starter + r.inside.main_starter,
                  extra_starter=r.outside.extra_starter + r.inside.extra_starter,
                  main_dish=r.outside.main_dish + r.inside.main_dish,
                  extra_dish=r.outside.extra_dish + r.inside.extra_dish,
                  third_dish=r.outside.third_dish + r.inside.third_dish,
                  kids_main_dish=r.kids.main_dish,
                  kids_extra_dish=r.kids.extra_dish,
                  kids_third_dish=r.kids.third_dish,
                  main_dessert=r.outside.main_dessert + r.inside.main_dessert + r.kids.main_dessert,
                  extra_dessert=r.outside.extra_dessert + r.inside.extra_dessert + r.kids.extra_dessert)))


def create_full_ticket_list(connection, rs: Iterable[Reservation], main_starter: int, extra_starter: int, main_dish: int, extra_dish: int, third_dish: int, kids_main_dish: int, kids_extra_dish: int, kids_third_dish: int, main_dessert: int, extra_dessert: int):
    for r in rs:
        extra_starter -= r.outside.extra_starter + r.inside.extra_starter
        main_starter -= r.outside.main_starter + r.inside.main_starter
        main_dish -= r.outside.main_dish + r.inside.main_dish
        extra_dish -= r.outside.extra_dish + r.inside.extra_dish
        third_dish -= r.outside.third_dish + r.inside.third_dish
        kids_main_dish -= r.kids.main_dish
        kids_extra_dish -= r.kids.extra_dish
        kids_third_dish -= r.kids.third_dish
        main_dessert -= r.outside.main_dessert + r.inside.main_dessert + r.kids.main_dessert
        extra_dessert -= r.outside.extra_dessert + r.inside.extra_dessert + r.kids.extra_dessert
        if extra_starter < 0 or main_starter < 0 or main_dish < 0 or extra_dish < 0 or third_dish < 0 or main_dessert < 0 or extra_dessert < 0 or kids_main_dish < 0 or kids_extra_dish < 0 or kids_third_dish < 0:
            raise RuntimeError(
                'Not enough tickets: ' + ', '.join('='.join((n, str(v))) for n, v in (
                    (MAIN_STARTER_NAME, main_starter),
                    (EXTRA_STARTER_NAME, extra_starter),
                    (MAIN_DISH_NAME, main_dish),
                    (EXTRA_DISH_NAME, extra_dish),
                    (THIRD_DISH_NAME, third_dish),
                    (KIDS_MAIN_DISH_NAME, kids_main_dish),
                    (KIDS_EXTRA_DISH_NAME, kids_extra_dish),
                    (KIDS_THIRD_DISH_NAME, kids_third_dish),
                    (MAIN_DESSERT_NAME, main_dessert),
                    (EXTRA_DESSERT_NAME, extra_dessert))))
        for e in create_tickets_for_one_reservation(connection, r):
            yield e
    
    yield _heading('Vente libre')
    yield ('div',
           ', '.join('='.join((n, str(v))) for n, v in (
               (MAIN_STARTER_NAME, main_starter),
               (EXTRA_STARTER_NAME, extra_starter),
               (MAIN_DISH_NAME, main_dish),
               (EXTRA_DISH_NAME, extra_dish),
               (THIRD_DISH_NAME, third_dish),
               (KIDS_MAIN_DISH_NAME, kids_main_dish),
               (KIDS_EXTRA_DISH_NAME, kids_extra_dish),
               (KIDS_THIRD_DISH_NAME, kids_third_dish),
               (MAIN_DESSERT_NAME, main_dessert),
               (EXTRA_DESSERT_NAME, extra_dessert))
                     if v > 0))
    yield _ticket_table(
        main_starter=main_starter,
        extra_starter=extra_starter,
        main_dish=main_dish,
        extra_dish=extra_dish,
        third_dish=third_dish,
        kids_main_dish=kids_main_dish,
        kids_extra_dish=kids_extra_dish,
        kids_third_dish=kids_third_dish,
        main_dessert=main_dessert,
        extra_dessert=extra_dessert)


def ul_for_menu_data(total_main_starter, total_extra_starter, total_main_dish, total_extra_dish, total_third_dish, total_kids_main_dish, total_kids_extra_dish, total_kids_third_dish, total_main_dessert, total_extra_dessert):
    return ('ul',
            *(('li', pluriel_naif(count, (singular_name, plural_name)))
              for (count, singular_name, plural_name) in (
                      (total_main_starter, MAIN_STARTER_NAME, MAIN_STARTER_NAME_PLURAL),
                      (total_extra_starter, EXTRA_STARTER_NAME, EXTRA_STARTER_NAME_PLURAL),
                      (total_main_dish, MAIN_DISH_NAME, MAIN_DISH_NAME_PLURAL),
                      (total_extra_dish, EXTRA_DISH_NAME, EXTRA_DISH_NAME_PLURAL),
                      (total_third_dish, THIRD_DISH_NAME, THIRD_DISH_NAME_PLURAL),
                      (total_kids_main_dish, KIDS_MAIN_DISH_NAME, KIDS_MAIN_DISH_NAME_PLURAL),
                      (total_kids_extra_dish, KIDS_EXTRA_DISH_NAME, KIDS_EXTRA_DISH_NAME_PLURAL),
                      (total_kids_third_dish, KIDS_THIRD_DISH_NAME, KIDS_THIRD_DISH_NAME_PLURAL),
                      (total_main_dessert, MAIN_DESSERT_NAME, MAIN_DESSERT_NAME_PLURAL),
                      (total_extra_dessert, EXTRA_DESSERT_NAME, EXTRA_DESSERT_NAME_PLURAL))))
