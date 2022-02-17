#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import os

import config
from htmlgen import (
    html_document,
    pluriel_naif,
    print_content_type,
    redirect,
    respond_html,
)
from storage import(
    Reservation,
    create_db,
)
from pricing import (
    price_in_euros,
)

CONCERT_PAGE = 'https://www.srhbraine.be/soiree-italienne-2022/'

    
def commande(categorie, nombre1, nom1, nombre2, nom2):
    commandes = [
        pluriel_naif(n, x) for (n, x) in ((nombre1, nom1), (nombre2, nom2)) if n > 0]
    if len(commandes) == 0:
        return ''
    elif len(commandes) == 1:
        return (f'{categorie}: {commandes[0]}',)
    else:
        return (categorie, (('ul', ), *((('li',), x) for x in commandes)))

if __name__ == '__main__':
    
    if os.getenv('REQUEST_METHOD') != 'GET':
        redirect(CONCERT_PAGE)
    CONFIGURATION = config.get_configuration()

    cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

    # Get form data
    form = cgi.FieldStorage()
    uuid_hex = form.getfirst('uuid_hex', default='')

    db_connection = create_db(CONFIGURATION)

    try:
        reservation = next(Reservation.select(
            db_connection,
            filtering=[('uuid', uuid_hex)],
            limit=1))
    except StopIteration:
        redirect(CONCERT_PAGE)

    if print_content_type('text/html; charset=utf-8'):
        print('Content-Language: en')
        print()

    places = ()
    if reservation.places > 0:
        places += (' pour ', pluriel_naif(reservation.places, 'place'))
    places += (' a été enregistrée.',)
    commandes = [x for x in (commande('Entrée',
                                      reservation.fondus,
                                      ['Assiette de fondus au fromage', 'Assiettes de fondus au fromage'],
                                      reservation.assiettes,
                                      ['Assiette de charcuterie italienne', 'Assiettes de charcuterie italienne']),
                             commande('Plat',
                                      reservation.bolo,
                                      ['Spaghetti Bolognaise', 'Spaghettis Bolognaise'],
                                      reservation.scampis,
                                      ['Spaghetti aux Scampis', 'Spaghettis aux Scampis']),
                             commande('Dessert',
                                      reservation.tiramisu,
                                      'Tiramisu',
                                      reservation.tranches,
                                      ['Tranche Napolitaine', 'Tranches Napolitaines']))
                 if x]
    if commandes:
        commandes = (('p', "Merci de nous avoir informé de votre commande à titre indicatif.  ",
                      "Nous préparerons vos tickets à l'entrée pour faciliter votre commande.  ",
                      'Le prix total est de ', price_in_euros(reservation), ' pour le repas.'),
                     (('ul', ), *((('li',), *x) for x in commandes)))
    else:
        commandes = (('p', "La commande des repas se fera à l'entrée."),)
    respond_html(html_document(
        'Réservation effectuée',
        (('p', 'Votre réservation au nom de ', reservation.name, *places),
         *commandes,
         ('p', (('a', 'href', CONCERT_PAGE), 'Cette page'), ' sera tenue à jour avec '
          'les mesures de sécurité en vigueur lors de notre repas italien. Merci de la consulter '
          'régulièrement. ',
          (('a', 'href', f"mailto:{CONFIGURATION['info_email']}"), 'Contactez-nous'),
          ' si vous avez encore des questions.'),
         ('p', 'Un tout grand merci pour votre présence le ', reservation.date,
          ': le soutien de nos auditeurs nous est indispensable!'))))
