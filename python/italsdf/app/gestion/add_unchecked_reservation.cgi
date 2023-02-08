#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
#
# After finding a way to make the CSRF check allow the script to proceed, test with
#
# echo | (script_name=add_unchecked_reservation.cgi && env SERVER_NAME=1.2.3.4 SCRIPT_NAME=$script_name REMOTE_USER=admin REQUEST_METHOD=POST 'QUERY_STRING=name=Qui+m%27appelle%3F&extraComment=02%2F123.45.67&places=1&insidemainstarter=1&insideextrastarter=0&insidebolo=0&insideextradish=1&bolokids=0&extradishkids=0&outsidemainstarter=0&outsideextrastarter=0&outsidebolo=0&outsideextradish=0&outsidedessert=0&csrf_token=e0eb75317b2d4084b0aa3594a8545375&date=2023-03-25' python3 $script_name)
import cgi
import cgitb
import os
import sys
import time
import uuid

# hack to get at my utilities:
sys.path.append('..')

import config
from htmlgen import (
    html_document,
    print_content_type,
    redirect_to_event,
    respond_html,
)
from storage import (
    Csrf,
    Reservation,
    create_db,
    ensure_connection,
)
from lib_post_reservation import(
    normalize_data,
    respond_with_reservation_confirmation,
    respond_with_reservation_failed,
    respond_with_reservations_closed,
    save_data_sqlite3
)


def fail_add_unchecked_reservation():
    redirect_to_event()


if __name__ == '__main__':
    if os.getenv('REQUEST_METHOD') != 'POST' or os.getenv('REMOTE_USER') is None:
        fail_add_unchecked_reservation()
    CONFIGURATION = config.get_configuration()

    cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

    try:
        if CONFIGURATION.get('disabled', False):
            respond_with_reservations_closed()
            sys.exit(0)

        db_connection = create_db(CONFIGURATION)

        # Get form data
        form = cgi.FieldStorage()
        csrf_token = form.getfirst('csrf_token')
        if csrf_token is None:
            fail_add_unchecked_reservation()
        else:
            try:
                Csrf.get(db_connection, csrf_token)
            except KeyError:
                fail_add_unchecked_reservation()

        name = form.getfirst('name', default='')
        email = ''
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
        (name, email, extra_comment, places, date,
         outside_main_starter, outside_extra_starter, outside_bolo, outside_extra_dish, outside_dessert,
         inside_main_starter, inside_extra_starter, inside_bolo, inside_extra_dish,
         kids_bolo, kids_extra_dish,
         gdpr_accepts_use) = normalize_data(
             name=name,
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
             gdpr_accepts_use=gdpr_accepts_use)
        respond_with_reservation_confirmation(
            name=name,
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
            connection=db_connection,
            configuration=CONFIGURATION,
            origin=os.getenv('REMOTE_USER'))
    except Exception:
        # cgitb needs the content-type header
        if print_content_type('text/html; charset=utf-8'):
            print('Content-Language: en')
            print()
        raise
