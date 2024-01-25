#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import os
import sys
import time

# hack to get at my utilities:
sys.path.append('..')
import config
from htmlgen import (
    html_document,
    print_content_type,
    redirect,
    redirect_to_event,
    respond_html,
)
from storage import (
    Csrf,
    Payment,
    create_db,
)


def fail_link_payment_and_reservation():
    redirect_to_event()


def respond_error(error_title, error_html, list_payments):
    respond_html(html_document(
        error_title,
        error_html + (('br', ),
                      ('p', (('a', 'href', list_payments),
                             'Retour à la liste des paiements')))))


def post_method(db_connection, server_name, script_name, user, ip):
    list_payments = f"https://{server_name}{os.path.join(os.path.dirname(script_name), 'list_payments.cgi')}"
    # Get form data
    form = cgi.FieldStorage()
    csrf_token = form.getfirst('csrf_token')
    if csrf_token is None:
        fail_link_payment_and_reservation()
    else:
        try:
            Csrf.validate_and_update(db_connection, csrf_token, user, ip)
        except KeyError:
            fail_link_payment_and_reservation()

    reservation_uuid = form.getfirst('reservation_uuid')
    if not reservation_uuid:
        respond_error('Formulaire incomplet', (('p', "Il n'y avait pas de ", ("code", "reservation_uuid"), " dans le formulaire."), ), list_payments)
        return

    src_id = form.getfirst('src_id')
    if not src_id:
        respond_error('Formulaire incomplet', (('p', "Il n'y avait pas de ", ("code", "src_id"), " dans le formulaire."), ), list_payments)
        return

    try:
        payment = Payment.find_by_src_id(db_connection, src_id)
    except Exception as exc:
        respond_error(
            "Erreur de recherche",
            (("p", "Le paiement '", str(src_id), "' n'a pas été retrouvé: ", repr(exc)),),
            list_payments)
        return

    if payment is None:
        respond_error(
            "Paiement inconnu",
            (('p', "Le paiement '", str(src_id), "' n'a pas été retrouvé."),),
            list_payments)
        return

    payment.uuid = reservation_uuid
    payment.timestamp = time.time()
    payment.user = user
    payment.ip = ip

    try:
        with db_connection:
            payment.update(db_connection)
    except Exception as exc:
        respond_error(
            "Erreur d'écriture",
            (("p", "Le paiement '", str(src_id), "' n'a pas pu être mis à jour: ", repr(exc)),),
            list_payments)
        return

    redirect(list_payments)


if __name__ == '__main__':
    try:
        remote_user = os.getenv('REMOTE_USER')
        remote_addr = os.getenv('REMOTE_ADDR')
        if not remote_user or not remote_addr:
            fail_link_payment_and_reservation()

        CONFIGURATION = config.get_configuration()

        cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

        if os.getenv('REQUEST_METHOD') == 'POST':
            server_name = os.getenv('SERVER_NAME')
            script_name = os.getenv('SCRIPT_NAME')
            if server_name and script_name:
                with create_db(CONFIGURATION) as db_connection:
                    post_method(db_connection, server_name, script_name, remote_user, remote_addr)
            else:
                fail_link_payment_and_reservation()
        else:
            fail_link_payment_and_reservation()
    except Exception:
        if print_content_type('text/html; charset=utf-8'):
            print('Content-Language: en')
            print()
        raise
