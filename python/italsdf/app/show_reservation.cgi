#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import os

import config
from htmlgen import (
    CONCERT_PAGE,
    html_document,
    pluriel_naif,
    print_content_type,
    redirect_to_event,
    respond_html,
)
from storage import(
    Reservation,
    create_db,
)
from pricing import (
    price_in_euros,
)


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


def commande(categorie, nombre1, nom1, nombre2=0, nom2=[]):
    commandes = [
        pluriel_naif(n, x) for (n, x) in ((nombre1, nom1), (nombre2, nom2)) if n > 0]
    if len(commandes) == 0:
        return ''
    elif len(commandes) == 1:
        return (f'{categorie}: {commandes[0]}',)
    else:
        return (categorie, (('ul', ), *((('li',), x) for x in commandes)))

if __name__ == '__main__':
    if os.getenv('REQUEST_METHOD') != 'GET':
        redirect_to_event()
    CONFIGURATION = config.get_configuration()

    cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

    try:
        # Get form data
        form = cgi.FieldStorage()
        uuid_hex = form.getfirst('uuid_hex', default='')

        db_connection = create_db(CONFIGURATION)

        try:
            reservation = next(Reservation.select(
                db_connection,
                filtering=[('uuid', uuid_hex)],
                limit=1))
        except StopIteration:
            redirect_to_event()

        if print_content_type('text/html; charset=utf-8'):
            print('Content-Language: en')
            print()

        commandes = [x for x in (commande('Entrée',
                                          reservation.outside_main_starter + reservation.inside_main_starter,
                                          [MAIN_STARTER_NAME, MAIN_STARTER_NAME_PLURAL],
                                          reservation.outside_extra_starter + reservation.inside_extra_starter,
                                          [EXTRA_STARTER_NAME, EXTRA_STARTER_NAME_PLURAL]),
                                 commande('Plat',
                                          reservation.outside_bolo + reservation.inside_bolo,
                                          [BOLO_NAME, BOLO_NAME_PLURAL],
                                          reservation.outside_extra_dish + reservation.inside_extra_dish,
                                          [EXTRA_DISH_NAME, EXTRA_DISH_NAME_PLURAL]),
                                 commande('Plat enfants',
                                          reservation.kids_bolo,
                                          [KIDS_BOLO_NAME, KIDS_BOLO_NAME_PLURAL],
                                          reservation.kids_extra_dish,
                                          [KIDS_EXTRA_DISH_NAME, KIDS_EXTRA_DISH_NAME_PLURAL]),
                                 commande('Dessert',
                                          reservation.outside_dessert + reservation.inside_dessert,
                                          [DESSERT_NAME, DESSERT_NAME_PLURAL]))
                     if x]
        if commandes:
            commandes = (('p', "Merci de nous avoir informé de votre commande à titre indicatif.  ",
                          "Nous préparerons vos tickets à l'entrée pour faciliter votre commande.  ",
                          'Le prix total est de ', price_in_euros(reservation), ' pour le repas.'),
                         (('ul', ), *((('li',), *x) for x in commandes)))
        else:
            commandes = (('p', "La commande des repas se fera à l'entrée."),)
        respond_html(html_document(
            'Réservation effectuée',
            (('p', 'Votre réservation au nom de ', reservation.name,
              ' pour ', pluriel_naif(reservation.places, 'place'), ' a été enregistrée.'),
             *commandes,
             ('p', (('a', 'href', CONCERT_PAGE), 'Cette page'), ' sera tenue à jour avec '
              'les mesures de sécurité en vigueur lors de notre repas italien. Merci de la consulter '
              'régulièrement. ',
              (('a', 'href', f"mailto:{CONFIGURATION['info_email']}"), 'Contactez-nous'),
              ' si vous avez encore des questions.'),
             ('p', 'Un tout grand merci pour votre présence le ', reservation.date,
              ': le soutien de nos auditeurs nous est indispensable!'))))
    except Exception:
        # cgitb needs the content-type header
        if print_content_type('text/html; charset=utf-8'):
            print('Content-Language: en')
            print()
        raise
