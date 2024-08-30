# -*- coding: utf-8 -*-
import cgitb
import os
import re
import time
from typing import Any, Union
import urllib
import uuid
import sqlite3

from htmlgen import (
    cents_to_euro,
    html_document,
    redirect,
    respond_html,
)
from storage import(
    Reservation,
    ensure_connection,
)


class ValidationException(Exception):
    pass


def is_test_reservation(name: str, email: str) -> bool:
    return name.lower().startswith('test') and email.lower().endswith('@example.com')


def normalize_data(name: str, email: str, date: str, paying_seats: str, free_seats: str, gdpr_accepts_use: str) -> tuple[str, str, str, int, int, bool]:
    def safe_strip(x: Union[str, None]) -> str:
        if x is None:
            return ''
        else:
            return ' '.join(x.split())[:256]
    def safe_non_negative_int_less_or_equal_than_50(x: str) -> int:
        try:
            return max(0, min(int(x), 50))
        except Exception:
            return 0
    name = safe_strip(name)
    email = safe_strip(email)
    date = safe_strip(date)
    try:
        gdpr_accepts_use_bool = gdpr_accepts_use.lower() in ['yes', 'oui', '1', 'true', 'vrai']
    except Exception:
        gdpr_accepts_use_bool = bool(gdpr_accepts_use) and gdpr_accepts_use not in [0, False]
    return (
        name,
        email,
        date,
        safe_non_negative_int_less_or_equal_than_50(paying_seats),
        safe_non_negative_int_less_or_equal_than_50(free_seats),
        gdpr_accepts_use_bool)


def validate_data(name, email, date, paying_seats, free_seats, gdpr_accepts_use, connection):
    (name, email, date, paying_seats, free_seats, gdpr_accepts_use) = normalize_data(
        name, email, date, paying_seats, free_seats, gdpr_accepts_use)
    if not(name and email):
        raise ValidationException('Vos données de contact sont incomplètes')
    INVALID_EMAIL = "L'adresse email renseignée n'a pas le format requis"
    try:
        email_match = re.fullmatch('[^@]+@([\\w-]+\\.)+\\w\\w+', email, flags=re.IGNORECASE | re.UNICODE)
    except Exception:
        raise ValidationException(INVALID_EMAIL)
    else:
        if email_match is None:
            raise ValidationException(INVALID_EMAIL)
    if paying_seats + free_seats < 1:
        raise ValidationException("Vous n'avez pas indiqué combien de sièges vous vouliez réserver")
    if date not in (('2099-01-01', '2099-01-02')
                    if is_test_reservation(name, email)
                    else ('2024-11-30', '2024-12-01',)):
        raise ValidationException(f"Il n'y a pas de concert le {date!r}")
    reservations_count, reserved_seats  = Reservation.count_reservations(connection, name, email)
    if (reservations_count or 0) > 10:
        raise ValidationException('Il y a déjà trop de réservations à votre nom')
    if (reserved_seats or 0) + paying_seats + free_seats > 60:
        raise ValidationException('Vous réservez ou avez réservé trop de sièges')
    return (name, email, date, paying_seats, free_seats, gdpr_accepts_use)


def save_data_sqlite3(
        name: str, email: str, date: str, paying_seats: int, free_seats: int, gdpr_accepts_use: bool,
        cents_due: int, origin: Union[str, None], connection_or_root_dir: Union[sqlite3.Connection, dict[str, Any]]
) -> Reservation:
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


def generate_payment_QR_code_content(remaining_due: int, bank_id: str, config: dict[str, Any]) -> str:
    # See scan2pay.info
    name = config.get("organizer_name", "Name")
    bic = config.get("organizer_bic", "BIC")
    iban = "".join(ch for ch in config.get("bank_account", "BExxxx") if ch in "BE" or ch.isdigit())
    amount = cents_to_euro(remaining_due)
    return ("BCD\n001\n1\nSCT\n" + bic + "\n" + name + "\n" + iban + "\n" + "EUR" + amount + "\n\n" + bank_id)
