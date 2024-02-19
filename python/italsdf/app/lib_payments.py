import cgi
import csv
import io
import sqlite3
import os
import time
from typing import Any, Callable, Iterable, Optional, Union
from urllib.parse import urlencode, urljoin, urlunsplit

from storage import Csrf, Payment, Reservation
from htmlgen import (
    cents_to_euro,
    format_bank_id,
    html_document,
    redirect,
    redirect_to_event,
    respond_html,
)
from lib_post_reservation import (
    make_show_reservation_url
)

def get_parameters_for_GET() -> tuple[Optional[str], Optional[int], Optional[int]]:
    params = cgi.parse()
    filtering = params.get("filtering")

    try:
        offset = int(params["offset"])
    except Exception:
        offset = None

    try:
        limit = int(params["limit"])
    except Exception:
        limit = None
        
    return (filtering, offset, limit)


BANK_STATEMENT_HEADERS = {
    "fr": {'N\xba de s\xe9quence': "src_id",
           'Date d\'ex\xe9cution': "timestamp",
           'Montant': "amount_in_cents",
           'Contrepartie': "other_account",
           'Nom de la contrepartie': "other_name",
           'Statut': "status",
           'Communication': "comment"}}


def _normalize_header(s: str) -> str:
    s = s.strip()
    return s[1:] if s.startswith('\ufeff') else s

def make_payment_builder(header_row: list[str]) -> Callable[[list[str], Optional[Payment]], Payment]:
    col_name_to_idx = {_normalize_header(col_name): col_idx for col_idx, col_name in enumerate(header_row)}
    columns = {}
    for mapping in BANK_STATEMENT_HEADERS.values():
        try:
            columns = {attr_name: col_name_to_idx[col_name] for col_name, attr_name in mapping.items()}
        except KeyError:
            pass
    if not columns:
        raise RuntimeError("Unable to map header row to Payment class definition")

    def payment_builder(row: list[str], proto: Optional[Payment]=None) -> Payment:
        amount_in_cents = round(float(row[columns["amount_in_cents"]].replace(",", ".")) * 100)
        return Payment(
            None,
            timestamp=time.mktime(time.strptime(f"{row[columns['timestamp']]}T12:00+01:00", "%d/%m/%YT%H:%M%z")),
            amount_in_cents=amount_in_cents,
            comment=row[columns['comment']],
            uuid=None,
            src_id=row[columns['src_id']],
            other_account=row[columns['other_account']],
            other_name=row[columns['other_name']],
            status=row[columns['status']],
            user=None if proto is None else proto.user,
            ip=None if proto is None else proto.ip,
            confirmation_timestamp=None if proto is None else proto.confirmation_timestamp,
        )

    return payment_builder


def import_bank_statements(connection, bank_statements_csv: str, user:str, ip: str) -> list[tuple[Exception, Payment]]:
    csv_reader = csv.reader(io.StringIO(bank_statements_csv), delimiter=';')
    builder = make_payment_builder(next(csv_reader))
    proto = Payment(
        rowid=None, timestamp=None, amount_in_cents=None, comment=None, uuid=None, src_id=None, other_account=None, other_name=None, status=None, user=user, ip=ip, confirmation_timestamp=None,
    )
    exceptions = []
    with connection:
        for row in csv_reader:
            pmnt = builder(row, proto)
            try:
                pmnt.insert_data(connection)
            except sqlite3.IntegrityError as exc:
                # My python versions and their shipped sqlite3 modules differ between my dev system and my deployment system :sad:
                old_style_unique_constraint_error = exc.args and isinstance(exc.args[0], str) and exc.args[0].startswith('UNIQUE ')
                new_style_unique_constraint_error = hasattr(exc, 'sqlite_errorname') and exc.sqlite_errorname == 'SQLITE_CONSTRAINT_UNIQUE'
                if old_style_unique_constraint_error or new_style_unique_constraint_error:
                    exceptions.append((None, pmnt))
                else:
                    exceptions.append((exc, pmnt))
            except Exception as exc:
                exceptions.append((exc, pmnt))
            else:
                exceptions.append((None, pmnt))
    return exceptions


def get_list_payments_row(
        connection: Union[sqlite3.Cursor, sqlite3.Connection],
        pmnt: Payment,
        res: Optional[Reservation],
        server_name: str,
        script_name: str,
        csrf_token: str) -> Iterable[tuple[Union[str, Iterable[str]], Any]]:
    return (('td', pmnt.src_id),
            ('td', time.strftime('%d/%m/%Y', time.gmtime(pmnt.timestamp))),
            ('td', pmnt.other_account),
            ('td', pmnt.other_name),
            ('td' if pmnt.money_received() else ('td', 'class', 'payment-not-ok'), pmnt.status),
            ('td', pmnt.comment),
            ('td' if pmnt.money_received() else ('td', 'class', 'payment-not-ok'), cents_to_euro(pmnt.amount_in_cents)),
            ('td', maybe_link_to_reservation(connection, pmnt, res, server_name, script_name, csrf_token)))


def _concat_name_and_mail(res: Reservation) -> str:
    if res.email is None or not res.email.strip():
        return res.name
    else:
        return res.name + ' ' + res.email


