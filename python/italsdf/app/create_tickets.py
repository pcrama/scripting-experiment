# -*- coding: utf-8 -*-
import itertools
import pricing
from htmlgen import (pluriel_naif)

# From https://docs.python.org/3/library/itertools.html?highlight=itertools:
def grouper(iterable, n, *, incomplete='fill', fillvalue=None):
    "Collect data into non-overlapping fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, fillvalue='x') --> ABC DEF Gxx
    # grouper('ABCDEFG', 3, incomplete='strict') --> ABC DEF ValueError
    # grouper('ABCDEFG', 3, incomplete='ignore') --> ABC DEF
    args = [iter(iterable)] * n
    if incomplete == 'fill':
        return itertools.zip_longest(*args, fillvalue=fillvalue)
    if incomplete == 'strict':
        return zip(*args, strict=True)
    if incomplete == 'ignore':
        return zip(*args)
    else:
        raise ValueError('Expected fill, strict, or ignore')


def tabulate(columns, orders, fillvalue):
    '''Distribute a list of orders into a table

        >>> list(tabulate(3, [('Foo', 3), ('Xyzzy', 0), ('Baz', 5)], '---'))
        [('Foo', 'Foo', 'Foo'), ('Baz', 'Baz', 'Baz'), ('Baz', 'Baz', '---')]
    '''
    return grouper(
        itertools.chain(*itertools.starmap(itertools.repeat, orders)),
        columns,
        fillvalue=fillvalue)


def _ticket_table(fondus, assiettes, bolo, scampis, tiramisu, tranches):
    return (('table', 'class', 'tickets'),
            *(('tr', *(('td', cell) for cell in row)) for row in tabulate(
                4,
                [('Fondus au fromage', fondus),
                 ('Charcuterie', assiettes),
                 ('Spaghettis Bolognaise', bolo),
                 ('Spaghettis aux scampis', scampis),
                 ('Tiramisu', tiramisu),
                 ('Tranche Napolitaine', tranches)],
                '-x-x-')))


def _heading(*content):
    return ('h3', *content)


def create_tickets_for_one_reservation(r):
    total_tickets = (
        r.outside_fondus + r.inside_fondus +
        r.outside_assiettes + r.inside_assiettes +
        r.outside_bolo + r.inside_bolo +
        r.outside_scampis + r.inside_scampis +
        r.outside_tiramisu + r.inside_tiramisu +
        r.outside_tranches + r.inside_tranches)
    return (
        ()
        if total_tickets == 0
        else ((('div', 'class', 'no-print-page-break'),
               _heading(r.name, ' ', r.date),
               ('p', 'Total: ', pricing.price_in_euros(r), ' pour ', pluriel_naif(total_tickets, 'ticket'), '.')),
              _ticket_table(
                  r.outside_fondus + r.inside_fondus,
                  r.outside_assiettes + r.inside_assiettes,
                  r.outside_bolo + r.inside_bolo,
                  r.outside_scampis + r.inside_scampis,
                  r.outside_tiramisu + r.inside_tiramisu,
                  r.outside_tranches + r.inside_tranches)))


def create_full_ticket_list(rs, fondus, assiettes, bolo, scampis, tiramisu, tranches):
    for r in rs:
        fondus -= r.outside_fondus + r.inside_fondus
        assiettes -= r.outside_assiettes + r.inside_assiettes
        bolo -= r.outside_bolo + r.inside_bolo
        scampis -= r.outside_scampis + r.inside_scampis
        tiramisu -= r.outside_tiramisu + r.inside_tiramisu
        tranches -= r.outside_tranches + r.inside_tranches
        if fondus < 0 or assiettes < 0 or bolo < 0 or scampis < 0 or tiramisu < 0 or tranches < 0:
            raise Exception(
                'Not enough tickets: '
                + f'fondus={fondus}, assiettes={assiettes}, bolo={bolo}, '
                + f'scampis={scampis}, tiramisu={tiramisu}, tranches={tranches}')
        for e in create_tickets_for_one_reservation(r):
            yield e
    
    yield _heading('Vente libre')
    yield ('p',
           f'fondus={fondus}, assiettes={assiettes}, bolo={bolo}, ',
           f'scampis={scampis}, tiramisu={tiramisu}, tranches={tranches}')
    yield _ticket_table(
        fondus=fondus,
        assiettes=assiettes,
        bolo=bolo,
        scampis=scampis,
        tiramisu=tiramisu,
        tranches=tranches)
