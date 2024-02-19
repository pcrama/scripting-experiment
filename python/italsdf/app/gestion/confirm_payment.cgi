#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
#
# Test with
#
# (cd app/gestion && env REQUEST_METHOD=GET REMOTE_USER=secretaire REMOTE_ADDR=1.2.3.4 SERVER_NAME=localhost SCRIPT_NAME=confirm_payment.cgi QUERY_STRING=uuid_hex=395e7b845afb4a71876360e0655138a7&src_id=2024-00071 python3 confirm_payment.cgi)

import cgi
import cgitb
import os
import sys
import time

# hack to get at my utilities:
sys.path.append('..')
import config
from htmlgen import (
    print_content_type,
    redirect_to_event,
    respond_html,
)
from storage import (
    Payment,
    Reservation,
    create_db,
)
from lib_payment_confirmation import handle_post, html_document_with_mail_template

if __name__ == '__main__':
    REMOTE_USER, REMOTE_ADDR, SERVER_NAME, SCRIPT_NAME = (os.getenv(p) for p in ('REMOTE_USER', 'REMOTE_ADDR', 'SERVER_NAME', 'SCRIPT_NAME'))
    if os.getenv('REQUEST_METHOD') not in ('GET', 'POST') or not all(
            (REMOTE_USER, REMOTE_ADDR, SERVER_NAME, SCRIPT_NAME)):
        redirect_to_event()
    assert REMOTE_USER
    assert REMOTE_ADDR
    assert SERVER_NAME
    assert SCRIPT_NAME

    CONFIGURATION = config.get_configuration()
    cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

    try:
        params = cgi.parse()
        connection = create_db(CONFIGURATION)
        form = cgi.FieldStorage()
        if os.getenv('REQUEST_METHOD') == 'POST':
            token = form.getfirst('csrf_token', default='')
            if not token:
                redirect_to_event()
                assert token
            payment = Payment.find_by_src_id(connection, form.getfirst('src_id', default=''))
            if not payment:
                redirect_to_event()
                assert payment is not None
            handle_post(
                connection,
                payment,
                token,
                time.time(),
                SERVER_NAME,
                SCRIPT_NAME,
                REMOTE_USER,
                REMOTE_ADDR,
            )
        else:
            reservation = Reservation.find_by_uuid(connection, form.getfirst('uuid_hex', default=''))
            if not reservation:
                redirect_to_event()
                assert reservation is not None
            payment = Payment.find_by_src_id(connection, form.getfirst('src_id', default=''))
            if not payment:
                redirect_to_event()
                assert payment is not None

            response = html_document_with_mail_template(
                connection,
                reservation,
                payment,
                CONFIGURATION,
                SERVER_NAME,
                SCRIPT_NAME,
                REMOTE_USER,
                REMOTE_ADDR)
            respond_html(response)
    except Exception:
        if print_content_type('text/html; charset=utf-8'):
            print()
        cgitb.handler()
