#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import os

import config
from htmlgen import (
    cents_to_euro,
    format_bank_id,
    html_document,
    print_content_type,
    redirect,
    respond_html,
)
from storage import(
    Reservation,
    create_db,
)


if __name__ == '__main__':
    if os.getenv('REQUEST_METHOD') != 'GET':
        redirect('https://www.srhbraine.be/concert-de-gala-2021/')
    CONFIGURATION = config.get_configuration()

    cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

    if print_content_type('text/html; charset=utf-8'):
        print('Content-Language: en')
        print()

    db_connection = create_db(CONFIGURATION)

    # Get form data
    form = cgi.FieldStorage()
    bank_id = form.getfirst('bank_id', default='')
    uuid_hex = form.getfirst('uuid_hex', default='')

    reservation = next(Reservation.select(
        db_connection,
        filtering=[('bank_id', bank_id), ('uuid', uuid_hex)],
        limit=1))
    places = (' pour ',)
    if reservation.paying_seats > 0:
        places += (str(reservation.paying_seats),
                   ' place payante ' if reservation.paying_seats == 1 else ' places payantes ')
    if reservation.free_seats > 0:
        if reservation.paying_seats > 0:
            places += ('et ',)
        places += (str(reservation.free_seats),
                   ' place gratuite ' if reservation.free_seats == 1 else ' places gratuites ')
    if reservation.paying_seats > 0:
        places += ('au prix de ', cents_to_euro(reservation.cents_due), '€ ')
    places += ('a été enregistrée.',)
    virement = '' \
        if reservation.paying_seats < 1 else (
                'p', 'Veuillez effectuer un virement pour ',
                cents_to_euro(reservation.cents_due),
                '€ au compte BExx XXXX YYYY ZZZZ en mentionnant la communication '
                'structurée ', ('code', format_bank_id(reservation.bank_id)), '.')
    respond_html(html_document(
        'Réservation effectuée',
        (('p', 'Votre réservation au nom de ', reservation.name) + places,
         virement,
         ('p', 'Un tout grand merci pour votre présence le ', reservation.date,
          ': le soutien de nos auditeurs nous est indispensable!'))))