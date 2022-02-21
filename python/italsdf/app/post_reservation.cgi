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
- outside_fondus
- outside_assiettes
- outside_bolo
- outside_scampis
- outside_tiramisu
- outside_tranches
- inside_fondus
- inside_assiettes
- inside_bolo
- inside_scampis
- inside_tiramisu
- inside_tranches
- gdpr_accepts_use
- uuid
- time
- active
- origin

Save:
- name
- email
- date
- outside_fondus
- outside_assiettes
- outside_bolo
- outside_scampis
- outside_tiramisu
- outside_tranches
- inside_fondus
- inside_assiettes
- inside_bolo
- inside_scampis
- inside_tiramisu
- inside_tranches
- gdpr_accepts_use
- uuid
- time
- active
- origin
'''


class ValidationException(Exception):
    pass


def is_test_reservation(name, email):
    return name.lower().startswith('test') and email.lower().endswith('@example.com')


def validate_data(
        name, email, places, date,
        outside_fondus, outside_assiettes, outside_bolo, outside_scampis, outside_tiramisu, outside_tranches,
        inside_fondus, inside_assiettes, inside_bolo, inside_scampis, inside_tiramisu, inside_tranches,
        gdpr_accepts_use, connection):
    (name, email, places, date,
     outside_fondus, outside_assiettes, outside_bolo, outside_scampis, outside_tiramisu, outside_tranches,
     inside_fondus, inside_assiettes, inside_bolo, inside_scampis, inside_tiramisu, inside_tranches,
     gdpr_accepts_use
     ) = normalize_data(
         name, email, places, date,
         outside_fondus, outside_assiettes, outside_bolo, outside_scampis, outside_tiramisu, outside_tranches,
         inside_fondus, inside_assiettes, inside_bolo, inside_scampis, inside_tiramisu, inside_tranches,
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
                    else ('2022-03-19',)):
        raise ValidationException("Il n'y a pas de repas italien ̀à cette date")
    total_menus = inside_bolo + inside_scampis
    if inside_fondus + inside_assiettes != total_menus or inside_tiramisu + inside_tranches != total_menus:
        raise ValidationException(
            "Le nombre d'entrées ou de desserts ne correspond pas au nombre de plats commandés dans les menus.")
    reservations_count, reserved_seats  = Reservation.count_places(connection, name, email)
    if (reservations_count or 0) > 10:
        raise ValidationException('Il y a déjà trop de réservations à votre nom')
    if (reserved_seats or 0) + places > 60:
        raise ValidationException('Vous réservez ou avez réservé trop de places')
    _, total_bookings = Reservation.count_places(connection)
    MAX_PLACES = 120
    if (total_bookings or 0) + places > MAX_PLACES:
        max_restantes = MAX_PLACES - (total_bookings or 0)
        raise ValidationException(f"Il n'y a plus assez de place dans la salle, il ne reste plus que {max_restantes} places libres.")
    return (name, email, places, date,
            outside_fondus, outside_assiettes, outside_bolo, outside_scampis, outside_tiramisu, outside_tranches,
            inside_fondus, inside_assiettes, inside_bolo, inside_scampis, inside_tiramisu, inside_tranches,
            gdpr_accepts_use)


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
        places = form.getfirst('places', default=0)
        date = form.getfirst('date', default='')
        outside_fondus = form.getfirst('outside_fondus', default=0)
        outside_assiettes = form.getfirst('outside_assiettes', default=0)
        outside_bolo = form.getfirst('outside_bolo', default=0)
        outside_scampis = form.getfirst('outside_scampis', default=0)
        outside_tiramisu = form.getfirst('outside_tiramisu', default=0)
        outside_tranches = form.getfirst('outside_tranches', default=0)
        inside_fondus = form.getfirst('inside_fondus', default=0)
        inside_assiettes = form.getfirst('inside_assiettes', default=0)
        inside_bolo = form.getfirst('inside_bolo', default=0)
        inside_scampis = form.getfirst('inside_scampis', default=0)
        inside_tiramisu = form.getfirst('inside_tiramisu', default=0)
        inside_tranches = form.getfirst('inside_tranches', default=0)
        gdpr_accepts_use = form.getfirst('gdpr_accepts_use', default=False)
        try:
            (name, email, places, date,
             outside_fondus, outside_assiettes, outside_bolo, outside_scampis, outside_tiramisu, outside_tranches,
             inside_fondus, inside_assiettes, inside_bolo, inside_scampis, inside_tiramisu, inside_tranches,
             gdpr_accepts_use) = validate_data(
                 name, email, places, date,
                 outside_fondus, outside_assiettes, outside_bolo, outside_scampis, outside_tiramisu, outside_tranches,
                 inside_fondus, inside_assiettes, inside_bolo, inside_scampis, inside_tiramisu, inside_tranches,
                 gdpr_accepts_use, db_connection)
        except ValidationException as e:
            respond_with_validation_error(form, e, CONFIGURATION)
        else:
            respond_with_reservation_confirmation(
                name,
                email,
                places,
                date,
                outside_fondus,
                outside_assiettes,
                outside_bolo,
                outside_scampis,
                outside_tiramisu,
                outside_tranches,
                inside_fondus,
                inside_assiettes,
                inside_bolo,
                inside_scampis,
                inside_tiramisu,
                inside_tranches,
                gdpr_accepts_use,
                db_connection,
                CONFIGURATION)
    except Exception:
        # cgitb needs the content-type header
        if print_content_type('text/html; charset=utf-8'):
            print('Content-Language: en')
            print()
        raise
