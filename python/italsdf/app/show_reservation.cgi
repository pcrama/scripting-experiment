#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import os

import config
from htmlgen import (
    CONCERT_PAGE,
    cents_to_euro,
    format_bank_id,
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

    MAIN_STARTER_NAME = CONFIGURATION["main_starter_name"]
    MAIN_STARTER_NAME_PLURAL = CONFIGURATION["main_starter_name_plural"]
    EXTRA_STARTER_NAME = CONFIGURATION["extra_starter_name"]
    EXTRA_STARTER_NAME_PLURAL = CONFIGURATION["extra_starter_name_plural"]
    BOLO_NAME = CONFIGURATION["bolo_name"]
    BOLO_NAME_PLURAL = CONFIGURATION["bolo_name_plural"]
    EXTRA_DISH_NAME = CONFIGURATION["extra_dish_name"]
    EXTRA_DISH_NAME_PLURAL = CONFIGURATION["extra_dish_name_plural"]
    DESSERT_NAME = CONFIGURATION["dessert_name"]
    DESSERT_NAME_PLURAL = CONFIGURATION["dessert_name_plural"]
    KIDS_BOLO_NAME = CONFIGURATION["kids_bolo_name"]
    KIDS_BOLO_NAME_PLURAL = CONFIGURATION["kids_bolo_name_plural"]
    KIDS_EXTRA_DISH_NAME = CONFIGURATION["kids_extra_dish_name"]
    KIDS_EXTRA_DISH_NAME_PLURAL = CONFIGURATION["kids_extra_dish_name_plural"]
    BANK_ACCOUNT = CONFIGURATION["bank_account"]

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
                                          reservation.outside_dessert + reservation.inside_dessert + reservation.kids_dessert,
                                          [DESSERT_NAME, DESSERT_NAME_PLURAL]))
                     if x]
        if commandes:
            remaining_due = reservation.remaining_amount_due_in_cents(db_connection)
            if remaining_due <= 0:
                due_amount_info = (
                    "Merci d'avoir déjà réglé l'entiéreté des ", cents_to_euro(reservation.cents_due), " € dûs.  ")
            else:
                due_amount_info = (
                    'Le prix total est de ', cents_to_euro(reservation.cents_due), ' € pour le repas dont ',
                    cents_to_euro(remaining_due), ' € sont encore dûs.  '
                )
            commandes = (('p', "Merci de nous avoir informé à l'avance de votre commande.  ",
                          "Nous préparerons vos tickets à l'entrée pour faciliter votre commande.  ",
                          *due_amount_info,
                          "Nous vous saurions gré de déjà verser cette somme avec la communication ",
                          "structurée ", ("code", format_bank_id(reservation.bank_id)), " sur le compte ",
                          BANK_ACCOUNT, " pour confirmer votre réservation."),
                         (('ul', ), *((('li',), *x) for x in commandes)))
        else:
            commandes = (('p', "La commande des repas se fera à l'entrée: nous préférons le paiement mobile "
                          "mais accepterons aussi le paiement en liquide."),)
        respond_html(html_document(
            'Réservation effectuée',
            (('p', 'Votre réservation au nom de ', reservation.name,
              ' pour ', pluriel_naif(reservation.places, 'place'), ' a été enregistrée.'),
             *commandes,
             ('p',
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
