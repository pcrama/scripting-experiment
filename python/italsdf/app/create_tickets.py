# -*- coding: utf-8 -*-
import itertools
import pricing
from htmlgen import (pluriel_naif)
import config

TICKET_IMAGE = config.get_configuration().get('ticket_image', 'default.png')


def _make_order(kind, plate):
    return ((('div', 'class', 'ticket-left-col'),
             ('div', 'table n°'), ('div', 'serveur'), ('div', kind), ('div', plate)),
            ('div', (('img', 'src', TICKET_IMAGE),)))


def _ticket_table(fondus, assiettes, bolo, scampis, tiramisu, tranches):
    return (('div', 'class', 'tickets'),
            *itertools.chain(
                *itertools.chain(
                    *(x
                      for x in (
                              itertools.repeat(_make_order(kind, plate), quantity)
                              for kind, plate, quantity
                              in (('entrée:', 'Fondus au fromage', fondus),
                                  ('entrée:', 'Assiette italienne', assiettes),
                                  ('plat:', 'Spaghetti bolognaise', bolo),
                                  ('plat:', 'Spaghetti aux scampis', scampis),
                                  ('dessert:', 'Tiramisu', tiramisu),
                                  ('dessert:', 'Tranche napolitaine', tranches)))))))


def _heading(*content):
    return (('div', 'class', 'ticket-heading'), *content)


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
               ('div', 'Total: ', pricing.price_in_euros(r), ' pour ', pluriel_naif(total_tickets, 'ticket'), '.')),
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
    yield ('div',
           f'fondus={fondus}, assiettes={assiettes}, bolo={bolo}, ',
           f'scampis={scampis}, tiramisu={tiramisu}, tranches={tranches}')
    yield _ticket_table(
        fondus=fondus,
        assiettes=assiettes,
        bolo=bolo,
        scampis=scampis,
        tiramisu=tiramisu,
        tranches=tranches)
