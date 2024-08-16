#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
#
# (export SCRIPT_NAME="$PWD/app/gestion/add_unchecked_reservation.cgi"; cd "$(dirname "$SCRIPT_NAME")" && echo | CONFIGURATION_JSON_DIR="$(dirname "$(ls -t /tmp/tmp.*/configuration.json | head -n 1)")" DB_DB="$CONFIGURATION_JSON_DIR/db.db" REQUEST_METHOD=POST REMOTE_USER="$(sqlite3 "$DB_DB" "select user from csrfs limit 1")" REMOTE_ADDR="$(sqlite3 "$DB_DB" "select ip from csrfs limit 1")" QUERY_STRING='csrf_token='"$(sqlite3 "$DB_DB" "select token from csrfs limit 1")"'&name=cmdlinename&comment=fromcmdline&date=2099-01-01&paying_seats=3&free_seats=4' SERVER_NAME=localhost python3 $SCRIPT_NAME)
import cgi
import cgitb
import os
import sys

# hack to get at my utilities:
sys.path.append('..')

import config
from htmlgen import (
    print_content_type,
    redirect_to_event,
)
from storage import (
    Csrf,
    create_db,
)
from lib_post_reservation import(
    normalize_data,
    respond_with_reservation_confirmation,
)


def fail_add_unchecked_reservation():
    redirect_to_event()


if __name__ == '__main__':
    REMOTE_USER, REMOTE_ADDR = (os.getenv(key) for key in ('REMOTE_USER', 'REMOTE_ADDR'))
    if os.getenv('REQUEST_METHOD') != 'POST' or not REMOTE_USER or not REMOTE_ADDR:
        fail_add_unchecked_reservation()
    assert REMOTE_USER
    assert REMOTE_ADDR

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
                Csrf.validate_and_update(db_connection, csrf_token, REMOTE_USER, REMOTE_ADDR)
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
            origin=REMOTE_USER)
    except Exception:
        # cgitb needs the content-type header
        if print_content_type('text/html; charset=utf-8'):
            print('Content-Language: en')
            print()
        raise
