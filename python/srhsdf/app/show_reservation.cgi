#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
#
# (export SCRIPT_NAME="$PWD/app/show_reservation.cgi"; cd "$(dirname "$SCRIPT_NAME")" && CONFIGURATION_JSON_DIR="$(dirname "$(ls -t /tmp/tmp.*/configuration.json | head -n 1)")" DB_DB="$CONFIGURATION_JSON_DIR/db.db" REQUEST_METHOD=GET REMOTE_USER="" REMOTE_ADDR="127.0.0.1" QUERY_STRING='bank_id='"$(sqlite3 "$DB_DB" 'select bank_id from reservations order by timestamp desc limit 1')"'&uuid_hex='"$(sqlite3 "$DB_DB" "select uuid from reservations order by timestamp desc limit 1")" SERVER_NAME=localhost python3 $SCRIPT_NAME)
import cgi
import cgitb
import os
import time

import qrcode
from qrcode.image.svg import SvgPathFillImage

import config
from htmlgen import (
    cents_to_euro,
    format_bank_id,
    html_document,
    print_content_type,
    respond_html,
    redirect_to_event,
)
from lib_post_reservation import (
    generate_payment_QR_code_content,
    make_show_reservation_url,
)
from storage import(
    Payment,
    Reservation,
    create_db,
)


if __name__ == '__main__':
    
    if os.getenv('REQUEST_METHOD') != 'GET':
        redirect_to_event()
    try:
        SERVER_NAME = os.environ["SERVER_NAME"]
        SCRIPT_NAME = os.environ["SCRIPT_NAME"]
    except KeyError:
        redirect_to_event()
    CONFIGURATION = config.get_configuration()
    BANK_ACCOUNT = CONFIGURATION["bank_account"]
    ORGANIZER_NAME = CONFIGURATION["organizer_name"]

    cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

    # Get form data
    form = cgi.FieldStorage()
    bank_id = form.getfirst('bank_id', default='')
    uuid_hex = form.getfirst('uuid_hex', default='')

    db_connection = create_db(CONFIGURATION)

    try:
        reservation = next(Reservation.select(
            db_connection,
            filtering=[('bank_id', bank_id), ('uuid', uuid_hex)],
            limit=1))
    except StopIteration:
        redirect_to_event()
        reservation = None
    assert reservation is not None

    if print_content_type('text/html; charset=utf-8'):
        print('Content-Language: en')
        print()

    places = (' pour ',)
    due_amount_info = ()
    if reservation.paying_seats > 0:
        places += (str(reservation.paying_seats),
                   ' place payante ' if reservation.paying_seats == 1 else ' places payantes ')
        remaining_due = reservation.remaining_amount_due_in_cents(db_connection)
        last_payment_update_timestamp = time.localtime(Payment.max_timestamp(db_connection))
        last_payment_update = time.strftime(
            "La dernière mise à jour de la liste des paiements reçus dans le système a eu lieu le %d/%m/%Y à %H:%M. ",
            last_payment_update_timestamp)
        if remaining_due <= 0:
            due_amount_info = (
                "Merci d'avoir déjà réglé l'entièreté des ", cents_to_euro(reservation.cents_due), " € dûs.  ",
                last_payment_update)
        else:
            due_amount_info = (
                'Le prix total pour votre réservation est de ', cents_to_euro(reservation.cents_due), ' €',
                *((' dont ', cents_to_euro(remaining_due), ' € sont encore dûs') if remaining_due != reservation.cents_due else ()),'.  ',
                'Vos places seront tenues'
                if (reservation.paying_seats + reservation.free_seats > 1)
                else 'Votre place sera tenue',
                " à votre disposition à l'entrée. ",
                "Afin de réduire les files à l'entrée, nous vous saurions gré de déjà verser cette somme avec la communication ",
                "structurée ", ("code", format_bank_id(reservation.bank_id)), " sur le compte ",
                BANK_ACCOUNT, " (bénéficiaire '", ORGANIZER_NAME, "') pour votre réservation, p.ex. en scannant ce code QR avec votre application bancaire mobile (testé avec Argenta, Belfius Mobile et BNP Paribas Fortis Easy Banking; incompatible avec Payconiq): ",
                ('br',),
                ('raw', qrcode.make(
                    generate_payment_QR_code_content(remaining_due, reservation.bank_id, CONFIGURATION),
                    image_factory=SvgPathFillImage
                ).to_string().decode('utf8')),
                ('br',),
                last_payment_update,
            )

    if reservation.free_seats > 0:
        if reservation.paying_seats > 0:
            places += ('et ',)
        places += (str(reservation.free_seats),
                   ' place gratuite ' if reservation.free_seats == 1 else ' places gratuites ')
    if reservation.paying_seats > 0:
        places += ('au prix de ', cents_to_euro(reservation.cents_due), '€ ')
    places += ('a été enregistrée.',)
    virement = '' \
        if reservation.paying_seats < 1 else ('p', *due_amount_info,)
    self_url = make_show_reservation_url(bank_id, uuid_hex, script_name=SCRIPT_NAME, server_name=SERVER_NAME)
    respond_html(html_document(
        'Réservation effectuée',
        (('p', 'Votre réservation au nom de ', reservation.name) + places,
         virement,
         ('p', (('a', 'href', f"mailto:{CONFIGURATION['info_email']}"), 'Contactez-nous'),
          ' si vous avez encore des questions.'),
         ('p', 'Un tout grand merci pour votre présence le ', reservation.date,
          ': le soutien de nos auditeurs nous est indispensable!'),
         ('hr',),
         ('p',
          'Ajoutez ', (('a', 'href', self_url), 'cette page'), " à vos favoris ou scannez ce code QR pour suivre l'état actuel de votre réservation:",
          ("br",),
          ('raw', qrcode.make(self_url, image_factory=SvgPathFillImage).to_string().decode('utf8'))))))
