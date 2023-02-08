# -*- coding: utf-8 -*-
import cgitb
import os
import re
import uuid
import time
import urllib

from htmlgen import (
    html_document,
    redirect,
    respond_html,
)
from pricing import (
    price_in_cents,
)
from storage import(
    Reservation,
    ensure_connection,
)


class ValidationException(Exception):
    pass


def is_test_reservation(name, email):
    return name.lower().startswith('test') and email.lower().endswith('@example.com')


def validate_data(
        name, email, extra_comment, places, date,
        outside_main_starter, outside_extra_starter, outside_bolo, outside_extra_dish, outside_dessert,
        inside_main_starter, inside_extra_starter, inside_bolo, inside_extra_dish,
        kids_bolo, kids_extra_dish,
        gdpr_accepts_use, connection):
    (name, email, extra_comment, places, date,
     outside_main_starter, outside_extra_starter, outside_bolo, outside_extra_dish, outside_dessert,
     inside_main_starter, inside_extra_starter, inside_bolo, inside_extra_dish,
     kids_bolo, kids_extra_dish,
     gdpr_accepts_use
     ) = normalize_data(
         name, email, extra_comment, places, date,
         outside_main_starter, outside_extra_starter, outside_bolo, outside_extra_dish, outside_dessert,
         inside_main_starter, inside_extra_starter, inside_bolo, inside_extra_dish,
         kids_bolo, kids_extra_dish,
         gdpr_accepts_use)
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
    if places < 1:
        raise ValidationException("Vous n'avez pas indiqué combien de places vous vouliez réserver")
    if date not in (('2099-01-01', '2099-01-02')
                    if is_test_reservation(name, email)
                    else ('2023-03-25',)):
        raise ValidationException("Il n'y a pas de repas italien ̀à cette date")
    total_menus = inside_bolo + inside_extra_dish
    if inside_extra_starter + inside_main_starter != total_menus:
        raise ValidationException(
            "Le nombre d'entrées ne correspond pas au nombre de plats commandés dans les menus.")
    reservations_count, reserved_seats  = Reservation.count_places(connection, name, email)
    if (reservations_count or 0) > 10:
        raise ValidationException('Il y a déjà trop de réservations à votre nom')
    if (reserved_seats or 0) + places > 60:
        raise ValidationException('Vous réservez ou avez réservé trop de places')
    _, total_bookings = Reservation.count_places(connection)
    MAX_PLACES = 200
    if (total_bookings or 0) + places > MAX_PLACES:
        max_restantes = MAX_PLACES - (total_bookings or 0)
        raise ValidationException(f"Il n'y a plus assez de place dans la salle, il ne reste plus que {max_restantes} places libres.")
    return (name, email, extra_comment, places, date,
            outside_main_starter, outside_extra_starter, outside_bolo, outside_extra_dish, outside_dessert,
            inside_main_starter, inside_extra_starter, inside_bolo, inside_extra_dish,
            kids_bolo, kids_extra_dish,
            gdpr_accepts_use)


def normalize_data(
        name, email, extra_comment, places, date,
        outside_main_starter, outside_extra_starter, outside_bolo, outside_extra_dish, outside_dessert,
        inside_main_starter, inside_extra_starter, inside_bolo, inside_extra_dish,
        kids_bolo, kids_extra_dish,
        gdpr_accepts_use):
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
    extra_comment = safe_strip(extra_comment)
    places = safe_non_negative_int_less_or_equal_than_50(places)
    date = safe_strip(date)
    outside_extra_starter = safe_non_negative_int_less_or_equal_than_50(outside_extra_starter)
    outside_main_starter = safe_non_negative_int_less_or_equal_than_50(outside_main_starter)
    outside_bolo = safe_non_negative_int_less_or_equal_than_50(outside_bolo)
    outside_extra_dish = safe_non_negative_int_less_or_equal_than_50(outside_extra_dish)
    outside_dessert = safe_non_negative_int_less_or_equal_than_50(outside_dessert)
    inside_extra_starter = safe_non_negative_int_less_or_equal_than_50(inside_extra_starter)
    inside_main_starter = safe_non_negative_int_less_or_equal_than_50(inside_main_starter)
    inside_bolo = safe_non_negative_int_less_or_equal_than_50(inside_bolo)
    inside_extra_dish = safe_non_negative_int_less_or_equal_than_50(inside_extra_dish)
    kids_bolo = safe_non_negative_int_less_or_equal_than_50(kids_bolo)
    kids_extra_dish = safe_non_negative_int_less_or_equal_than_50(kids_extra_dish)
    try:
        gdpr_accepts_use = gdpr_accepts_use.lower() in ['yes', 'oui', '1', 'true', 'vrai']
    except Exception:
        gdpr_accepts_use = gdpr_accepts_use and gdpr_accepts_use not in [0, False]
    return (name, email, extra_comment, places, date,
            outside_main_starter, outside_extra_starter, outside_bolo, outside_extra_dish, outside_dessert,
            inside_main_starter, inside_extra_starter, inside_bolo, inside_extra_dish,
            kids_bolo, kids_extra_dish,
            gdpr_accepts_use)