def maybe_link_to_reservation(
        connection: Union[sqlite3.Cursor, sqlite3.Connection],
        pmnt: Payment,
        res: Optional[Reservation],
        server_name: str,
        script_name: str,
        csrf_token: str) -> Union[str, Iterable[Any]]:
    # drop "gestion/" from .../gestion/script.cgi
    (script_dir, script_basename) = os.path.split(script_name)
    script_super_dir = os.path.dirname(script_dir)
    if res is not None:
        return ('div',
                (('form', 'style', 'display: inline', 'method', 'POST', 'action', os.path.join(script_dir, 'link_payment_and_reservation.cgi')),
                 (('a',
                   'href',
                   make_show_reservation_url(
                       res.uuid, server_name=server_name, script_name=os.path.join(script_super_dir, script_basename))),
                  _concat_name_and_mail(res)),
                 ' ',
                 (('input', 'type', 'hidden', 'name', 'csrf_token', 'value', csrf_token),),
                 (('input', 'type', 'hidden', 'name', 'src_id', 'value', pmnt.src_id),),
                 (('input', 'type', 'hidden', 'name', 'reservation_uuid', 'value', ''),),
                 (('input', 'type', 'submit', 'value', 'X'),)),
                (('a', 'href', urlunsplit((
                    'https',
                    server_name,
                    os.path.join(script_dir, 'confirm_payment.cgi'),
                    urlencode((('uuid_hex', res.uuid), ('src_id', pmnt.src_id))),
                    ''))),
                 '🖄' if pmnt.confirmation_timestamp is None else 'send again?'))

    bank_id = pmnt.comment.strip().replace("+", "").replace("/", "")
    if len(bank_id) != 12 or not all(ch.isdigit() for ch in bank_id):
        return _maybe_link__make_form_when_no_reservation_matches_well(connection, pmnt, csrf_token, script_dir)

    matching_reservation = Reservation.find_by_bank_id(connection, bank_id)
    if matching_reservation is None:
        return _maybe_link__make_form_when_no_reservation_matches_well(connection, pmnt, csrf_token, script_dir)

    return (('form', 'method', 'POST', 'action', os.path.join(script_dir, 'link_payment_and_reservation.cgi')),
            (('input', 'type', 'hidden', 'name', 'csrf_token', 'value', csrf_token),),
            (('input', 'type', 'hidden', 'name', 'src_id', 'value', pmnt.src_id),),
            (('select', 'name', 'reservation_uuid'),
             _maybe_link__make_option(matching_reservation, bank_id),
             *(_maybe_link__make_option(res) for res in Reservation.list_reservations_for_linking_with_payments(connection, matching_reservation.uuid))),
            (('input', 'type', 'submit', 'value', 'OK'),))


def _maybe_link__make_option(res: Reservation, bank_id: Union[str, None]=None) -> Iterable[Any]:
    return (('option', 'value', res.uuid, *(() if bank_id is None else ('selected', 'selected'))), format_bank_id(res.bank_id), ' ', _concat_name_and_mail(res))


def _maybe_link__make_form_when_no_reservation_matches_well(connection, pmnt: Payment, csrf_token: str, script_dir: str) -> Union[str, Iterable[Any]]:
    options = [_maybe_link__make_option(res) for res in Reservation.list_reservations_for_linking_with_payments(connection, '')]
    if options:
        return (('form', 'method', 'POST', 'action', os.path.join(script_dir, 'link_payment_and_reservation.cgi')),
                (('input', 'type', 'hidden', 'name', 'csrf_token', 'value', csrf_token),),
                (('input', 'type', 'hidden', 'name', 'src_id', 'value', pmnt.src_id),),
                (('select', 'name', 'reservation_uuid'),
                 (('option', 'value', ''), '--- Choisir la réservation correspondante ---'),
                 *options),
                (('input', 'type', 'submit', 'value', 'OK'),))
    else:
        return "#N/A"


def fail_link_payment_and_reservation():
    redirect_to_event()


def respond_link_payment_and_reservation_error(error_title, error_html, list_payments):
    respond_html(html_document(
        error_title,
        error_html + (('br', ),
                      ('p', (('a', 'href', list_payments),
                             'Retour à la liste des paiements')))))

def link_payment_and_reservation(db_connection, server_name: str, script_name: str, user: str, ip: str) -> None:
    list_payments = f"https://{server_name}{os.path.join(os.path.dirname(script_name), 'list_payments.cgi')}"
    # Get form data
    form = cgi.FieldStorage()
    csrf_token = form.getfirst('csrf_token')
    if csrf_token is None:
        fail_link_payment_and_reservation()
        return None
    else:
        try:
            Csrf.validate_and_update(db_connection, csrf_token, user, ip)
        except KeyError:
            fail_link_payment_and_reservation()
            return None

    reservation_uuid = form.getfirst('reservation_uuid', '')

    src_id = form.getfirst('src_id')
    if not src_id:
        respond_link_payment_and_reservation_error('Formulaire incomplet', (('p', "Il n'y avait pas de ", ("code", "src_id"), " dans le formulaire."), ), list_payments)
        return

    try:
        payment = Payment.find_by_src_id(db_connection, src_id)
    except Exception as exc:
        respond_link_payment_and_reservation_error(
            "Erreur de recherche",
            (("p", "Le paiement '", str(src_id), "' n'a pas été retrouvé: ", repr(exc)),),
            list_payments)
        return

    if payment is None:
        respond_link_payment_and_reservation_error(
            "Paiement inconnu",
            (('p', "Le paiement '", str(src_id), "' n'a pas été retrouvé."),),
            list_payments)
        return

    try:
        with db_connection:
            payment.update_uuid(db_connection, reservation_uuid, user, ip)
    except Exception as exc:
        respond_link_payment_and_reservation_error(
            "Erreur d'écriture",
            (("p", "Le paiement '", str(src_id), "' n'a pas pu être mis à jour: ", repr(exc)),),
            list_payments)
        return

    send_email = urlunsplit((
        'https',
        server_name,
        os.path.join(os.path.dirname(script_name), 'confirm_payment.cgi'),
        urlencode((('uuid_hex', reservation_uuid), ('src_id', src_id))),
        ''))
    redirect(send_email)
