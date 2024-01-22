#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import os
import sys

# hack to get at my utilities:
sys.path.append('..')
import config
from htmlgen import (
    html_document,
    pluriel_naif,
    print_content_type,
    redirect,
    redirect_to_event,
    respond_html,
)
from storage import (
    Csrf,
    create_db,
)
from lib_payments import (
    import_bank_statements,
)


def fail_import_payments():
    redirect_to_event()


def decode_list(bs) -> list[str]:
    try:
        return [b.decode("utf-8") for b in bs]
    except UnicodeDecodeError:
        return [b.decode("latin1", errors='replace') for b in bs]


def post_method(db_connection, server_name, script_name, user, ip):
    list_payments = f"https://{server_name}{os.path.join(os.path.dirname(script_name), 'list_payments.cgi')}"
    # Get form data
    cgi.maxlen = 10 * 1024 * 1024
    form = cgi.FieldStorage()
    csrf_token = form.getfirst('csrf_token')
    if csrf_token is None:
        fail_import_payments()
    else:
        try:
            csrf = Csrf.validate_and_update(db_connection, csrf_token, user, ip)
        except KeyError:
            fail_import_payments()

    csv_file = form['csv_file']
    if not csv_file.file:
        respond_html(html_document('No input data', (('p', 'No input data'), )))
        return

    csv = "".join(decode_list(line for line in csv_file.file)).strip()
    if not csv:
        redirect(list_payments)
        return

    try:
        import_result = import_bank_statements(db_connection, csv, user, ip)
    except Exception as exc:
        respond_html(html_document(
            "Erreur d'import de fichier CSV",
            (("p", "L'import du fichier CSV a échoué à cause de ", repr(exc)),
             ('p', (('a', 'href', list_payments), 'Retour à la liste des paiements')))))
        return

    exceptions = [(e, p) for e, p in import_result if e]
    if exceptions:
        respond_html(html_document(
            f"{pluriel_naif(len(exceptions), 'Erreur')} lors de l'import de {pluriel_naif(len(import_result), 'paiements')}",
            (('ul',
              *(('li', str(e), ('br', ), repr(p)) for e, p in exceptions)), )))
        return

    redirect(list_payments)


if __name__ == '__main__':
    db_connection = None
    try:
        remote_user = os.getenv('REMOTE_USER')
        remote_addr = os.getenv('REMOTE_ADDR')
        if not remote_user or not remote_addr:
            fail_import_payments()

        CONFIGURATION = config.get_configuration()

        cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

        db_connection = create_db(CONFIGURATION)

        if os.getenv('REQUEST_METHOD') == 'POST':
            server_name = os.getenv('SERVER_NAME')
            script_name = os.getenv('SCRIPT_NAME')
            if server_name and script_name:
                post_method(db_connection, server_name, script_name, remote_user, remote_addr)
            else:
                fail_import_payments()
        else:
            fail_import_payments()
    except Exception:
        if print_content_type('text/html; charset=utf-8'):
            print('Content-Language: en')
            print()
        raise
    finally:
        if db_connection:
            try:
                db_connection.close()
            except Exception:
                pass
