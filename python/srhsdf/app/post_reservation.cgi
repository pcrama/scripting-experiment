#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import contextlib
import glob
import json
import os
import sys
import time
import uuid

from htmlgen import (
    cents_to_euro,
    html_document,
    redirect,
    respond_html,
)
from storage import(
    Reservation,
    create_db,
    ensure_connection,
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

try:
    SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
except NameError:
    SCRIPT_DIR = os.path.realpath(os.getcwd())


def normalize_data(name, email, date, paying_seats, free_seats, gdpr_accepts_use):
    def safe_strip(x):
        if x is None:
            return ''
        else:
            return ' '.join(x.split())
    def safe_non_negative_int_less_or_equal_than_50(x):
        try:
            x = int(x)
            return max(0, min(x, 50))
        except Exception:
            return 0
    name = safe_strip(name)
    email = safe_strip(email)
    date = safe_strip(date)
    paying_seats = safe_non_negative_int_less_or_equal_than_50(paying_seats)
    free_seats = safe_non_negative_int_less_or_equal_than_50(free_seats)
    try:
        gdpr_accepts_use = gdpr_accepts_use.lower() in ['yes', 'oui', '1', 'true', 'vrai']
    except Exception:
        gdpr_accepts_use = gdpr_accepts_use and gdpr_accepts_use not in [0, False]
    return (name, email, date, paying_seats, free_seats, gdpr_accepts_use)


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


def save_data_sqlite3(name, email, date, paying_seats, free_seats, gdpr_accepts_use,
                      cents_due, connection_or_root_dir):
    connection = ensure_connection(connection_or_root_dir)
    process_id = os.getpid()
    uuid_hex = uuid.uuid4().hex
    def count_reservations():
        return connection.execute('SELECT COUNT(*) FROM reservations').fetchone()[0]
    retries = 3
    while retries > 0:
        retries -= 1
        timestamp = time.time()
        bank_id = generate_bank_id(timestamp, count_reservations(), process_id)
        try:
            new_row = Reservation(name=name,
                                  email=email,
                                  date=date,
                                  paying_seats=paying_seats,
                                  free_seats=free_seats,
                                  gdpr_accepts_use=gdpr_accepts_use,
                                  cents_due=cents_due,
                                  bank_id=append_bank_id_control_number(bank_id),
                                  uuid_hex=uuid_hex,
                                  timestamp=timestamp)
            with connection:
                new_row.insert_data(connection)
            return new_row
        except Exception:
            if retries > 0:
                time.sleep(0.011)
                pass
            else:
                raise


def to_bits(n):
    while n > 0:
        if n & 1 == 0:
            yield 0
        else:
            yield 1
        n >>= 1


def generate_bank_id(time_time, number_of_previous_calls, process_id):
    data = [(x & ((1 << b) - 1), b)
            for (x, b)
            in ((round(time_time * 100.0), 7),
                (number_of_previous_calls, 10),
                (process_id, 16))]
    bits = 0
    n = 0
    for (x, b) in data:
        n = (n << b) + x
    return f'{n:010}'


def append_bank_id_control_number(s):
    n = 0
    for c in s:
        if c == '/':
            continue
        elif not c.isdigit():
            raise Exception(f'{c} is not a digit')
        n = (n * 10 + int(c)) % 97
    if n == 0:
        n = 97
    return f'{s}{n:02}'


def respond_with_validation_error(form, e):
    respond_html(html_document(
        'Données invalides dans le formulaire',
        (('p', "Votre formulaire contient l'erreur suivante:"),
         ('p', (('code', 'lang', 'en'), str(e))))
        + ((('p', 'Formulaire vide.'),)
           if len(form) < 1 else
           (('p', "Voici les données reçues"),
            ('ul',) + tuple(('li', ('code', k), ': ', repr(form[k]))
                         for k in form.keys())))))


def compute_price(paying_seats, date):
    return paying_seats * CONFIGURATION['paying_seat_cents']


def respond_with_reservation_failed():
    respond_html(html_document(
        'Erreur interne au serveur',
        (('p',
          "Malheureusement une erreur s'est produite et votre réservation n'a pas été enregistrée.  "
          "Merci de bien vouloir ré-essayer plus tard."),)))



def respond_with_reservation_confirmation(
        name, email, date, paying_seats, free_seats, gdpr_accepts_use, connection):
    cents_due = compute_price(paying_seats, date)
    try:
        new_row = save_data_sqlite3(
            name, email, date, paying_seats, free_seats, gdpr_accepts_use, cents_due, connection)
    except Exception:
        respond_with_reservation_failed()
        cgitb.handler()
    places = (' pour ',)
    if paying_seats > 0:
        places += (str(paying_seats),
                   ' place payante ' if paying_seats == 1 else ' places payantes ')
    if free_seats > 0:
        if paying_seats > 0:
            places += ('et ',)
        places += (str(free_seats),
                   ' place gratuite ' if free_seats == 1 else ' places gratuites ')
    if paying_seats > 0:
        places += ('au prix de ', cents_to_euro(cents_due), '€')
    places += (' a été enregistrée.',)
    virement = '' \
        if paying_seats < 1 else (
                'p', 'Veuillez effectuer un virement pour ',
                cents_to_euro(cents_due),
                '€ au compte BExx XXXX YYYY ZZZZ en mentionnant la communication '
                'structurée ', ('code', new_row.bank_id), '.')
    respond_html(html_document(
        'Réservation effectuée',
        (('p', 'Votre réservation au nom de ', name) + places,
         virement,
         ('p', 'Un tout grand merci pour votre présence le ', date, ': le soutien '
          'de nos auditeurs nous est indispensable!'))))

if __name__ == '__main__':
    if os.getenv('REQUEST_METHOD') != 'POST':
        redirect('https://www.srhbraine.be/concert-de-gala-2021/')
    # CGI script configuration
    CONFIGURATION_DEFAULTS = {
        'logdir': os.getenv('TEMP', SCRIPT_DIR),
        'dbdir': os.getenv('TEMP', SCRIPT_DIR),
        'cgitb_display': 1,
        'paying_seat_cents': 500,
    }
    try:
        with open(os.path.join(SCRIPT_DIR, 'configuration.json')) as f:
            CONFIGURATION = json.load(f)
    except Exception:
        CONFIGURATION = dict()
    for k, v in CONFIGURATION_DEFAULTS.items():
        CONFIGURATION.setdefault(k, v)

    cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

    try:
        db_connection = create_db(CONFIGURATION['dbdir'])

        # Get form data
        form = cgi.FieldStorage()
        name = form.getfirst('name', default='')
        email = form.getfirst('email', default='')
        date = form.getfirst('date', default='')
        paying_seats = form.getfirst('paying_seats', default=0)
        free_seats = form.getfirst('free_seats', default=0)
        gdpr_accepts_use = form.getfirst('gdpr_accepts_use', default=False)
    except Exception:
        # cgitb needs the content-type header
        print('Content-Type: text/html; charset=utf-8')
        print('Content-Language: en')
        print()
        raise

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
            db_connection)
