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
    cents_to_euro,
    format_bank_id,
    print_content_type,
    redirect_to_event,
)
from storage import (
    Reservation,
    create_db,
)

if __name__ == '__main__':
    if os.getenv('REQUEST_METHOD') != 'GET' or not os.getenv('REMOTE_USER'):
        redirect_to_event()

    CONFIGURATION = config.get_configuration()
    cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

    try:
        connection = create_db(CONFIGURATION)
        writer = csv.writer(sys.stdout, 'excel')
        if print_content_type('text/csv; charset=utf-8'):
            print()
        writer.writerow((
            'H/F', 'Nom', 'Prénom', 'Email', 'Date', 'Payants', 'Gratuits', 'Dû', 'Communication', 'Origine', 'Commentaire', 'Actif', 'Email RGPD'
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
            euros_due = (''
                         if (x.cents_due is None or not math.isfinite(x.cents_due)) else
                         cents_to_euro(x.remaining_amount_due_in_cents(connection)) + '€')
            writer.writerow((
                x.civility, x.last_name, x.first_name, email, x.date, x.paying_seats, x.free_seats, euros_due, format_bank_id(x.bank_id), x.origin, comment, x.active, gdpr_email
            ))
    except Exception:
        if print_content_type('text/html; charset=utf-8'):
            print()
        cgitb.handler()
