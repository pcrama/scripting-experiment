#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
#
# Test with
#
# echo | (cd app && env REQUEST_METHOD=POST 'QUERY_STRING=name=bambi&email=a@b.com' python post_reservation.cgi)
import cgi
import cgitb
import os
import re
import sys

import config
from htmlgen import (
    html_document,
    print_content_type,
    redirect_to_event,
    respond_html,
)
from storage import(
    create_db,
)
from lib_post_reservation import(
    ValidationException,
    normalize_data,
    respond_with_reservation_confirmation,
    respond_with_reservation_failed,
    respond_with_reservations_closed,
    save_data_sqlite3,
    validate_data,
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
        if CONFIGURATION.get('disabled', False):
            respond_with_reservations_closed()
            sys.exit(0)

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
