#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
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
    redirect,
    respond_html,
)
from storage import (
    Csrf,
    Reservation,
    create_db,
    ensure_connection,
)
from lib_post_reservation import(
    compute_price,
    normalize_data,
    respond_with_reservation_confirmation,
    respond_with_reservation_failed,
    save_data_sqlite3
)


def fail_add_unchecked_reservation():
    redirect('https://www.srhbraine.be/concert-de-gala-2022/')


if __name__ == '__main__':
    if os.getenv('REQUEST_METHOD') != 'POST' or os.getenv('REMOTE_USER') is None:
        fail_add_unchecked_reservation()
    CONFIGURATION = config.get_configuration()

    cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

    try:
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
        comment = form.getfirst('comment', default='')
        date = form.getfirst('date', default='')
        paying_seats = form.getfirst('paying_seats', default=0)
        free_seats = form.getfirst('free_seats', default=0)
        # Abuse 'email' field to store 'comment'
        (name, comment, date, paying_seats, free_seats, gdpr_accepts_use) = normalize_data(
            name,
            comment,
            date,
            paying_seats,
            free_seats,
            # there is no email address or they would have registered
            # themselves -> No GDPR
            False)
        respond_with_reservation_confirmation(
            name,
            comment,
            date,
            paying_seats,
            free_seats,
            gdpr_accepts_use,
            db_connection,
            CONFIGURATION,
            origin=os.getenv('REMOTE_USER'))
    except Exception:
        # cgitb needs the content-type header
        if print_content_type('text/html; charset=utf-8'):
            print('Content-Language: en')
            print()
        raise
