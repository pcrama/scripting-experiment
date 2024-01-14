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
    redirect_to_event,
    respond_html,
)
from storage import (
    Csrf,
    Reservation,
    create_db,
)
from create_tickets import (
    create_full_ticket_list,
    ul_for_menu_data,
)


def fail_generate_tickets():
    redirect_to_event()


def get_method(db_connection, configuration, user, ip):
    csrf_token = Csrf.get_by_user_and_ip(db_connection, user, ip)
    (groups,
     total_main_starter,
     total_extra_starter,
     total_bolo,
     total_extra_dish,
     total_kids_bolo,
     total_kids_extra_dish,
     total_dessert) = Reservation.count_menu_data(db_connection)
    respond_html(html_document(
        'Impression des tickets pour la nourriture',
        (('p', 'Il y a ', pluriel_naif(groups, 'réservation'), ':'),
         ul_for_menu_data(total_main_starter=total_main_starter,
                          total_extra_starter=total_extra_starter,
                          total_bolo=total_bolo,
                          total_extra_dish=total_extra_dish,
                          total_kids_bolo=total_kids_bolo,
                          total_kids_extra_dish=total_kids_extra_dish,
                          total_dessert=total_dessert),
         (('form', 'method', 'POST'),
          (('input', 'type', 'hidden', 'id', 'csrf_token', 'name', 'csrf_token', 'value', csrf_token.token),),
          (('label', 'for', 'main_starter'), configuration['main_starter_name'], ':'),
          (('input', 'type', 'number', 'id', 'main_starter', 'name', 'main_starter', 'value', str(total_main_starter), 'min', str(total_main_starter), 'max', '200'), ),
          ('br',),
          (('label', 'for', 'extra_starter'), configuration['extra_starter_name'], ':'),
          (('input', 'type', 'number', 'id', 'extra_starter', 'name', 'extra_starter', 'value', str(total_extra_starter), 'min', str(total_extra_starter), 'max', '200'), ),
          ('br',),
          (('label', 'for', 'bolo'), configuration['bolo_name'], ':'),
          (('input', 'type', 'number', 'id', 'bolo', 'name', 'bolo', 'value', str(total_bolo), 'min', str(total_bolo), 'max', '200'), ),
          ('br',),
          (('label', 'for', 'extra_dish'), configuration['extra_dish_name'], ':'),
          (('input', 'type', 'number', 'id', 'extra_dish', 'name', 'extra_dish', 'value', str(total_extra_dish), 'min', str(total_extra_dish), 'max', '200'), ),
          ('br',),
          (('label', 'for', 'kids_bolo'), configuration['kids_bolo_name'], ':'),
          (('input', 'type', 'number', 'id', 'kids_bolo', 'name', 'kids_bolo', 'value', str(total_kids_bolo), 'min', str(total_kids_bolo), 'max', '200'), ),
          ('br',),
          (('label', 'for', 'kids_extra_dish'), configuration['kids_extra_dish_name'], ':'),
          (('input', 'type', 'number', 'id', 'kids_extra_dish', 'name', 'kids_extra_dish', 'value', str(total_kids_extra_dish), 'min', str(total_kids_extra_dish), 'max', '200'), ),
          ('br',),
          (('label', 'for', 'dessert'), configuration['dessert_name'], ':'),
          (('input', 'type', 'number', 'id', 'dessert', 'name', 'dessert', 'value', str(total_dessert), 'min', str(total_dessert), 'max', '200'), ),
          ('br',),
          (('input', 'type', 'submit', 'value', 'Générer les tickets pour impression'),)))))


def post_method(db_connection, user, ip):
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
            Csrf.validate_and_update(db_connection, csrf_token, user, ip)
        except KeyError:
            fail_generate_tickets()

    extra_starter = safe_non_negative_int_less_or_equal_than_500(form.getfirst('extra_starter', default=0))
    main_starter = safe_non_negative_int_less_or_equal_than_500(form.getfirst('main_starter', default=0))
    bolo = safe_non_negative_int_less_or_equal_than_500(form.getfirst('bolo', default=0))
    extra_dish = safe_non_negative_int_less_or_equal_than_500(form.getfirst('extra_dish', default=0))
    kids_bolo = safe_non_negative_int_less_or_equal_than_500(form.getfirst('kids_bolo', default=0))
    kids_extra_dish = safe_non_negative_int_less_or_equal_than_500(form.getfirst('kids_extra_dish', default=0))
    dessert = safe_non_negative_int_less_or_equal_than_500(form.getfirst('dessert', default=0))

    if print_content_type('text/html; charset=utf-8'):
        print('Content-Language: en')
        print()

    respond_html(html_document(
        'Liste des tickets à imprimer',
        create_full_ticket_list(
            db_connection,
            Reservation.select(
                db_connection,
                filtering=[('active', True)],
                order_columns=['date', 'name', 'email']),
            extra_starter=extra_starter,
            main_starter=main_starter,
            bolo=bolo,
            extra_dish=extra_dish,
            kids_bolo=kids_bolo,
            kids_extra_dish=kids_extra_dish,
            dessert=dessert),
        with_banner=False))


if __name__ == '__main__':
    try:
        remote_user = os.getenv('REMOTE_USER')
        remote_addr = os.getenv('REMOTE_ADDR')
        if remote_user is None or remote_addr is None:
            fail_generate_tickets()

        CONFIGURATION = config.get_configuration()

        cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

        db_connection = create_db(CONFIGURATION)

        if os.getenv('REQUEST_METHOD') == 'GET':
            get_method(db_connection, CONFIGURATION, remote_user, remote_addr)
        elif os.getenv('REQUEST_METHOD') == 'POST':
            post_method(db_connection, remote_user, remote_addr)
        else:
            fail_generate_tickets()
    except Exception:
        if print_content_type('text/html; charset=utf-8'):
            print('Content-Language: en')
            print()
        raise
