#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
#
# Test with
#
# echo | (cd app && script_name=post_reservation.cgi && env REQUEST_METHOD=POST 'QUERY_STRING=name=test&email=i%40example.com&extraComment=commentaire&places=1&insidemainstarter=2&insideextrastarter=1&insidebolo=0&insideextradish=3&bolokids=1&extradishkids=3&outsidemainstarter=9&outsideextrastarter=5&outsidebolo=6&outsideextradish=7&outsidedessert=8&gdpr_accepts_use=true&date=2099-01-01' SERVER_NAME=example.com SCRIPT_NAME=$script_name python3 $script_name)
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
- ou_outsidemainstarter
- ou_outsideextrastarter
- ou_outsidebolo
- ou_outsideextradish
- ou_outsidedessert
- in_insidemainstarter
- in_insideextrastarter
- in_insidebolo
- in_insideextradish
- kd_kidsbolo
- kd_kidsextradish
- gdpr_accepts_use
- uuid
- time
- active
- origin

Save:
- name
- email
- date
- outside_main_starter
- outside_extra_starter
- outside_bolo
- outside_extra_dish
- outside_dessert
- inside_main_starter
- inside_extra_starter
- inside_bolo
- inside_extra_dish
- kids_bolo
- kids_extra_dish
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
        extra_comment = form.getfirst('extraComment', default='')
        places = form.getfirst('places', default=0)
        date = form.getfirst('date', default='')
        outside_main_starter = form.getfirst('outsidemainstarter', default=0)
        outside_extra_starter = form.getfirst('outsideextrastarter', default=0)
        outside_bolo = form.getfirst('outsidebolo', default=0)
        outside_extra_dish = form.getfirst('outsideextradish', default=0)
        outside_dessert = form.getfirst('outsidedessert', default=0)
        inside_main_starter = form.getfirst('insidemainstarter', default=0)
        inside_extra_starter = form.getfirst('insideextrastarter', default=0)
        inside_bolo = form.getfirst('insidebolo', default=0)
        inside_extra_dish = form.getfirst('insideextradish', default=0)
        kids_bolo = form.getfirst('bolokids', default=0)
        kids_extra_dish = form.getfirst('extradishkids', default=0)
        gdpr_accepts_use = form.getfirst('gdpr_accepts_use', default=False)
        try:
            (name, email, extra_comment, places, date,
             outside_main_starter, outside_extra_starter, outside_bolo, outside_extra_dish, outside_dessert,
             inside_main_starter, inside_extra_starter, inside_bolo, inside_extra_dish,
             kids_bolo, kids_extra_dish,
             gdpr_accepts_use) = validate_data(
                 name, email, extra_comment, places, date,
                 outside_main_starter, outside_extra_starter, outside_bolo, outside_extra_dish, outside_dessert,
                 inside_main_starter, inside_extra_starter, inside_bolo, inside_extra_dish,
                 kids_bolo, kids_extra_dish,
                 gdpr_accepts_use, db_connection)
        except ValidationException as e:
            respond_with_validation_error(form, e, CONFIGURATION)
        else:
            respond_with_reservation_confirmation(
                name,
                email,
                extra_comment,
                places,
                date,
                outside_main_starter,
                outside_extra_starter,
                outside_bolo,
                outside_extra_dish,
                outside_dessert,
                inside_main_starter,
                inside_extra_starter,
                inside_bolo,
                inside_extra_dish,
                kids_bolo,
                kids_extra_dish,
                gdpr_accepts_use,
                db_connection,
                CONFIGURATION)
    except Exception:
        # cgitb needs the content-type header
        if print_content_type('text/html; charset=utf-8'):
            print('Content-Language: en')
            print()
        raise
