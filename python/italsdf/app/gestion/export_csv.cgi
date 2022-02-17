#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
import cgitb
import csv
import math
import os
import sys

# hack to get at my utilities:
sys.path.append('..')
import config
from htmlgen import (
    print_content_type,
    redirect,
)
from storage import (
    Reservation,
    create_db,
)

if __name__ == '__main__':
    if os.getenv('REQUEST_METHOD') != 'GET' or os.getenv('REMOTE_USER') is None:
        redirect('https://www.srhbraine.be/soiree-italienne-2022/')

    CONFIGURATION = config.get_configuration()
    cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

    try:
        connection = create_db(CONFIGURATION)
        writer = csv.writer(sys.stdout, 'excel')
        if print_content_type('text/csv; charset=utf-8'):
            print()
        writer.writerow((
            'Nom', 'Email', 'Places', 'Date', 'Fondus', 'Charcuterie', 'Bolo', 'Scampis', 'Tiramisu', 'Napolitaines', 'Origine', 'Commentaire', 'Actif', 'Email RGPD'
        ))
        for x in Reservation.select(connection,
                                    order_columns=('ACTIVE', 'date', 'name')):
            if x.origin:
                comment = x.email
                email = ''
                gdpr_email = ''
            else:
                comment = ''
                email = x.email
                gdpr_email = x.email if x.gdpr_accepts_use else ''
            writer.writerow((
                x.name, email, x.places, x.date, x.fondus, x.assiettes, x.bolo, x.scampis, x.tiramisu, x.tranches, x.origin, comment, x.active, gdpr_email
            ))
    except Exception:
        if print_content_type('text/html; charset=utf-8'):
            print()
        cgitb.handler()
