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

        COLUMNS = [('name', 'Nom'), ('email', 'Email'), ('date', 'Date'),
                   ('paying_seats', 'Payant'), ('free_seats', 'Gratuit'),
                   ('bank_id', 'Communication')]
        table_header_row = tuple(
            ('th', (('a', 'href', make_url(update_sort_order(column, sort_order), limit, offset)),
                    header + sort_direction(column, sort_order)))
            for column, header in COLUMNS)
        total_bookings = Reservation.length(connection)
        respond_html(html_document(
            'List of reservations',
            (('ul',
              *tuple(x for x in
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
                     if x is not None)),
             ('p', 'Il y a ', str(total_bookings), ' bulle', '' if total_bookings == 1 else 's', ' en tout.'),
             ('table',
              ('tr', *table_header_row),
              *tuple(('tr',
                      ('td', r.name),
                      ('td', r.email),
                      ('td', r.date),
                      ('td', r.paying_seats),
                      ('td', r.free_seats),
                      ('td', r.bank_id))
                     for r in Reservation.select(connection,
                                                 order_columns=sort_order,
                                                 limit=limit,
                                                 offset=offset))))))
    except Exception:
        if print_content_type('text/html; charset=utf-8'):
            print()
        cgitb.handler()
