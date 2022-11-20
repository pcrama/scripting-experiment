#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
#
# Test with
#
# (cd app/gestion && env REQUEST_METHOD=GET REMOTE_USER=secretaire REMOTE_ADDR=1.2.3.4 SERVER_NAME=localhost SCRIPT_NAME=list_reservations.cgi python list_reservations.cgi)

import cgi
import cgitb
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
        base_url = f'https://{environ["SERVER_NAME"]}{environ["SCRIPT_NAME"]}'
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

    try:
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

        COLUMNS = [('name', 'Nom'), ('email', 'Email'), ('date', 'Date'),
                   ('places', 'Places'),
                   ('fondus', 'Fondus'), ('assiettes', 'Charcuterie'),
                   ('bolo', 'Bolo'), ('scampis', 'Scampis'),
                   ('tiramisu', 'Tiramisu'), ('tranches', 'Napolitaines'),
                   ('origin', 'Origine'),
                   ('time', 'Réservé le')]
        table_header_row = tuple(
            ('th', make_navigation_a_elt(update_sort_order(column, sort_order), limit, offset,
                                         header + sort_direction(column, sort_order)))
            for column, header in COLUMNS)
        total_bookings = Reservation.length(connection)
        (active_reservations,
         total_fondus,
         total_assiettes,
         total_bolo,
         total_scampis,
         total_tiramisu,
         total_tranches) = Reservation.count_menu_data(connection)
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
             if offset + limit < total_bookings else
             None]
            if x is not None))
        respond_html(html_document(
            'List of reservations',
            (*((('p',
                 'Il y a ', pluriel_naif(total_bookings, 'bulle'), ' en tout dont ',
                 pluriel_naif(active_reservations, ['est active', 'sont actives']),
                 '.'),
                ul_for_menu_data(total_fondus, total_assiettes,
                                 total_bolo, total_scampis,
                                 total_tiramisu, total_tranches)
                if total_fondus + total_assiettes + total_bolo + total_scampis + total_tiramisu + total_tranches > 0
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
                      ('td', r.date),
                      ('td', r.places),
                      ('td', r.outside_fondus + r.inside_fondus),
                      ('td', r.outside_assiettes + r.inside_assiettes),
                      ('td', r.outside_bolo + r.inside_bolo),
                      ('td', r.outside_scampis + r.inside_scampis),
                      ('td', r.outside_tiramisu + r.inside_tiramisu),
                      ('td', r.outside_tranches + r.inside_tranches),
                      ('td', r.origin if r.origin else (('span', 'class', 'null_value'),
                                                        'formulaire web')),
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
              'const CONCERT_DATE = "2022-03-19";',
              'const CSRF_TOKEN = "', csrf_token.token, '";'),
             (('script', 'src', '../main.js'), ''),
             ('hr',),
             (('a', 'href', 'generate_tickets.cgi'), 'Générer les tickets nourriture pour impression'))))
    except Exception:
        if print_content_type('text/html; charset=utf-8'):
            print()
        cgitb.handler()
