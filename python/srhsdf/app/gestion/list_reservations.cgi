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
        if new_col_name == sort_order[0]:
            return sort_order[1:]
        else:
            return [new_col_name] + [x for x in sort_order if x != new_col_name]
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

        respond_html(html_document(
            'List of reservations',
            (('p', 'test'),
             ('table',
              ('tr',
               ('th', (('a', 'href', make_url(update_sort_order('name', sort_order), limit, offset)),
                       'Nom')),
               ('th', (('a', 'href', make_url(update_sort_order('email', sort_order), limit, offset)),
                       'Email')),
               ('th', (('a', 'href', make_url(update_sort_order('date', sort_order), limit, offset)),
                       'Date')),
               ('th', (('a', 'href', make_url(update_sort_order('paying_seats', sort_order), limit, offset)),
                       'Payant')),
               ('th', (('a', 'href', make_url(update_sort_order('free_seats', sort_order), limit, offset)),
                       'Gratuit')),
               ('th', (('a', 'href', make_url(update_sort_order('bank_id', sort_order), limit, offset)),
                       'Communication'))))
             + tuple(('tr',
                      ('td', r.name),
                      ('td', r.email),
                      ('td', r.date),
                      ('td', r.paying_seats),
                      ('td', r.free_seats),
                      ('td', r.bank_id))
                     for r in Reservation.select(connection,
                                                 order_columns=','.join(sort_order),
                                                 limit=limit,
                                                 offset=offset)))))
    except Exception:
        if print_content_type('text/html; charset=utf-8'):
            print()
        cgitb.handler()
