#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
import cgitb
import os
import sys

# hack to get at my utilities:
sys.path.append('..')
import config
from htmlgen import print_content_type
from storage import create_db
from lib_payments import (
    fail_link_payment_and_reservation,
    link_payment_and_reservation,
)


def main() -> None:
    try:
        remote_user = os.getenv('REMOTE_USER')
        remote_addr = os.getenv('REMOTE_ADDR')
        if not remote_user or not remote_addr:
            fail_link_payment_and_reservation()
            return None

        CONFIGURATION = config.get_configuration()

        cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

        if os.getenv('REQUEST_METHOD') == 'POST':
            server_name = os.getenv('SERVER_NAME')
            script_name = os.getenv('SCRIPT_NAME')
            if server_name and script_name:
                with create_db(CONFIGURATION) as db_connection:
                    link_payment_and_reservation(db_connection, server_name, script_name, remote_user, remote_addr)
                    return None
            else:
                fail_link_payment_and_reservation()
                return None
        else:
            fail_link_payment_and_reservation()
            return None
    except Exception:
        if print_content_type('text/html; charset=utf-8'):
            print('Content-Language: en')
            print()
        raise


if __name__ == '__main__':
    main()
