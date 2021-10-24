#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import html
import itertools
import os
import sys

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
    params = '&'.join(f'{k}={v}'
                      for k, v in
                      itertools.chain(
                          (('limit', limit),
                           ('offset', offset)),
                          (('sort_order', s) for s in sort_order))
                      if v is not None)
    if params:
        return f'{base_url}?{params}'
    else:
        return base_url


def get_first(d, k):
    return d.get(k, [None])[0]


def sort_direction(col, sort_order):
    col = col.lower()
    try:
        sort_col = next(x for x in sort_order if x.lower() == col)
        return ' ↓' if sort_col[0].isupper() else ' ↑'
    except StopIteration:
        return ''


if __name__ == '__main__':
    if os.getenv('REQUEST_METHOD') != 'GET':
        redirect('https://www.srhbraine.be/concert-de-gala-2021/')

    CONFIGURATION = config.get_configuration()
    cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

    try:
        params = cgi.parse()
        sort_order = params.get('sort_order', '')
        try:
            limit = max(int(get_first(params, 'limit')), 5)
        except Exception:
            limit = 5
        try:
            offset = max(int(get_first(params, 'offset')), 0)
        except Exception:
            offset = 0
        connection = create_db(CONFIGURATION)
        csrf_token = Csrf.get_by_user_and_ip(
            connection, os.getenv('REMOTE_USER'), os.getenv('REMOTE_ADDR'))

        COLUMNS = [('name', 'Nom'), ('email', 'Email'), ('date', 'Date'),
                   ('paying_seats', 'Payant'), ('free_seats', 'Gratuit'),
                   ('bank_id', 'Communication'), ('origin', 'Origine')]
        table_header_row = tuple(
            ('th', (('a', 'href', make_url(update_sort_order(column, sort_order), limit, offset)),
                    header + sort_direction(column, sort_order)))
            for column, header in COLUMNS)
        total_bookings = Reservation.length(connection)
        pagination_links = tuple((
            x for x in
            [('li', (('a', 'href', make_url(sort_order, limit, 0)), 'Début'))
             if offset > 0
             else None,
             ('li',
              (('a', 'href', make_url(sort_order, limit, offset - limit)), 'Précédent'))
             if offset > limit else
             None,
             ('li',
              (('a', 'href', make_url(sort_order, limit, offset + limit)), 'Suivant'))
             if offset + limit < total_bookings else
             None]
            if x is not None))
        respond_html(html_document(
            'List of reservations',
            (('ul', *pagination_links) if pagination_links else '',
             ('p', 'Il y a ', str(total_bookings), ' bulle', '' if total_bookings == 1 else 's', ' en tout.'),
             (('form', 'action', os.getenv('SCRIPT_NAME')),
              (('label', 'for', 'limit'), 'Limiter le tableau à ', ('em', 'n'), ' lignes:'),
              (('input', 'id', 'limit', 'type', 'number', 'name', 'limit', 'min', '5', 'value', str(limit), 'max', '10000'),),
              (('input', 'type', 'submit', 'value', 'Rafraichir la page'),),
              *((('input', 'id', 'sort_order', 'name', 'sort_order', 'type', 'hidden', 'value', v),)
                for v in sort_order),
              (('input', 'id', 'offset', 'name', 'offset', 'type', 'hidden', 'value', str(offset)),)),
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
                                                        'formulaire web')))
                     for r in Reservation.select(connection,
                                                 order_columns=sort_order,
                                                 limit=limit,
                                                 offset=offset))),
             ('hr',),
             ('p', 'Ajouter une réservation:'),
             (('form', 'method', 'post', 'action', 'add_unchecked_reservation.cgi'),
              (('input', 'type', 'hidden', 'id', 'csrf_token', 'name', 'csrf_token', 'value', csrf_token.token),),
              (('label', 'for', 'name'), 'Nom'),
              (('input', 'id', 'name', 'name', 'name', 'type', 'text', 'placeholder', 'Nom de la bulle', 'required', 'required', 'style', 'width:100%;'),),
              ('br',),
              (('label', 'for', 'comment'), 'Commentaire'),
              (('input', 'id', 'comment', 'name', 'comment', 'type', 'text', 'placeholder', 'Commentaire', 'required', 'required', 'style', 'width:100%;'),),
              ('br',),
              (('input', 'id', 'samedi', 'name', 'date', 'type', 'radio', 'value', '2021-12-04'),),
              (('label', 'for', 'samedi'), 'Samedi 4 décembre 2021 à 20h'),
              ('br',),
              (('input', 'id', 'dimanche', 'name', 'date', 'type', 'radio', 'value', '2021-12-05'),),
              (('label', 'for', 'dimanche'), 'Dimanche 5 décembre 2021 à 15h'),
              ('br',),
              (('label', 'for', 'paying_seats'), 'Places payantes:'),
              (('input', 'id', 'paying_seats', 'name', 'paying_seats', 'type', 'number', 'min', '0'),),
              ('br',),
              (('label', 'for', 'free_seats'), 'Places gratuites:'),
              (('input', 'id', 'free_seats', 'name', 'free_seats', 'type', 'number', 'min', '0'),),
              ('br',),
              (('input', 'type', 'submit', 'value', 'Confirmer'),)))))
    except Exception:
        if print_content_type('text/html; charset=utf-8'):
            print()
        cgitb.handler()
