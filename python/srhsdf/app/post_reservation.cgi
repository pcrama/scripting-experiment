#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
#
# Test with
#
# echo | (cd app && script_name=post_reservation.cgi && env REQUEST_METHOD=POST 'QUERY_STRING=civility=melle&first_name=Jean&last_name=test&email=i%40example.com&paying_seats=3&free_seats=2&gdpr_accepts_use=true&date=2099-01-01' SERVER_NAME=example.com SCRIPT_NAME=$script_name python3 $script_name)
import cgi
import cgitb
import os

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
    validate_data,
    respond_with_reservation_confirmation,
)


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
        civility = form.getfirst('civility', default='')
        first_name = form.getfirst('first_name', default='')
        last_name = form.getfirst('last_name', default='')
        email = form.getfirst('email', default='')
        date = form.getfirst('date', default='')
        paying_seats = form.getfirst('paying_seats', default=0)
        free_seats = form.getfirst('free_seats', default=0)
        gdpr_accepts_use = form.getfirst('gdpr_accepts_use', default=False)

        try:
            (civility, first_name, last_name, email, date, paying_seats, free_seats, gdpr_accepts_use) = validate_data(
                civility, first_name, last_name, email, date, paying_seats, free_seats, gdpr_accepts_use, db_connection)
        except ValidationException as e:
            respond_with_validation_error(form, e, CONFIGURATION)
        else:
            respond_with_reservation_confirmation(
                civility,
                first_name,
                last_name,
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
