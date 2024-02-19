#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
#
# Test with
#
# uuid_hex=00112233445566778899aabbccddeeff
# (cd app && env QUERY_STRING=uuid_hex=$uuid_hex REQUEST_METHOD=GET SERVER_NAME=localhost SCRIPT_NAME=show_reservation.cgi python3 show_reservation.cgi)
import cgi
import cgitb
import os
import time
from urllib.parse import ParseResult
import qrcode
from qrcode.image.svg import SvgPathFillImage

import config
from htmlgen import (
    cents_to_euro,
    format_bank_id,
    html_document,
    pluriel_naif,
    print_content_type,
    redirect_to_event,
    respond_html,
)
from lib_post_reservation import generate_payment_QR_code_content, make_show_reservation_url
from storage import(
    Payment,
    Reservation,
    create_db,
)


def commande(categorie, nombre1, nom1, nombre2=0, nom2=[], nombre3=0, nom3=[]):
    commandes = [
        pluriel_naif(n, x) for (n, x) in ((nombre1, nom1), (nombre2, nom2), (nombre3, nom3)) if n > 0]
    if len(commandes) == 0:
        return ''
    elif len(commandes) == 1:
        return (f'{categorie}: {commandes[0]}',)
    else:
        return (categorie, (('ul', ), *((('li',), x) for x in commandes)))


