#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import os

import config
from htmlgen import (
    html_document,
    print_content_type,
    redirect,
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
        raise ValidationException('No contact information')
    try:
        at_sign = email.index('@', 1) # email address must contain '@' but may not start with it
        host_dot = email.index('.', at_sign + 1)
    except ValueError:
        email_is_bad = email != ''
    else:
        email_is_bad = False
    if email_is_bad:
        raise ValidationException('Invalid email address')
    if paying_seats + free_seats < 1:
        raise ValidationException('No seats reserved')
    if date not in (('2099-01-01', '2099-01-02')
                    if is_test_reservation(name, email)
                    else ('2021-12-04', '2021-12-05')):
        raise ValidationException('No representation')
    reservations_count, reserved_seats  = connection.execute(
        'SELECT COUNT(*), SUM(paying_seats + free_seats) FROM reservations WHERE LOWER(name) = :name OR LOWER(email) = :email',
        {'name': name.lower(), 'email': email.lower()}
    ).fetchone()
    if (reservations_count or 0) > 10:
        raise ValidationException('Too many distinct reservations')
    if (reserved_seats or 0) + paying_seats + free_seats > 60:
        raise ValidationException('Too many seats reserved')
    return (name, email, date, paying_seats, free_seats, gdpr_accepts_use)


def respond_with_validation_error(form, e):
    respond_html(html_document(
        'Données invalides dans le formulaire',
        (('p', "Votre formulaire contient l'erreur suivante:"),
         ('p', (('code', 'lang', 'en'), str(e))))
        + ((('p', 'Formulaire vide.'),)
           if len(form) < 1 else
           (('p', "Voici les données reçues"),
            ('ul', *tuple(('li', ('code', k), ': ', repr(form[k]))
                          for k in sorted(form.keys())))))))


if __name__ == '__main__':
    if os.getenv('REQUEST_METHOD') != 'POST':
        redirect('https://www.srhbraine.be/concert-de-gala-2021/')
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
            respond_with_validation_error(form, e)
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
