#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
#
# Test with
#
# (cd app/gestion && env REQUEST_METHOD=GET REMOTE_USER=secretaire REMOTE_ADDR=1.2.3.4 SERVER_NAME=localhost SCRIPT_NAME=list_reservations.cgi python list_reservations.cgi)

import cgi
import cgitb
import glob
import itertools
import os
import sys
import time
import urllib.parse

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
    ul_for_menu_data,
)


def update_sort_order(new_col_name, sort_order):
    if sort_order:
        if new_col_name.upper() == sort_order[0]:
            return sort_order[1:]
        elif new_col_name.lower() == sort_order[0]:
            return [new_col_name.upper(), *(x for x in sort_order if x.lower() != new_col_name.lower())]
        else:
            return [new_col_name.lower(), *(x for x in sort_order if x.lower() != new_col_name.lower())]
    else:
        return [new_col_name]


def make_url(sort_order, limit, offset, base_url=None, environ=None):
    if base_url is None:
        environ = environ or os.environ
        base_url = urllib.parse.urljoin(f'https://{environ["SERVER_NAME"]}', environ["SCRIPT_NAME"])
    params = list((k, v) for k, v in itertools.chain(
        (('limit', limit),
         ('offset', offset)),
        (('sort_order', s) for s in sort_order))
                  if v is not None)
    split_result = urllib.parse.urlsplit(base_url)
    return urllib.parse.urlunsplit((
        split_result.scheme,
        split_result.netloc,
        split_result.path,
        urllib.parse.urlencode(params),
        split_result.fragment))


def make_navigation_a_elt(sort_order, limit, offset, text):
    return (('a',
             'class', 'navigation',
             'href', make_url(sort_order, limit, offset)),
            text)


def get_first(d, k):
    return d.get(k, [None])[0]


def sort_direction(col, sort_order):
    col = col.lower()
    if sort_order and sort_order[0].lower() == col:
        return ' ⬇' if sort_order[0].isupper() else ' ⬆'
    try:
        sort_col = next(x for x in sort_order if x.lower() == col)
        return ' ↓' if sort_col[0].isupper() else ' ↑'
    except StopIteration:
        return ''


DEFAULT_LIMIT = 20
MAX_LIMIT = 500

