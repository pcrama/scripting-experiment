import cgi
import time
from typing import Callable, Optional, Union

from storage import Payment

def get_parameters_for_GET() -> (Optional[str], Optional[int], Optional[int]):
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


def to_jsonable_payment(payment: Payment) -> dict[str, Union[int, float, str]]:
    return {
        "timestamp": payment.timestamp,
        "amount_in_cents": payment.amount_in_cents,
        "comment": payment.comment,
        "rowid": payment.rowid,
    }


def get_payments_data(
        connection,
        max_rows: int,
        filtering: Optional[str],
        offset: Optional[int],
        limit: Optional[int]
) -> dict[str, Union[list[dict[str, Union[int, str]]], str]]:
    filtering = (("comment", filtering),) if filtering else None
    offset = 0 if offset is None else max(offset, 0)
    limit = max_rows if limit is None else max(0, min(limit, max_rows))

    return [to_jsonable_payment(p)
            for p
            in Payment.select(connection, filtering=filtering, limit=limit, offset=offset)]


BANK_STATEMENT_HEADERS = {
    "fr": {'N\xba de s\xe9quence': "src_id",
           'Date d\'ex\xe9cution': "timestamp",
           'Montant': "amount_in_cents",
           'Contrepartie': "other_account",
           'Nom de la contrepartie': "other_name",
           'Statut': "status",
           'Communication': "comment"}}


def make_payment_builder(header_row: list[str]) -> Callable[[list[str, Optional[Payment]]], Payment]:
    col_name_to_idx = {col_name: col_idx for col_idx, col_name in enumerate(header_row)}
    columns = {}
    for lang, mapping in BANK_STATEMENT_HEADERS.items():
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
