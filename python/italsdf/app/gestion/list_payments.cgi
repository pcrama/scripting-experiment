#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
#
# Test with
#
# (cd app/gestion && env REQUEST_METHOD=GET REMOTE_USER=secretaire REMOTE_ADDR=1.2.3.4 SERVER_NAME=localhost SCRIPT_NAME=list_payments.cgi python list_payments.cgi)

import cgi
import cgitb
import itertools
import os
import sys
import urllib.parse

# hack to get at my utilities:
sys.path.append('..')
import config
from htmlgen import (
    html_document,
    format_bank_id,
    pluriel_naif,
    print_content_type,
    redirect_to_event,
    respond_html,
)
from storage import (
    Csrf,
    Payment,
    create_db,
)
from lib_payments import get_list_payments_row

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

        COLUMNS = [('src_id', 'N° séquence'),
                   ('timestamp', 'Date exécution'),
                   ('other_account', 'Contrepartie'),
                   ('other_name', 'Nom Contrepartie'),
                   ('status', 'Statut'),
                   ('comment', 'Communication'),
                   ('amount_in_cents', 'Montant'),
                   ]
        table_header_row = tuple(
            ('th', make_navigation_a_elt(update_sort_order(column, sort_order), limit, offset,
                                         header + sort_direction(column, sort_order)))
            for column, header in COLUMNS) + (('th', 'Réservation'),)
        payment_count = Payment.length(connection)
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
             if offset + limit < payment_count else
             None]
            if x is not None))
        respond_html(html_document(
            'List of payments',
            ((('form', 'method', 'POST', 'action', 'import_payments.cgi', 'id', 'import_csv', 'enctype', 'multipart/form-data'),
              (('input', 'type', 'hidden', 'id', 'csrf_token', 'name', 'csrf_token', 'value', csrf_token.token),),
              (('label', 'for', 'csv_file'), 'Extraits de compte au format CSV:'),
              (('input', 'type', 'file', 'id', 'csv_file', 'name', 'csv_file'), ),
              (('input', 'type', 'submit', 'value', 'Importer les extraits de compte'),)),
             (('form', 'action', os.getenv('SCRIPT_NAME'), 'id', 'pagination'),
              (('label', 'for', 'limit'), 'Limiter le tableau à ', ('em', 'n'), ' lignes:'),
              (('input', 'id', 'limit', 'type', 'number', 'name', 'limit', 'min', '5', 'value', str(limit), 'max', '10000'),),
              (('input', 'type', 'submit', 'value', 'Rafraichir la page'),),
              *((('input', 'id', 'sort_order', 'name', 'sort_order', 'type', 'hidden', 'value', v),)
                for v in sort_order),
              (('input', 'id', 'offset', 'name', 'offset', 'type', 'hidden', 'value', str(offset)),)),
             (('ul', 'class', 'navbar'), *pagination_links) if pagination_links else '',
             (('table', 'class', 'list'),
              ('tr', *table_header_row),
              *tuple(('tr', *get_list_payments_row(pmnt, res))
                     for pmnt, res in Payment.join_reservations(connection,
                                                                order_columns=sort_order,
                                                                limit=limit,
                                                                offset=offset))),
             ('hr',),
             ('ul',
              ('li', (('a', 'href', 'list_reservations.cgi'), 'Liste des réservations')),
              ('li', (('a', 'href', 'generate_tickets.cgi'), 'Générer les tickets nourriture pour impression'))))))
    except Exception:
        if print_content_type('text/html; charset=utf-8'):
            print()
        cgitb.handler()
