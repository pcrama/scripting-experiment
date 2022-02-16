#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import os
import sys

# hack to get at my utilities:
sys.path.append('..')
import config
from htmlgen import (
    html_document,
    pluriel_naif,
    print_content_type,
    redirect,
    respond_html,
)
from storage import(
    Csrf,
    Reservation,
    create_db,
)
from create_tickets import(
    create_full_ticket_list,
)


CONCERT_PAGE = 'https://www.srhbraine.be/soiree-italienne-2022/'


def fail_generate_tickets():
    redirect('https://www.srhbraine.be/soiree-italienne-2022/')


def get_method(db_connection):
    csrf_token = Csrf.get_by_user_and_ip(
        db_connection, os.getenv('REMOTE_USER'), os.getenv('REMOTE_ADDR'))
    (groups,
     total_fondus,
     total_assiettes,
     total_bolo,
     total_scampis,
     total_pannacotta,
     total_tranches) = Reservation.count_menu_data(db_connection)
    respond_html(html_document(
        'Impression des tickets pour la nourriture',
        (('p', 'Il y a ', pluriel_naif(groups, 'réservation'), ':'),
         ('ul',
          ('li', str(total_fondus), ' fondus'),
          ('li', str(total_assiettes), ' assiettes'),
          ('li', pluriel_naif(total_bolo, 'bolo')),
          ('li', str(total_scampis), ' scampis'),
          ('li', pluriel_naif(total_pannacotta, 'pannacotta')),
          ('li', str(total_tranches,), ' tranches napolitaines')),
         (('form', 'method', 'POST'),
          (('input', 'type', 'hidden', 'id', 'csrf_token', 'name', 'csrf_token', 'value', csrf_token.token),),
          (('label', 'for', 'fondus'), 'fondus:'),
          (('input', 'type', 'number', 'id', 'fondus', 'name', 'fondus', 'value', str(total_fondus), 'min', str(total_fondus), 'max', '200'), ),
          ('br',),
          (('label', 'for', 'assiettes'), 'assiettes:'),
          (('input', 'type', 'number', 'id', 'assiettes', 'name', 'assiettes', 'value', str(total_assiettes), 'min', str(total_assiettes), 'max', '200'), ),
          ('br',),
          (('label', 'for', 'bolo'), 'bolo:'),
          (('input', 'type', 'number', 'id', 'bolo', 'name', 'bolo', 'value', str(total_bolo), 'min', str(total_bolo), 'max', '200'), ),
          ('br',),
          (('label', 'for', 'scampis'), 'scampis:'),
          (('input', 'type', 'number', 'id', 'scampis', 'name', 'scampis', 'value', str(total_scampis), 'min', str(total_scampis), 'max', '200'), ),
          ('br',),
          (('label', 'for', 'pannacotta'), 'pannacotta:'),
          (('input', 'type', 'number', 'id', 'pannacotta', 'name', 'pannacotta', 'value', str(total_pannacotta), 'min', str(total_pannacotta), 'max', '200'), ),
          ('br',),
          (('label', 'for', 'tranches'), 'tranches:'),
          (('input', 'type', 'number', 'id', 'tranches', 'name', 'tranches', 'value', str(total_tranches), 'min', str(total_tranches), 'max', '200'), ),
          ('br',),
          (('input', 'type', 'submit', 'value', 'Générer les tickets pour impression'),)))))


def post_method(db_connection):
    def safe_non_negative_int_less_or_equal_than_500(x):
        try:
            x = int(x)
            return max(0, min(x, 500))
        except Exception:
            return 0

    # Get form data
    form = cgi.FieldStorage()
    csrf_token = form.getfirst('csrf_token')
    if csrf_token is None:
        fail_generate_tickets()
    else:
        try:
            Csrf.get(db_connection, csrf_token)
        except KeyError:
            fail_generate_tickets()

    fondus = safe_non_negative_int_less_or_equal_than_500(form.getfirst('fondus', default=0))
    assiettes = safe_non_negative_int_less_or_equal_than_500(form.getfirst('assiettes', default=0))
    bolo = safe_non_negative_int_less_or_equal_than_500(form.getfirst('bolo', default=0))
    scampis = safe_non_negative_int_less_or_equal_than_500(form.getfirst('scampis', default=0))
    pannacotta = safe_non_negative_int_less_or_equal_than_500(form.getfirst('pannacotta', default=0))
    tranches = safe_non_negative_int_less_or_equal_than_500(form.getfirst('tranches', default=0))

    if print_content_type('text/html; charset=utf-8'):
        print('Content-Language: en')
        print()

    respond_html(html_document(
        'Liste des tickets à imprimer',
        create_full_ticket_list(
            Reservation.select(
                db_connection,
                filtering=[('active', True)],
                order_columns=['date', 'name', 'email']),
            fondus, assiettes, bolo, scampis, pannacotta, tranches)))

    
if __name__ == '__main__':
    try:
        # if os.getenv('REMOTE_USER') is None or os.getenv('REMOTE_ADDR') is None:
        #     fail_generate_tickets()

        CONFIGURATION = config.get_configuration()

        cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

        db_connection = create_db(CONFIGURATION)

        if os.getenv('REQUEST_METHOD') == 'GET':
            get_method(db_connection)
        elif os.getenv('REQUEST_METHOD') == 'POST':
            post_method(db_connection)
        else:
            fail_generate_tickets()
    except Exception:
        if print_content_type('text/html; charset=utf-8'):
            print('Content-Language: en')
            print()
        raise
