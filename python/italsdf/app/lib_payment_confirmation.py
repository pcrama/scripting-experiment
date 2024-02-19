import html
import os
from typing import Any
import urllib.parse

from storage import Csrf, Payment, Reservation
from htmlgen import (
    cents_to_euro,
    format_bank_id,
    html_document,
    redirect,
)
from lib_post_reservation import (
    make_show_reservation_url
)

def html_document_with_mail_template(connection, reservation: Reservation, payment: Payment, config: dict[str, Any], server_name: str, confirm_payment_script_name: str, user: str, ip: str) -> tuple:
    if reservation.uuid != payment.uuid:
        raise ValueError("Can't send confirmation email for this reservation")
    csrf = Csrf.get_by_user_and_ip(connection, user, ip)
    remaining_amount_due_in_cents = reservation.remaining_amount_due_in_cents(connection)
    if remaining_amount_due_in_cents <= 0:
        template = config["full_payment_confirmation_template"]
    else:
        template = config["partial_payment_confirmation_template"]
    for key in ("organizer_name",
                "organizer_bic",
                'bank_account',
                ('reservation_url', make_show_reservation_url(reservation.uuid,
                                      server_name=server_name,
                                      script_name=os.path.dirname(confirm_payment_script_name))),
                ('formatted_bank_id', format_bank_id(reservation.bank_id)),
                ('remaining_amount_in_euro', cents_to_euro(remaining_amount_due_in_cents)),
                ):
        key, val = ((f'%{key}%', html.escape(config[key], quote=False))
                    if isinstance(key, str)
                    else (f'%{key[0]}%', key[1]))
        template = template.replace(key, val)
    return (*html_document(
        "Mail template to confirm payment",
        (('p',
          'To: ',
          reservation.email,
          ('br',),
          'Subject: Merci pour votre réservation et votre virement'),
         ('raw', template),
         (('form', 'method', 'POST', 'action', urllib.parse.urljoin(f'https://{server_name}', confirm_payment_script_name)),
          (('input', 'type', 'hidden', 'name', 'csrf_token', 'value', csrf.token),),
          (('input', 'type', 'hidden', 'name', 'src_id', 'value', payment.src_id),),
          (('input', 'type', 'submit', 'value', 'Email was sent'),))),),)


def handle_post(connection, payment: Payment, csrf_token: str, now: float, server_name: str, confirm_payment_script_name: str, user: str, ip: str, file=None) -> None:
    Csrf.validate_and_update(connection, csrf_token, user, ip)
    with connection:
        payment.update_confirmation_timestamp(connection, now)
    redirect(
        urllib.parse.urljoin(f'https://{server_name}',
                             os.path.join(
                                 os.path.dirname(confirm_payment_script_name), 'list_payments.cgi')),
        and_exit=False,
        file=file)
