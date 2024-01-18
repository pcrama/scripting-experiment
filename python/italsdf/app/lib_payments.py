import cgi
import csv
import io
import sqlite3
import os
import time
from typing import Any, Callable, Iterable, Optional, Union

from storage import Payment, Reservation
from htmlgen import (
    cents_to_euro,
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
        )

    return payment_builder


def import_bank_statements(connection, bank_statements_csv: str, user:str, ip: str) -> list[tuple[Exception, Payment]]:
    csv_reader = csv.reader(io.StringIO(bank_statements_csv), delimiter=';')
    builder = make_payment_builder(next(csv_reader))
    proto = Payment(
        rowid=None, timestamp=None, amount_in_cents=None, comment=None, uuid=None, src_id=None, other_account=None, other_name=None, status=None, user=user, ip=ip
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


def get_list_payments_row(pmnt: Payment, res: Optional[Reservation]) -> Iterable[tuple[Union[str, Iterable[str]], Any]]:
    return (('td', pmnt.src_id),
            ('td', time.strftime('%d/%m/%Y', time.gmtime(pmnt.timestamp))),
            ('td', pmnt.other_account),
            ('td', pmnt.other_name),
            ('td' if pmnt.money_received() else ('td', 'class', 'payment-not-ok'), pmnt.status),
            ('td', pmnt.comment),
            ('td', cents_to_euro(pmnt.amount_in_cents)),
            ('td', maybe_link_to_reservation(res)))


def maybe_link_to_reservation(res: Optional[Reservation]) -> Union[str, tuple[Iterable[str], str]]:
    if res is None:
        return "???"
    else:
        return (('a', 'href', make_show_reservation_url(res.uuid, script_name=os.path.dirname(os.environ["SCRIPT_NAME"]))), f'{res.name} {res.email}')
