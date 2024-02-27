# -*- coding: utf-8 -*-
import cgitb
import os
import re
import time
from typing import Any, Optional
from urllib.parse import urlunsplit, urljoin, urlencode
import uuid

from htmlgen import (
    cents_to_euro,
    html_document,
    redirect,
    respond_html,
)
from pricing import (
    price_in_cents,
)
from storage import(
    FullMealCount,
    KidMealCount,
    MenuCount,
    Reservation,
    ensure_connection,
)


class ValidationException(Exception):
    pass


def is_test_reservation(name, email):
    return name.lower().startswith('test') and email.lower().endswith('@example.com')


def validate_data(
        name, email, extra_comment, places, date,
        outside_main_starter, outside_extra_starter, outside_main_dish, outside_extra_dish, outside_third_dish, outside_main_dessert, outside_extra_dessert,
        inside_main_starter, inside_extra_starter, inside_main_dish, inside_extra_dish, inside_third_dish, inside_main_dessert, inside_extra_dessert,
        kids_main_dish, kids_extra_dish, kids_third_dish, kids_main_dessert, kids_extra_dessert,
        gdpr_accepts_use, connection):
    (name, email, extra_comment, places, date,
     outside_main_starter, outside_extra_starter, outside_main_dish, outside_extra_dish, outside_third_dish, outside_main_dessert, outside_extra_dessert,
     inside_main_starter, inside_extra_starter, inside_main_dish, inside_extra_dish, inside_third_dish, inside_main_dessert, inside_extra_dessert,
     kids_main_dish, kids_extra_dish, kids_third_dish, kids_main_dessert, kids_extra_dessert,
     gdpr_accepts_use
     ) = normalize_data(
         name, email, extra_comment, places, date,
         outside_main_starter, outside_extra_starter, outside_main_dish, outside_extra_dish, outside_third_dish, outside_main_dessert, outside_extra_dessert,
         inside_main_starter, inside_extra_starter, inside_main_dish, inside_extra_dish, inside_third_dish, inside_main_dessert, inside_extra_dessert,
         kids_main_dish, kids_extra_dish, kids_third_dish, kids_main_dessert, kids_extra_dessert,
         gdpr_accepts_use
     )
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
    if places < 1:
        raise ValidationException("Vous n'avez pas indiqué combien de places vous vouliez réserver")
    REAL_DATES = ('2024-03-23',)
    if date not in (('2099-01-01', '2099-01-02')
                    if is_test_reservation(name, email)
                    else REAL_DATES):
        raise ValidationException(f"Il n'y a pas de repas italien ̀à cette date: {date=}")
    total_menus = inside_main_dish + inside_extra_dish + inside_third_dish
    if inside_extra_starter + inside_main_starter != total_menus:
        raise ValidationException(
            "Le nombre d'entrées ne correspond pas au nombre de plats commandés dans les menus.")
    if inside_extra_dessert + inside_main_dessert != total_menus:
        raise ValidationException(
            "Le nombre de desserts ne correspond pas au nombre de plats commandés dans les menus.")
    kids_total_menus = kids_main_dish + kids_extra_dish + kids_third_dish
    if kids_extra_dessert + kids_main_dessert != kids_total_menus:
        raise ValidationException(
            "Le nombre de desserts ne correspond pas au nombre de plats commandés dans les menus enfants.")
    reservations_count, reserved_seats  = Reservation.count_places(connection, name, email)
    if (reservations_count or 0) > 10:
        raise ValidationException('Il y a déjà trop de réservations à votre nom')
    if (reserved_seats or 0) + places > 60:
        raise ValidationException('Vous réservez ou avez réservé trop de places')
    _, total_bookings = Reservation.count_places(connection)
    MAX_PLACES = 140
    if (total_bookings or 0) + places > MAX_PLACES:
        max_restantes = MAX_PLACES - (total_bookings or 0)
        raise ValidationException(f"Il n'y a plus assez de place dans la salle, il ne reste plus que {max_restantes} places libres.")
    return (name, email, extra_comment, places, date,
     outside_main_starter, outside_extra_starter, outside_main_dish, outside_extra_dish, outside_third_dish, outside_main_dessert, outside_extra_dessert,
     inside_main_starter, inside_extra_starter, inside_main_dish, inside_extra_dish, inside_third_dish, inside_main_dessert, inside_extra_dessert,
     kids_main_dish, kids_extra_dish, kids_third_dish, kids_main_dessert, kids_extra_dessert,
     gdpr_accepts_use
     )


