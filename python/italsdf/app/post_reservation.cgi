#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
#
# Test with
#
# echo | (cd app && script_name=post_reservation.cgi && env REQUEST_METHOD=POST 'QUERY_STRING=name=test&email=i%40example.com&extraComment=commentaire&places=1&insidemainstarter=2&insideextrastarter=1&insidemaindish=0&insideextradish=3&kidsmaindish=1&kidsextradish=3&outsidemainstarter=9&outsideextrastarter=5&outsidemaindish=6&outsideextradish=7&outsidedessert=8&gdpr_accepts_use=true&date=2099-01-01' SERVER_NAME=example.com SCRIPT_NAME=$script_name python3 $script_name)
import cgi
import cgitb
import os
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
    respond_with_reservation_confirmation,
    respond_with_reservations_closed,
    validate_data,
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
        outside_main_dish = form.getfirst('outsidemaindish', default=0)
        outside_extra_dish = form.getfirst('outsideextradish', default=0)
        outside_third_dish = form.getfirst('outsidethirddish', default=0)
        outside_main_dessert = form.getfirst('outsidemaindessert', default=0)
        outside_extra_dessert = form.getfirst('outsideextradessert', default=0)
        inside_main_starter = form.getfirst('insidemainstarter', default=0)
        inside_extra_starter = form.getfirst('insideextrastarter', default=0)
        inside_main_dish = form.getfirst('insidemaindish', default=0)
        inside_extra_dish = form.getfirst('insideextradish', default=0)
        inside_third_dish = form.getfirst('insidethirddish', default=0)
        inside_main_dessert = form.getfirst('insidemaindessert', default=0)
        inside_extra_dessert = form.getfirst('insideextradessert', default=0)
        kids_main_dish = form.getfirst('kidsmaindish', default=0)
        kids_extra_dish = 0
        kids_third_dish = 0
        kids_main_dessert = form.getfirst('kidsmaindessert', default=0)
        kids_extra_dessert = form.getfirst('kidsextradessert', default=0)
        gdpr_accepts_use = form.getfirst('gdpr_accepts_use', default=False)
        try:
            (name, email, extra_comment, places, date,
             outside_main_starter, outside_extra_starter, outside_main_dish, outside_extra_dish, outside_third_dish, outside_main_dessert, outside_extra_dessert,
             inside_main_starter, inside_extra_starter, inside_main_dish, inside_extra_dish, inside_third_dish, inside_main_dessert, inside_extra_dessert,
             kids_main_dish, kids_extra_dish, kids_third_dish, kids_main_dessert, kids_extra_dessert,
             gdpr_accepts_use) = validate_data(
                 name, email, extra_comment, places, date,
             outside_main_starter, outside_extra_starter, outside_main_dish, outside_extra_dish, outside_third_dish, outside_main_dessert, outside_extra_dessert,
             inside_main_starter, inside_extra_starter, inside_main_dish, inside_extra_dish, inside_third_dish, inside_main_dessert, inside_extra_dessert,
             kids_main_dish, kids_extra_dish, kids_third_dish, kids_main_dessert, kids_extra_dessert,
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
                outside_main_dish,
                outside_extra_dish,
                outside_third_dish,
                outside_main_dessert,
                outside_extra_dessert,
                inside_main_starter,
                inside_extra_starter,
                inside_main_dish,
                inside_extra_dish,
                inside_third_dish,
                inside_main_dessert,
                inside_extra_dessert,
                kids_main_dish,
                kids_extra_dish,
                kids_third_dish,
                kids_main_dessert,
                kids_extra_dessert,
                gdpr_accepts_use,
                db_connection,
                CONFIGURATION)
    except Exception:
        # cgitb needs the content-type header
        if print_content_type('text/html; charset=utf-8'):
            print('Content-Language: en')
            print()
        raise
