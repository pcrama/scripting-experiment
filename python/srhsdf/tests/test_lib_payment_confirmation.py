# -*- coding: utf-8 -*-
import io
from typing import Any
import unittest

import conftest

try:
    import app.lib_payment_confirmation as lib_payment_confirmation
    import app.storage as storage
    import app.htmlgen as htmlgen
except ImportError:
    import sys_path_hack
    with sys_path_hack.app_in_path():
        import lib_payment_confirmation as lib_payment_confirmation
        import storage
        import htmlgen


class _BaseTestCase(unittest.TestCase):
    CONFIGURATION = {'dbdir': ':memory:'}
    USER = "admin_test_user"
    IP = "1.23.4.56"
    output: io.StringIO

    def setUp(self):
        self.output = io.StringIO()

    def setup_reservation_and_payment(self, missing_cents: int = 0, uuid_mismatch: str = "") -> tuple[
            Any, storage.Reservation, storage.Payment]:
        connection = storage.ensure_connection(self.CONFIGURATION)
        with connection:
            reservation = conftest.make_reservation(
                cents_due=2700,
                email="emile@example.com",
                places=1,
                inside_main_starter=1,
                inside_main_dish=1,
                inside_main_dessert=1,
                bank_id='483513812577',
            ).insert_data(connection)
            payment = conftest.make_payment(
                amount_in_cents=reservation.cents_due - missing_cents,
                uuid=reservation.uuid + uuid_mismatch,
                src_id="unit_test_src_id_full_payment",
                bank_ref="unit_test_bank_ref_full_payment",
            ).insert_data(connection)
        return connection, reservation, payment

