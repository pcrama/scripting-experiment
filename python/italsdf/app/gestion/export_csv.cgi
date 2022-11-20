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
    redirect_to_event,
)
from storage import (
    Reservation,
    create_db,
)
from pricing import (
    price_in_euros
)
from lib_export_csv import (
    export_reservation,
    write_column_header_rows,
)

if __name__ == '__main__':
    if os.getenv('REQUEST_METHOD') != 'GET' or os.getenv('REMOTE_USER') is None:
        redirect_to_event()

    CONFIGURATION = config.get_configuration()
    cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

    try:
        connection = create_db(CONFIGURATION)
        writer = csv.writer(sys.stdout, 'excel')
        if print_content_type('text/csv; charset=utf-8'):
            print()
        write_column_header_rows(writer)
        for x in Reservation.select(connection,
                                    order_columns=('ACTIVE', 'date', 'name')):
            export_reservation(writer, x)
    except Exception:
        if print_content_type('text/html; charset=utf-8'):
            print()
        cgitb.handler()