if __name__ == '__main__':
    if os.getenv('REQUEST_METHOD') != 'GET' or any(
            os.getenv(p) is None for p in (
                'REMOTE_USER', 'REMOTE_ADDR', 'SERVER_NAME', 'SCRIPT_NAME')):
        redirect_to_event()

    CONFIGURATION = config.get_configuration()
    cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

    MAIN_STARTER_SHORT = CONFIGURATION["main_starter_short"]
    EXTRA_STARTER_SHORT = CONFIGURATION["extra_starter_short"]
    BOLO_SHORT = CONFIGURATION["bolo_short"]
    EXTRA_DISH_SHORT = CONFIGURATION["extra_dish_short"]
    KIDS_BOLO_SHORT = CONFIGURATION["kids_bolo_short"]
    KIDS_EXTRA_DISH_SHORT = CONFIGURATION["kids_extra_dish_short"]
    DESSERT_SHORT = CONFIGURATION["dessert_short"]

    try:
        # NB: the latter branch of the `or' is for automated testing purposes only...
        JS_FILES = glob.glob("../*.js") or glob.glob("../../input-form/build/*.js")
        params = cgi.parse()
        sort_order = params.get('sort_order', '')
        try:
            limit = min(int(get_first(params, 'limit') or DEFAULT_LIMIT), MAX_LIMIT)
        except Exception:
            limit = DEFAULT_LIMIT
        try:
            offset = max(int(get_first(params, 'offset')), 0)
        except Exception:
            offset = 0
        connection = create_db(CONFIGURATION)
        csrf_token = Csrf.get_by_user_and_ip(
            connection, os.getenv('REMOTE_USER'), os.getenv('REMOTE_ADDR'))

        COLUMNS = [('name', 'Nom'), ('email', 'Email'), ('extra_comment', 'Commentaire'),
                   ('places', 'Places'),
                   ('main_starter', MAIN_STARTER_SHORT), ('extra_starter', EXTRA_STARTER_SHORT),
                   ('bolo', BOLO_SHORT), ('extra_dish', EXTRA_DISH_SHORT),
                   ('kids_bolo', KIDS_BOLO_SHORT), ('kids_extra_dish', KIDS_EXTRA_DISH_SHORT),
                   ('dessert', DESSERT_SHORT),
                   ('origin', 'Origine'), ('date', 'Date'),
                   ('time', 'Réservé le')]
        table_header_row = tuple(
            ('th', make_navigation_a_elt(update_sort_order(column, sort_order), limit, offset,
                                         header + sort_direction(column, sort_order)))
            for column, header in COLUMNS)
        total_bookings = Reservation.length(connection)
        (active_reservations,
         total_main_starter,
         total_extra_starter,
         total_bolo,
         total_extra_dish,
         total_kids_bolo,
         total_kids_extra_dish,
         total_dessert) = Reservation.count_menu_data(connection)
        reservation_summary = Reservation.summary_by_date(connection)
        pagination_links = tuple((
            x for x in
            [('li', make_navigation_a_elt(sort_order, limit, 0, 'Début'))
             if offset > 0
             else None,
             ('li',
              make_navigation_a_elt(sort_order, limit, offset - limit, 'Précédent'))
             if offset > limit else
             None,
             ('li',
              make_navigation_a_elt(sort_order, limit, offset + limit, 'Suivant'))
             if offset + limit < active_reservations else
             None]
            if x is not None))
        respond_html(html_document(
            'List of reservations',
            (*((('p',
                 'Il y a ', pluriel_naif(total_bookings, 'bulle'), ' en tout dont ',
                 pluriel_naif(active_reservations, ['est active', 'sont actives']),
                 '.'),
                ul_for_menu_data(total_main_starter, total_extra_starter,
                                 total_bolo, total_extra_dish,
                                 total_kids_bolo, total_kids_extra_dish,
                                 total_dessert)
                if sum((total_main_starter, total_extra_starter,
                        total_bolo, total_extra_dish,
                        total_kids_bolo, total_kids_extra_dish,
                        total_dessert)
                       ) > 0
                else '')
               if total_bookings > 0
               else []),
             ('ul', *tuple(('li', row[0], ': ',
                            pluriel_naif(row[1], ['place réservée', 'places réservées']))
                           for row in reservation_summary))
             if total_bookings > 0
             else '',
             (('form', 'action', os.getenv('SCRIPT_NAME')),
              (('label', 'for', 'limit'), 'Limiter le tableau à ', ('em', 'n'), ' lignes:'),
              (('input', 'id', 'limit', 'type', 'number', 'name', 'limit', 'min', '5', 'value', str(limit), 'max', '10000'),),
              (('input', 'type', 'submit', 'value', 'Rafraichir la page'),),
              *((('input', 'id', 'sort_order', 'name', 'sort_order', 'type', 'hidden', 'value', v),)
                for v in sort_order),
              (('input', 'id', 'offset', 'name', 'offset', 'type', 'hidden', 'value', str(offset)),)),
             (('ul', 'class', 'navbar'), *pagination_links) if pagination_links else '',
             (('table', 'class', 'list'),
              ('tr', *table_header_row),
              *tuple(('tr',
                      ('td', r.name),
                      ('td', r.email),
                      ('td', r.extra_comment),
                      ('td', r.places),
                      ('td', r.outside_main_starter + r.inside_main_starter),
                      ('td', r.outside_extra_starter + r.inside_extra_starter),
                      ('td', r.outside_bolo + r.inside_bolo),
                      ('td', r.outside_extra_dish + r.inside_extra_dish),
                      ('td', r.kids_bolo),
                      ('td', r.kids_extra_dish),
                      ('td', r.outside_dessert + r.inside_dessert + r.kids_dessert),
                      ('td', r.origin if r.origin else (('span', 'class', 'null_value'),
                                                        'formulaire web')),
                      ('td', r.date),
                      ('td', time.strftime('%d/%m/%Y %H:%M', time.gmtime(r.timestamp))))
                     for r in Reservation.select(connection,
                                                 filtering=[('active', '1')],
                                                 order_columns=sort_order,
                                                 limit=limit,
                                                 offset=offset))),
             ('hr',),
             ('p',
              # name is a fake parameter to encourage clients to believe Excel
              # can really open it.
              (('a', 'href', 'export_csv.cgi?name=export.csv'),
                    'Exporter en format CSV (Excel ou autres tableurs)'),
              '. Excel a du mal avec les accents et autres caractères spéciaux, voyez ',
              (('a', 'href', 'https://www.nextofwindows.com/how-to-display-csv-files-with-unicode-utf-8-encoding-in-excel'),
               'cette page'),
              " pour plus d'explications."),
             ('hr',),
             ('p', 'Ajouter une réservation:'),
             (('div', 'id', 'elmish-app'), ''),
             ('script',
              'const ACTION_DEST = "add_unchecked_reservation.cgi";',
              'const CONCERT_DATE = "2023-03-25";',
              'const CSRF_TOKEN = "', csrf_token.token, '";'),
             *((('script', 'defer src', js),) for js in JS_FILES),
             ('hr',),
             (('a', 'href', 'generate_tickets.cgi'), 'Générer les tickets nourriture pour impression'))))
    except Exception:
        if print_content_type('text/html; charset=utf-8'):
            print()
        cgitb.handler()