if __name__ == '__main__':
    SCRIPT_NAME = os.getenv('SCRIPT_NAME')
    SERVER_NAME = os.getenv('SERVER_NAME')
    if os.getenv('REQUEST_METHOD') != 'GET' or not SCRIPT_NAME or not SERVER_NAME:
        redirect_to_event()
    CONFIGURATION = config.get_configuration()

    cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

    MAIN_STARTER_NAME = CONFIGURATION["main_starter_name"]
    MAIN_STARTER_NAME_PLURAL = CONFIGURATION["main_starter_name_plural"]
    EXTRA_STARTER_NAME = CONFIGURATION["extra_starter_name"]
    EXTRA_STARTER_NAME_PLURAL = CONFIGURATION["extra_starter_name_plural"]
    MAIN_DISH_NAME = CONFIGURATION["main_dish_name"]
    MAIN_DISH_NAME_PLURAL = CONFIGURATION["main_dish_name_plural"]
    EXTRA_DISH_NAME = CONFIGURATION["extra_dish_name"]
    EXTRA_DISH_NAME_PLURAL = CONFIGURATION["extra_dish_name_plural"]
    THIRD_DISH_NAME = CONFIGURATION["third_dish_name"]
    THIRD_DISH_NAME_PLURAL = CONFIGURATION["third_dish_name_plural"]
    MAIN_DESSERT_NAME = CONFIGURATION["main_dessert_name"]
    MAIN_DESSERT_NAME_PLURAL = CONFIGURATION["main_dessert_name_plural"]
    EXTRA_DESSERT_NAME = CONFIGURATION["extra_dessert_name"]
    EXTRA_DESSERT_NAME_PLURAL = CONFIGURATION["extra_dessert_name_plural"]
    KIDS_MAIN_DISH_NAME = CONFIGURATION["kids_main_dish_name"]
    KIDS_MAIN_DISH_NAME_PLURAL = CONFIGURATION["kids_main_dish_name_plural"]
    KIDS_EXTRA_DISH_NAME = CONFIGURATION["kids_extra_dish_name"]
    KIDS_EXTRA_DISH_NAME_PLURAL = CONFIGURATION["kids_extra_dish_name_plural"]
    KIDS_THIRD_DISH_NAME = CONFIGURATION["kids_third_dish_name"]
    KIDS_THIRD_DISH_NAME_PLURAL = CONFIGURATION["kids_third_dish_name_plural"]
    BANK_ACCOUNT = CONFIGURATION["bank_account"]
    ORGANIZER_NAME = CONFIGURATION["organizer_name"]

    try:
        # Get form data
        form = cgi.FieldStorage()
        uuid_hex = form.getfirst('uuid_hex', default='')
        if not uuid_hex:
            redirect_to_event()
            assert uuid_hex

        db_connection = create_db(CONFIGURATION)
        reservation = Reservation.find_by_uuid(db_connection, uuid_hex)
        if not reservation:
            redirect_to_event()
            assert reservation is not None

        if print_content_type('text/html; charset=utf-8'):
            print('Content-Language: en')
            print()

        commandes = [x for x in (commande('Entrée',
                                          reservation.outside.main_starter + reservation.inside.main_starter,
                                          [MAIN_STARTER_NAME, MAIN_STARTER_NAME_PLURAL],
                                          reservation.outside.extra_starter + reservation.inside.extra_starter,
                                          [EXTRA_STARTER_NAME, EXTRA_STARTER_NAME_PLURAL]),
                                 commande('Plat',
                                          reservation.outside.main_dish + reservation.inside.main_dish,
                                          [MAIN_DISH_NAME, MAIN_DISH_NAME_PLURAL],
                                          reservation.outside.extra_dish + reservation.inside.extra_dish,
                                          [EXTRA_DISH_NAME, EXTRA_DISH_NAME_PLURAL],
                                          reservation.outside.third_dish + reservation.inside.third_dish,
                                          [THIRD_DISH_NAME, THIRD_DISH_NAME_PLURAL]),
                                 commande('Plat enfants',
                                          reservation.kids.main_dish,
                                          [KIDS_MAIN_DISH_NAME, KIDS_MAIN_DISH_NAME_PLURAL],
                                          reservation.kids.extra_dish,
                                          [KIDS_EXTRA_DISH_NAME, KIDS_EXTRA_DISH_NAME_PLURAL],
                                          reservation.kids.third_dish,
                                          [KIDS_THIRD_DISH_NAME, KIDS_THIRD_DISH_NAME_PLURAL]),
                                 commande('Dessert',
                                          reservation.outside.main_dessert + reservation.inside.main_dessert + reservation.kids.main_dessert,
                                          [MAIN_DESSERT_NAME, MAIN_DESSERT_NAME_PLURAL],
                                          reservation.outside.extra_dessert + reservation.inside.extra_dessert + reservation.kids.extra_dessert,
                                          [EXTRA_DESSERT_NAME, EXTRA_DESSERT_NAME_PLURAL]))
                     if x]
        if commandes:
            remaining_due = reservation.remaining_amount_due_in_cents(db_connection)
            last_payment_update_timestamp = time.localtime(Payment.max_timestamp(db_connection))
            last_payment_update = time.strftime(
                "La dernière mise à jour de la liste des paiements reçus dans le système a eu lieu le %d/%m/%Y à %H:%M.",
                last_payment_update_timestamp)
            if remaining_due <= 0:
                due_amount_info = (
                    "Merci d'avoir déjà réglé l'entièreté des ", cents_to_euro(reservation.cents_due), " € dûs.  ",
                    last_payment_update)
            else:
                due_amount_info = (
                    'Le prix total est de ', cents_to_euro(reservation.cents_due), ' € pour le repas dont ',
                    cents_to_euro(remaining_due), ' € sont encore dûs.  ',
                    "Nous vous saurions gré de déjà verser cette somme avec la communication ",
                    "structurée ", ("code", format_bank_id(reservation.bank_id)), " sur le compte ",
                    BANK_ACCOUNT, " (bénéficiaire '", ORGANIZER_NAME, "') pour confirmer votre réservation, p.ex. en scannant ce code QR avec votre application bancaire mobile (compatible avec Argenta, Belfius Mobile, BNP Paribas Fortis Easy Banking; incompatible avec Payconiq): ",
                    ('br',),
                    ('raw', qrcode.make(generate_payment_QR_code_content(remaining_due, reservation.bank_id, CONFIGURATION),
                                        image_factory=SvgPathFillImage
                                        ).to_string().decode('utf8')),
                    ('br',),
                    last_payment_update,
                )
            commandes = (('p', "Merci de nous avoir informé à l'avance de votre commande.  ",
                          "Nous préparerons vos tickets à l'entrée pour faciliter votre commande.  ",
                          *due_amount_info),
                         (('ul', ), *((('li',), *x) for x in commandes)))
        else:
            commandes = (('p', "La commande des repas se fera à l'entrée: nous préférons le paiement mobile "
                          "mais accepterons aussi le paiement en liquide."),)
        qr_server_template = ParseResult(scheme='https', netloc='api.qrserver.com', path='/v1/create-qr-code/', params='', query='', fragment='')
        respond_html(html_document(
            'Réservation effectuée',
            (('p', 'Votre réservation au nom de ', reservation.name,
              ' pour ', pluriel_naif(reservation.places, 'place'), " a été enregistrée.  Vous pouvez garder cette page dans vos favoris ou l'imprimer comme preuve de réservation."),
             *commandes,
             ('p',
              (('a', 'href', f"mailto:{CONFIGURATION['info_email']}"), 'Contactez-nous'),
              ' si vous avez encore des questions.'),
             ('p', 'Un tout grand merci pour votre présence le ', reservation.date,
              ': le soutien de nos auditeurs nous est indispensable!'),
             ('hr',),
             ('p',
              "Scannez ce code QR pour suivre l'état actuel de votre réservation:",
              ("br",),
              ('raw', qrcode.make(make_show_reservation_url(uuid_hex, script_name=SCRIPT_NAME, server_name=SERVER_NAME),
                                  image_factory=SvgPathFillImage).to_string().decode('utf8'))))))
    except Exception:
        # cgitb needs the content-type header
        if print_content_type('text/html; charset=utf-8'):
            print('Content-Language: en')
            print()
        raise
