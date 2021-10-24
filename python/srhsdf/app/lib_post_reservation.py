# -*- coding: utf-8 -*-
import os
import uuid
import time

from htmlgen import (
    cents_to_euro,
    format_bank_id,
    html_document,
    respond_html,
)
from storage import(
    Reservation,
    ensure_connection,
)


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


def save_data_sqlite3(name, email, date, paying_seats, free_seats, gdpr_accepts_use,
                      cents_due, origin, connection_or_root_dir):
    connection = ensure_connection(connection_or_root_dir)
    process_id = os.getpid()
    uuid_hex = uuid.uuid4().hex
    retries = 3
    while retries > 0:
        retries -= 1
        timestamp = time.time()
        bank_id = generate_bank_id(timestamp, Reservation.length(connection), process_id)
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
                                  timestamp=timestamp,
                                  active=True,
                                  origin=origin)
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


def compute_price(paying_seats, date, configuration):
    return paying_seats * configuration['paying_seat_cents']


def respond_with_reservation_failed():
    respond_html(html_document(
        'Erreur interne au serveur',
        (('p',
          "Malheureusement une erreur s'est produite et votre réservation n'a pas été enregistrée.  "
          "Merci de bien vouloir ré-essayer plus tard."),)))


def respond_with_reservation_confirmation(
        name, email, date, paying_seats, free_seats, gdpr_accepts_use, connection, configuration, origin=None):
    cents_due = compute_price(paying_seats, date, configuration)
    try:
        new_row = save_data_sqlite3(
            name, email, date, paying_seats, free_seats, gdpr_accepts_use, cents_due, origin, connection)
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
        places += ('au prix de ', cents_to_euro(cents_due), '€ ')
    places += ('a été enregistrée.',)
    virement = '' \
        if paying_seats < 1 else (
                'p', 'Veuillez effectuer un virement pour ',
                cents_to_euro(cents_due),
                '€ au compte BExx XXXX YYYY ZZZZ en mentionnant la communication '
                'structurée ', ('code', format_bank_id(new_row.bank_id)), '.')
    respond_html(html_document(
        'Réservation effectuée',
        (('p', 'Votre réservation au nom de ', name) + places,
         virement,
         ('p', 'Un tout grand merci pour votre présence le ', date, ': le soutien '
          'de nos auditeurs nous est indispensable!'))))
