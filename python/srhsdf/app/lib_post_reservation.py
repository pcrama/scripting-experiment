# -*- coding: utf-8 -*-
import cgitb
import os
import time
import urllib
import uuid

from htmlgen import (
    html_document,
    redirect,
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
            return ' '.join(x.split())[:256]
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
                      cents_due, origin, connection_or_root_dir) -> Reservation:
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
                                  uuid=uuid_hex,
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
    raise RuntimeError(f"Unable to save Reservation for {name} {email}")


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


def respond_with_reservation_failed(configuration):
    respond_html(html_document(
        'Erreur interne au serveur',
        (('p',
          "Malheureusement une erreur s'est produite et votre réservation n'a pas été enregistrée.  "
          "Merci de bien vouloir ré-essayer plus tard. ",
          (('a', 'href', f'mailto:{configuration["info_email"]}'), "Contactez-nous"),
          " si ce problème persiste."),)))


def make_show_reservation_url(bank_id, uuid_hex, server_name=None, script_name=None):
    server_name = os.environ["SERVER_NAME"] if server_name is None else server_name
    script_name = os.environ["SCRIPT_NAME"] if script_name is None else script_name
    base_url = urllib.parse.urljoin(
        f'https://{server_name}{script_name}', 'show_reservation.cgi')
    split_result = urllib.parse.urlsplit(base_url)
    return urllib.parse.urlunsplit((
        'https',
        server_name,
        urllib.parse.urljoin(script_name, 'show_reservation.cgi'),
        urllib.parse.urlencode((('bank_id', bank_id), ('uuid_hex', uuid_hex))),
        ''))


def respond_with_reservation_confirmation(
        name, email, date, paying_seats, free_seats, gdpr_accepts_use, connection, configuration, origin=None):
    cents_due = compute_price(paying_seats, date, configuration)
    try:
        new_row = save_data_sqlite3(
            name, email, date, paying_seats, free_seats, gdpr_accepts_use, cents_due, origin, connection)
    except Exception:
        respond_with_reservation_failed(configuration)
        cgitb.handler()
    else:
        redirect(make_show_reservation_url(
            new_row.bank_id,
            new_row.uuid,
            script_name=(os.environ["SCRIPT_NAME"]
                         if origin is None else
                         os.path.dirname(os.environ["SCRIPT_NAME"]))))