def save_data_sqlite3(name, email, extra_comment, places, date,
                      outside_main_starter, outside_extra_starter, outside_bolo, outside_extra_dish, outside_dessert,
                      inside_main_starter, inside_extra_starter, inside_bolo, inside_extra_dish,
                      kids_bolo, kids_extra_dish,
                      gdpr_accepts_use, origin, connection_or_root_dir):
    connection = ensure_connection(connection_or_root_dir)
    process_id = os.getpid()
    retries = 3
    while retries > 0:
        uuid_hex = uuid.uuid4().hex
        retries -= 1
        timestamp = time.time()
        bank_id = generate_bank_id(timestamp, Reservation.length(connection), process_id)
        try:
            new_row = Reservation(name=name,
                                  email=email,
                                  extra_comment=extra_comment,
                                  places=places,
                                  date=date,
                                  outside_main_starter=outside_main_starter,
                                  outside_extra_starter=outside_extra_starter,
                                  outside_bolo=outside_bolo,
                                  outside_extra_dish=outside_extra_dish,
                                  outside_dessert=outside_dessert,
                                  inside_main_starter=inside_main_starter,
                                  inside_extra_starter=inside_extra_starter,
                                  inside_bolo=inside_bolo,
                                  inside_extra_dish=inside_extra_dish,
                                  kids_bolo=kids_bolo,
                                  kids_extra_dish=kids_extra_dish,
                                  gdpr_accepts_use=gdpr_accepts_use,
                                  cents_due=-1, # To be fixed once the object is initialized
                                  bank_id=append_bank_id_control_number(bank_id),
                                  uuid=uuid_hex,
                                  time=timestamp,
                                  active=True,
                                  origin=origin)
            new_row.cents_due = price_in_cents(new_row)
            with connection:
                new_row.insert_data(connection)
            return new_row
        except Exception:
            if retries > 0:
                time.sleep(0.011)
                pass
            else:
                raise


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


def respond_with_reservation_failed(configuration):
    respond_html(html_document(
        'Erreur interne au serveur',
        (('p',
          "Malheureusement une erreur s'est produite et votre réservation n'a pas été enregistrée.  "
          "Merci de bien vouloir ré-essayer plus tard. ",
          (('a', 'href', f'mailto:{configuration["info_email"]}'), "Contactez-nous"),
          " si ce problème persiste."),)))


def make_show_reservation_url(uuid_hex, server_name=None, script_name=None):
    server_name = os.environ["SERVER_NAME"] if server_name is None else server_name
    script_name = os.environ["SCRIPT_NAME"] if script_name is None else script_name
    return urllib.parse.urlunsplit((
        'https',
        server_name,
        urllib.parse.urljoin(script_name, 'show_reservation.cgi'),
        urllib.parse.urlencode((('uuid_hex', uuid_hex), )),
        ''))


def respond_with_reservation_confirmation(
        name, email, extra_comment, places, date,
        outside_main_starter, outside_extra_starter, outside_bolo, outside_extra_dish, outside_dessert,
        inside_main_starter, inside_extra_starter, inside_bolo, inside_extra_dish,
        kids_bolo, kids_extra_dish,
        gdpr_accepts_use, connection, configuration, origin=None):
    try:
        new_row = save_data_sqlite3(
            name, email, extra_comment, places, date,
            outside_main_starter, outside_extra_starter, outside_bolo, outside_extra_dish, outside_dessert,
            inside_main_starter, inside_extra_starter, inside_bolo, inside_extra_dish,
            kids_bolo, kids_extra_dish,
            gdpr_accepts_use, origin, connection)
        redirection_url = make_show_reservation_url(
            new_row.uuid,
            script_name=(os.environ["SCRIPT_NAME"]
                         if origin is None else
                         os.path.dirname(os.environ["SCRIPT_NAME"])))
    except Exception:
        respond_with_reservation_failed(configuration)
        cgitb.handler()
    else:
        redirect(redirection_url)


def respond_with_reservations_closed():
    respond_html(html_document(
        'Soirée Italienne',
        (('p',
          "Nous n'acceptons plus de réservations mais il reste encore des places.  Présentez-vous ",
          "simplement à l'entrée et vous serez les bienvenus."),)))
