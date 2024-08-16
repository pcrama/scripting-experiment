#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import os
import re

import config
from htmlgen import (
    html_document,
    print_content_type,
    redirect,
    redirect_to_event,
    respond_html,
)
from storage import(
    Reservation,
    create_db,
)
from lib_post_reservation import(
    normalize_data,
    respond_with_reservation_confirmation,
    respond_with_reservation_failed,
    save_data_sqlite3
)

'''
Input:
- name
- email
- date
- paying_seats
- free_seats
- gdpr_accepts_use
- uuid

Generate bank_id (10 digits, 33 bits):
- time: 7 bits
- number of previous calls: 10 bits
- process ID: os.getpid(), 16 bits

Save:
- name
- email
- date
- paying_seats
- free_seats
- gdpr_accepts_use
- bank_id
- uuid
- time
'''


class ValidationException(Exception):
    pass


def is_test_reservation(name, email):
    return name.lower().startswith('test') and email.lower().endswith('@example.com')


def validate_data(name, email, date, paying_seats, free_seats, gdpr_accepts_use, connection):
    (name, email, date, paying_seats, free_seats, gdpr_accepts_use) = normalize_data(
        name, email, date, paying_seats, free_seats, gdpr_accepts_use)
    if not(name and email):
        raise ValidationException('Vos données de contact sont incomplètes')
    INVALID_EMAIL = "L'adresse email renseignée n'a pas le format requis"
    try:
        email_match = re.fullmatch(
            '[^@]+@(\\w+\\.)+\\w\\w+', email, flags=re.IGNORECASE | re.UNICODE)
    except Exception:
        raise ValidationException(INVALID_EMAIL)
    else:
        if email_match is None:
            raise ValidationException(INVALID_EMAIL)
    if paying_seats + free_seats < 1:
        raise ValidationException("Vous n'avez pas indiqué combien de sièges vous vouliez réserver")
    if date not in (('2099-01-01', '2099-01-02')
                    if is_test_reservation(name, email)
                    else ('2022-12-10', '2022-12-11',)):
        raise ValidationException("Il n'y a pas de concert ̀à cette date")
    reservations_count, reserved_seats  = Reservation.count_reservations(connection, name, email)
    if (reservations_count or 0) > 10:
        raise ValidationException('Il y a déjà trop de réservations à votre nom')
    if (reserved_seats or 0) + paying_seats + free_seats > 60:
        raise ValidationException('Vous réservez ou avez réservé trop de sièges')
    return (name, email, date, paying_seats, free_seats, gdpr_accepts_use)


def respond_with_validation_error(form, e, configuration):
    respond_html(html_document(
        'Données invalides dans le formulaire',
        (('p', "Votre formulaire contient l'erreur suivante:"),
         ('p', (('code', 'lang', 'en'), str(e))),
        *((('p', 'Formulaire vide.'),)
          if len(form) < 1 else
          (('p', "Voici les données reçues"),
           ('ul', *tuple(('li', ('code', k), ': ', repr(form[k]))
                         for k in sorted(form.keys()))))),
         ('p',
          (('a', 'href', f'mailto:{configuration["info_email"]}'), "Contactez-nous"),
          " si vous désirez de l'aide pour enregistrer votre réservation."))))


if __name__ == '__main__':
    if os.getenv('REQUEST_METHOD') != 'POST':
        redirect_to_event()
    CONFIGURATION = config.get_configuration()

    cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

    try:
        db_connection = create_db(CONFIGURATION)

        # Get form data
        form = cgi.FieldStorage()
        name = form.getfirst('name', default='')
        email = form.getfirst('email', default='')
        date = form.getfirst('date', default='')
        paying_seats = form.getfirst('paying_seats', default=0)
        free_seats = form.getfirst('free_seats', default=0)
        gdpr_accepts_use = form.getfirst('gdpr_accepts_use', default=False)

        try:
            (name, email, date, paying_seats, free_seats, gdpr_accepts_use) = validate_data(
                name, email, date, paying_seats, free_seats, gdpr_accepts_use, db_connection)
        except ValidationException as e:
            respond_with_validation_error(form, e, CONFIGURATION)
        else:
            respond_with_reservation_confirmation(
                name,
                email,
                date,
                paying_seats,
                free_seats,
                gdpr_accepts_use,
                db_connection,
                CONFIGURATION)
    except Exception:
        # cgitb needs the content-type header
        if print_content_type('text/html; charset=utf-8'):
            print('Content-Language: en')
            print()
        raise
