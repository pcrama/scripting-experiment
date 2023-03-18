import cgi
from typing import Optional, Union

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


def to_jsonable_payment(payment):
    return {
        "timestamp": payment.timestamp,
        "amount_in_cents": payment.amount_in_cents,
        "comment": payment.comment,
        "id": payment.id,
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