def normalize_data(
        name, email, extra_comment, places, date,
        outside_main_starter, outside_extra_starter, outside_main_dish, outside_extra_dish, outside_third_dish, outside_main_dessert, outside_extra_dessert,
        inside_main_starter, inside_extra_starter, inside_main_dish, inside_extra_dish, inside_third_dish, inside_main_dessert, inside_extra_dessert,
        kids_main_dish, kids_extra_dish, kids_third_dish, kids_main_dessert, kids_extra_dessert,
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
    outside_main_starter = safe_non_negative_int_less_or_equal_than_50(outside_main_starter)
    outside_extra_starter = safe_non_negative_int_less_or_equal_than_50(outside_extra_starter)
    outside_main_dish = safe_non_negative_int_less_or_equal_than_50(outside_main_dish)
    outside_extra_dish = safe_non_negative_int_less_or_equal_than_50(outside_extra_dish)
    outside_third_dish = safe_non_negative_int_less_or_equal_than_50(outside_third_dish)
    outside_main_dessert = safe_non_negative_int_less_or_equal_than_50(outside_main_dessert)
    outside_extra_dessert = safe_non_negative_int_less_or_equal_than_50(outside_extra_dessert)
    inside_main_starter = safe_non_negative_int_less_or_equal_than_50(inside_main_starter)
    inside_extra_starter = safe_non_negative_int_less_or_equal_than_50(inside_extra_starter)
    inside_main_dish = safe_non_negative_int_less_or_equal_than_50(inside_main_dish)
    inside_extra_dish = safe_non_negative_int_less_or_equal_than_50(inside_extra_dish)
    inside_third_dish = safe_non_negative_int_less_or_equal_than_50(inside_third_dish)
    inside_main_dessert = safe_non_negative_int_less_or_equal_than_50(inside_main_dessert)
    inside_extra_dessert = safe_non_negative_int_less_or_equal_than_50(inside_extra_dessert)
    kids_main_dish = safe_non_negative_int_less_or_equal_than_50(kids_main_dish)
    kids_extra_dish = safe_non_negative_int_less_or_equal_than_50(kids_extra_dish)
    kids_third_dish = safe_non_negative_int_less_or_equal_than_50(kids_third_dish)
    kids_main_dessert = safe_non_negative_int_less_or_equal_than_50(kids_main_dessert)
    kids_extra_dessert = safe_non_negative_int_less_or_equal_than_50(kids_extra_dessert)
    try:
        gdpr_accepts_use = gdpr_accepts_use.lower() in ['yes', 'oui', '1', 'true', 'vrai']
    except Exception:
        gdpr_accepts_use = gdpr_accepts_use and gdpr_accepts_use not in [0, False]
    return (name, email, extra_comment, places, date,
            outside_main_starter, outside_extra_starter, outside_main_dish, outside_extra_dish, outside_third_dish, outside_main_dessert, outside_extra_dessert,
            inside_main_starter, inside_extra_starter, inside_main_dish, inside_extra_dish, inside_third_dish, inside_main_dessert, inside_extra_dessert,
            kids_main_dish, kids_extra_dish, kids_third_dish, kids_main_dessert, kids_extra_dessert,
            gdpr_accepts_use)


def save_data_sqlite3(name, email, extra_comment, places, date,
                      outside_main_starter, outside_extra_starter, outside_main_dish, outside_extra_dish, outside_third_dish, outside_main_dessert, outside_extra_dessert,
                      inside_main_starter, inside_extra_starter, inside_main_dish, inside_extra_dish, inside_third_dish, inside_main_dessert, inside_extra_dessert,
                      kids_main_dish, kids_extra_dish, kids_third_dish, kids_main_dessert, kids_extra_dessert,
                      gdpr_accepts_use, origin, connection_or_root_dir) -> Optional[Reservation]:
    connection = ensure_connection(connection_or_root_dir)
    process_id = os.getpid()
    retries = 3
    while retries > 0:
        uuid_hex = uuid.uuid4().hex
        retries -= 1
        timestamp = time.time()
        bank_id = generate_bank_id(timestamp, Reservation.length(connection), process_id)
        try:
            new_row = Reservation(
                name=name,
                email=email,
                extra_comment=extra_comment,
                places=places,
                date=date,
                outside=FullMealCount(
                    main_starter=outside_main_starter, extra_starter=outside_extra_starter,
                    main_dish=outside_main_dish, extra_dish=outside_extra_dish, third_dish=outside_third_dish,
                    main_dessert=outside_main_dessert, extra_dessert=outside_extra_dessert,
                ),
                inside=MenuCount(
                    main_starter=inside_main_starter, extra_starter=inside_extra_starter,
                    main_dish=inside_main_dish, extra_dish=inside_extra_dish, third_dish=inside_third_dish,
                    main_dessert=inside_main_dessert, extra_dessert=inside_extra_dessert,
                ),
                kids=KidMealCount(
                    main_dish=kids_main_dish, extra_dish=kids_extra_dish, third_dish=kids_third_dish,
                    main_dessert=kids_main_dessert, extra_dessert=kids_extra_dessert,
                ),
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


def make_show_reservation_url(uuid_hex: str, server_name: Optional[str]=None, script_name: Optional[str]=None) -> str:
    server_name = os.environ["SERVER_NAME"] if server_name is None else server_name
    script_name = os.environ["SCRIPT_NAME"] if script_name is None else script_name
    return urlunsplit((
        'https',
        server_name,
        urljoin(script_name, 'show_reservation.cgi'),
        urlencode((('uuid_hex', uuid_hex), )),
        ''))


def respond_with_reservation_confirmation(
        name, email, extra_comment, places, date,
        outside_main_starter, outside_extra_starter, outside_main_dish, outside_extra_dish, outside_third_dish, outside_main_dessert, outside_extra_dessert,
        inside_main_starter, inside_extra_starter, inside_main_dish, inside_extra_dish, inside_third_dish, inside_main_dessert, inside_extra_dessert,
        kids_main_dish, kids_extra_dish, kids_third_dish, kids_main_dessert, kids_extra_dessert,
        gdpr_accepts_use, connection, configuration, origin=None):
    try:
        new_row = save_data_sqlite3(
            name, email, extra_comment, places, date,
            outside_main_starter, outside_extra_starter, outside_main_dish, outside_extra_dish, outside_third_dish, outside_main_dessert, outside_extra_dessert,
            inside_main_starter, inside_extra_starter, inside_main_dish, inside_extra_dish, inside_third_dish, inside_main_dessert, inside_extra_dessert,
            kids_main_dish, kids_extra_dish, kids_third_dish, kids_main_dessert, kids_extra_dessert,
            gdpr_accepts_use, origin, connection)
        if new_row is None:
            raise ValueError("Unable to save reservation in DB")
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


def generate_payment_QR_code_content(remaining_due: int, bank_id: str, config: dict[str, Any]) -> str:
    name = config.get("organizer_name", "Name")
    bic = config.get("organizer_bic", "BIC")
    iban = "".join(ch for ch in config.get("bank_account", "BExxxx") if ch in "BE" or ch.isdigit())
    amount = cents_to_euro(remaining_due)
    remit = bank_id # apparently both are needed to get the three banks I tested to include the information
    inf = bank_id # additional info
    return ("BCD\n001\n1\nSCT\n" + bic + "\n" + name + "\n" + iban + "\n" + "EUR" + amount + "\n" + remit + "\n" + inf)
