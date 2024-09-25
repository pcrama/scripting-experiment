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
                ('reservation_url', make_show_reservation_url(
                    reservation.bank_id,
                    reservation.uuid,
                    server_name=server_name,
                    script_name=os.path.dirname(confirm_payment_script_name))),
                ('formatted_bank_id', format_bank_id(reservation.bank_id)),
                ('remaining_amount_in_euro', cents_to_euro(remaining_amount_due_in_cents)),
                ):
        key, val = ((f'%{key}%', html.escape(config[key], quote=False))
                    if isinstance(key, str)
                    else (f'%{key[0]}%', key[1]))
        template = template.replace(key, val)
    email_id = "reservation_email"
    subject_id = "subject_id"
    template_id = "mail_template_id"
    return (*html_document(
        "Mail template to confirm payment",
        (('script',
          ('raw',
           """/** Paste richly formatted text.
 * https://stackoverflow.com/a/77305170
 * @param {string} rich - the text formatted as HTML
 * @param {string} plain - a plain text fallback
 */
async function pasteRich(rich, plain) {
  if (typeof ClipboardItem !== "undefined") {
    // Shiny new Clipboard API, not fully supported in Firefox.
    // https://developer.mozilla.org/en-US/docs/Web/API/Clipboard_API#browser_compatibility
    const html = new Blob([rich], { type: "text/html" });
    const text = new Blob([plain], { type: "text/plain" });
    const data = new ClipboardItem({ "text/html": html, "text/plain": text });
    await navigator.clipboard.write([data]);
  } else {
    // Fallback using the deprecated `document.execCommand`.
    // https://developer.mozilla.org/en-US/docs/Web/API/Document/execCommand#browser_compatibility
    const cb = e => {
      e.clipboardData.setData("text/html", rich);
      e.clipboardData.setData("text/plain", plain);
      e.preventDefault();
    };
    document.addEventListener("copy", cb);
    document.execCommand("copy");
    document.removeEventListener("copy", cb);
  }
}""")),
         ('p',
          'To: ',
          (('span',
            'onclick', f"navigator.clipboard.writeText(document.getElementById('{email_id}').innerText)",
            'id', email_id,
            'style', 'cursor: copy;'),
           reservation.email),
          ('br',),
          'Subject: ',
          (('span', 'onclick', f"navigator.clipboard.writeText(document.getElementById('{subject_id}').innerText)",
            'id', subject_id,
            'style', 'cursor: copy;'),
           'Merci pour votre réservation et votre virement')),
         (('div',
           'onclick', f"pasteRich(document.getElementById('{template_id}').innerHTML, document.getElementById('{template_id}').innerText)",
           'id', template_id,
           'style', 'cursor: copy;'),
          ('raw', template)),
         (('form', 'method', 'POST', 'action', urllib.parse.urljoin(f'https://{server_name}', confirm_payment_script_name)),
          (('input', 'type', 'hidden', 'name', 'csrf_token', 'value', csrf.token),),
          (('input', 'type', 'hidden', 'name', 'bank_ref', 'value', payment.bank_ref),),
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