class TestHtmlDocumentWithMailTemplate(_BaseTestCase):
    def test_generate_email_template_with_reservation_and_payment_mismatch_raises(self):
        connection, reservation, payment = self.setup_reservation_and_payment(uuid_mismatch="xyz")
        self.assertRaises(ValueError,
                          lib_payment_confirmation.html_document_with_mail_template,
                          connection,
                          reservation,
                          payment,
                          {'full_payment_confirmation_template': 'Hello, you paid for your <a href="%reservation_url%">reservation</a>.',
                           'partial_payment_confirmation_template': '',
                           'organizer_name': 'The Organizer',
                           'organizer_bic': 'GEBAGEBA',
                           'bank_account': 'BE00 1234 5678 9012'},
                          "example.com",
                          "/italsdf/gestion/confirm_payment.cgi",
                          self.USER,
                          self.IP,
                          )

    def test_generate_email_template_for_full_payment(self):
        connection, reservation, payment = self.setup_reservation_and_payment()
        for with_prior_csrf_token in (False, True):
            if with_prior_csrf_token:
                existing_token = storage.Csrf.get_by_user_and_ip(connection, self.USER, self.IP)
            else:
                assert storage.Csrf.length(connection) == 0
            with self.subTest(with_prior_csrf_token=with_prior_csrf_token):
                document = lib_payment_confirmation.html_document_with_mail_template(
                    connection,
                    reservation,
                    payment,
                    {'full_payment_confirmation_template': 'Hello, you paid for your <a href="%reservation_url%">reservation</a>.',
                     'partial_payment_confirmation_template': '',
                     'organizer_name': 'The Organizer',
                     'organizer_bic': 'GEBAGEBA',
                     'bank_account': 'BE00 1234 5678 9012'},
                    "example.com",
                    "/italsdf/gestion/confirm_payment.cgi",
                    self.USER,
                    self.IP,
                )
                htmlgen.respond_html(document, file=self.output)
                self.assertEqual(storage.Csrf.length(connection), 1)
                tokens = list(storage.Csrf.select(connection))
                if with_prior_csrf_token:
                    self.assertEqual(tokens[0].token, existing_token.token)
                else:
                    self.assertEqual((tokens[0].user, tokens[0].ip), (self.USER, self.IP))
                result = self.output.getvalue()
                last_pos = result.find("body>")
                for needle in ('<p>To:', '>emile@example.com<', '>Subject:', '>Merci pour votre réservation et votre virement<'):
                    self.assertIn(needle, result)
                    needle_pos = result.find(needle, last_pos)
                    self.assertLess(last_pos, needle_pos)
                    last_pos = needle_pos
                self.assertIn(f'<form method="POST" action="https://example.com/italsdf/gestion/confirm_payment.cgi">', result)
                self.assertIn(f'<input type="hidden" name="csrf_token" value="{tokens[0].token}">', result)
                self.assertIn(f'<input type="hidden" name="bank_ref" value="{payment.bank_ref}">', result)
                self.assertIn(f'Hello, you paid for your <a href="https://example.com/italsdf/show_reservation.cgi?bank_id={reservation.bank_id}&uuid_hex={reservation.uuid}">', result)

    def test_generate_email_template_for_partial_payment(self):
        connection, reservation, payment = self.setup_reservation_and_payment(missing_cents=123)
        for with_prior_csrf_token in (False, True):
            if with_prior_csrf_token:
                existing_token = storage.Csrf.get_by_user_and_ip(connection, self.USER, self.IP)
            else:
                assert storage.Csrf.length(connection) == 0
            with self.subTest(with_prior_csrf_token=with_prior_csrf_token):
                document = lib_payment_confirmation.html_document_with_mail_template(
                    connection,
                    reservation,
                    payment,
                    {'full_payment_confirmation_template': '',
                     'partial_payment_confirmation_template': 'Hello, your payment for <a href="%reservation_url%">your reservation</a> was incomplete and you still owe us %remaining_amount_in_euro%. Please make a bank transfert to %organizer_name% %bank_account% %organizer_bic% %formatted_bank_id%',
                     'organizer_name': 'The <Organizer>',
                     'organizer_bic': 'GEBAGEBA',
                     'bank_account': 'BE00 1234 5678 9012'},
                    "example.com",
                    "/italsdf/gestion/confirm_payment.cgi",
                    self.USER,
                    self.IP,
                )
                htmlgen.respond_html(document, file=self.output)
                self.assertEqual(storage.Csrf.length(connection), 1)
                tokens = list(storage.Csrf.select(connection))
                if with_prior_csrf_token:
                    self.assertEqual(tokens[0].token, existing_token.token)
                else:
                    self.assertEqual((tokens[0].user, tokens[0].ip), (self.USER, self.IP))
                result = self.output.getvalue()
                last_pos = result.find("body>")
                for needle in ('<p>To:', '>emile@example.com<', '>Subject:', '>Merci pour votre réservation et votre virement<'):
                    self.assertIn(needle, result)
                    needle_pos = result.find(needle, last_pos)
                    self.assertLess(last_pos, needle_pos)
                    last_pos = needle_pos
                self.assertIn(f'<form method="POST" action="https://example.com/italsdf/gestion/confirm_payment.cgi">', result)
                self.assertIn(f'<input type="hidden" name="csrf_token" value="{tokens[0].token}">', result)
                self.assertIn(f'<input type="hidden" name="bank_ref" value="{payment.bank_ref}">', result)
                self.assertIn(f'<a href="https://example.com/italsdf/show_reservation.cgi?bank_id={reservation.bank_id}&uuid_hex={reservation.uuid}">', result)
                self.assertIn(' 1.23. ', result)
                self.assertIn('The &lt;Organizer&gt;', result)
                self.assertIn('BE00 1234 5678 9012', result)
                self.assertIn('GEBAGEBA', result)
                self.assertIn('+++483/5138/12577+++', result)


class TestHtmlRedirectAfterUpdatingPayment(_BaseTestCase):
    def run_a_test(self, with_csrf_token: bool) -> tuple[Any, storage.Payment]:
        connection, _, payment = self.setup_reservation_and_payment()
        csrf = storage.Csrf.get_by_user_and_ip(connection, self.USER, self.IP) if with_csrf_token else None
        lib_payment_confirmation.handle_post(
            connection,
            payment,
            "there_is_no_csrf_token_yet" if csrf is None else csrf.token,
            1234678.91,
            "example.com",
            "/italsdf/gestion/confirm_payment.cgi",
            self.USER,
            self.IP,
            self.output
        )

        return connection, payment

    def test_no_csrf_token(self):
        self.assertRaises(KeyError, self.run_a_test, False)

    def test_happy_path(self):
        connection, payment = self.run_a_test(True)

        self.assertEqual(self.output.getvalue(),
                         'Status: 302\nLocation: https://example.com/italsdf/gestion/list_payments.cgi\n\n')
        pmnt = storage.Payment.find_by_bank_ref(connection, payment.bank_ref)
        self.assertEqual(pmnt.confirmation_timestamp, 1234678.91)


if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python3 test_lib_payment_confirmation.py"
# End:
