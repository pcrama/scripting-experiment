#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
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
    cents_to_euro,
    html_document,
    print_content_type,
    redirect,
    respond_html,
)
from storage import (
    Csrf,
    Reservation,
    create_db,
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


def pluriel_naif(x, c):
    return x if c == 1 else f'{x}s'


DEFAULT_LIMIT = 20
MAX_LIMIT = 500

if __name__ == '__main__':
    if os.getenv('REQUEST_METHOD') != 'GET' or os.getenv('REMOTE_USER') is None:
        redirect('https://www.srhbraine.be/concert-de-gala-2022/')

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
                   ('paying_seats', 'Payant'), ('free_seats', 'Gratuit'),
                   ('bank_id', 'Communication'), ('origin', 'Origine'),
                   ('time', 'Réservé le')]
        table_header_row = tuple(
            ('th', make_navigation_a_elt(update_sort_order(column, sort_order), limit, offset,
                                         header + sort_direction(column, sort_order)))
            for column, header in COLUMNS)
        total_bookings = Reservation.length(connection)
        active_reservations = Reservation.length(connection, [('active', 1)])
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
            (('p',
              'Il y a ', str(total_bookings), pluriel_naif(' bulle', total_bookings), ' en tout',
              *(' dont ', str(active_reservations), ' ',
                'est active' if active_reservations == 1 else 'sont actives'),
              '.')
             if total_bookings > 0
             else '',
             ('ul', *tuple(('li', row[0], ': ',
                            str(row[1]), pluriel_naif(' place', row[1]), pluriel_naif(' réservée', row[1]))
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
             ('table',
              ('tr', *table_header_row),
              *tuple(('tr',
                      ('td', r.name),
                      ('td', r.email),
                      ('td', r.date),
                      ('td', r.paying_seats),
                      ('td', r.free_seats),
                      ('td', r.bank_id),
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
             (('form', 'method', 'post', 'action', 'add_unchecked_reservation.cgi'),
              (('input', 'type', 'hidden', 'id', 'csrf_token', 'name', 'csrf_token', 'value', csrf_token.token),),
              (('label', 'for', 'name'), 'Nom'),
              (('input', 'id', 'name', 'name', 'name', 'type', 'text', 'placeholder', 'Nom de la bulle', 'required', 'required', 'style', 'width:100%;'),),
              ('br',),
              (('label', 'for', 'comment'), 'Commentaire'),
              (('input', 'id', 'comment', 'name', 'comment', 'type', 'text', 'placeholder', 'Commentaire', 'style', 'width:100%;'),),
              ('br',),
              (('input', 'id', 'samedi', 'name', 'date', 'type', 'radio', 'value', '2022-12-10',
                'checked', 'checked'),),
              (('label', 'for', 'samedi'), 'Samedi 10 décembre 2022 à 20h'),
              ('br',),
              (('input', 'id', 'dimanche', 'name', 'date', 'type', 'radio', 'value', '2022-12-11'),),
              (('label', 'for', 'dimanche'), 'Dimanche 11 décembre 2022 à 15h'),
              ('br',),
              (('label', 'for', 'paying_seats'), 'Places payantes:'),
              (('input', 'id', 'paying_seats', 'name', 'paying_seats', 'type', 'number', 'min', '0', 'value', '1'),),
              ('br',),
              (('label', 'for', 'free_seats'), 'Places gratuites:'),
              (('input', 'id', 'free_seats', 'name', 'free_seats', 'type', 'number', 'min', '0', 'value', '0'),),
              ('br',),
              (('input', 'type', 'submit', 'value', 'Confirmer'),)))))
    except Exception:
        if print_content_type('text/html; charset=utf-8'):
            print()
        cgitb.handler()
