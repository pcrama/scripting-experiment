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
        # Abuse 'email' field to store 'comment'
        (name, email, places, date,
         outside_fondus, outside_assiettes, outside_bolo, outside_scampis, outside_tiramisu, outside_tranches,
         inside_fondus, inside_assiettes, inside_bolo, inside_scampis, inside_tiramisu, inside_tranches,
         gdpr_accepts_use) = normalize_data(
            name,
            comment,
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
            # there is no email address or they would have registered
            # themselves -> No GDPR
            False)
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
            CONFIGURATION,
            origin=os.getenv('REMOTE_USER'))
    except Exception:
        # cgitb needs the content-type header
        if print_content_type('text/html; charset=utf-8'):
            print('Content-Language: en')
            print()
        raise
