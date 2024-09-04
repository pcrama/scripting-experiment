# -*- coding: utf-8 -*-
import unittest

import sys_path_hack

with sys_path_hack.app_in_path():
    import lib_post_reservation
    import storage


# TODO: many more unit tests


class IsTestReservation(unittest.TestCase):
    def test_examples(self):
        for (name, email, expected) in (
                ("test", "yo@ho.com", False),
                ("test", "yo@example.com", True),
                ("Test", "Yo@Example.Com", True),
                ("I am a Test", "Yo@Example.Com", False),
                ("test", "example.com@gmail.com", False),
        ):
            with self.subTest(name=name, email=email):
                self.assertIs(lib_post_reservation.is_test_reservation(name, email), expected)


class NormalizeData(unittest.TestCase):
    def test_full_positional_list(self):
        (civility, first_name, last_name, email, date, paying_seats, free_seats, gdpr_accepts_use) = lib_post_reservation.normalize_data(
             'Mr', 'first_name', 'last_name', 'email', 'date', '2', '3', 'yes')
        self.assertEqual(civility, 'Mr')
        self.assertEqual(first_name, 'first_name')
        self.assertEqual(last_name, 'last_name')
        self.assertEqual(email, 'email')
        self.assertEqual(date, 'date')
        self.assertEqual(paying_seats, 2)
        self.assertEqual(free_seats, 3)
        self.assertIs(gdpr_accepts_use, True)


    def test_string_normalization(self):
        for (string_in, expected) in (
                (" spaces outside are trimmed \t", "spaces outside are trimmed"),
                ("spaces   inside\tare \t normalized", "spaces inside are normalized"),
                (None, ""),
        ):
            with self.subTest(string_in=string_in):
                (civility, first_name, last_name, email, date, _paying_seats, _free_seats, _gdpr_accepts_use) = lib_post_reservation.normalize_data(
                    string_in, string_in, string_in, string_in, string_in, 'paying_seats', 'free_seats', 'gdpr_accepts_use')
                self.assertEqual(civility, '')
                self.assertEqual(first_name, expected)
                self.assertEqual(last_name, expected)
                self.assertEqual(email, expected)
                self.assertEqual(date, expected)


    def test_number_normalization(self):
        for (string_in, expected) in (
                (" rubbish defaults to 0 \t", 0),
                (None, 0),
                ("-3", 0),
                ("0", 0),
                (" 1 ", 1),
                ("49", 49),
                ("50", 50),
                ("451", 50),
        ):
            with self.subTest(string_in=string_in):
                (_civility, _first_name, _last_name, _email, _date, paying_seats, free_seats, _gdpr_accepts_use) = lib_post_reservation.normalize_data(
                     'Mr', 'jean', "name", "email", "date", paying_seats=string_in, free_seats=string_in, gdpr_accepts_use="gdpr_accepts_use")
                self.assertEqual(paying_seats, expected)
                self.assertEqual(free_seats, expected)



class ValidateDate(unittest.TestCase):
    def test_name_and_email_are_mandatory(self):
        for name, email in ((None, "email"), ("", "email"), (" ", "email"), ("name", None), ("name", ""), ("name", " "), (None, None)):
            with self.subTest(name=name, email=email):
                with self.assertRaises(lib_post_reservation.ValidationException):
                    lib_post_reservation.validate_data(
                        'Melle', 'Jo', name, email, 'date', 'paying_seats', 'free_seats',
                        'gdpr_accepts_use', 'connection')


    def test_invalid_email_rejected(self):
        for email in ("a@", "a @b", "a @ b . com", "a@b", "example.com", "bourgmestre@braine-lalleud.be-fr"):
            with self.subTest(email=email):
                with self.assertRaises(lib_post_reservation.ValidationException) as cm:
                    lib_post_reservation.validate_data(
                        'Mr', '', 'name', email, 'date', 'paying_seats', 'free_seats',
                        'gdpr_accepts_use', 'connection')
                message = cm.exception.args[0]
                self.assertTrue("email" in message and "format" in message)


    def test_valid_email_accepted(self):
        configuration = {"dbdir": ":memory:"}
        connection = storage.ensure_connection(configuration)
        for email in ("me-and-you@together.com", "a+test@bcd.az", "bourgmestre@braine-lalleud.be"):
            with self.subTest(email=email):
                lib_post_reservation.validate_data(
                    '', '', 'name', email, '2024-12-01', 3, 0, True, connection)


    def test_date_validation_date_is_OK(self):
        for (name, email, date) in (
                ("Test Name", "test.email@example.com", "2099-01-01"),
                ("Test Name", "test.email@example.com", "2099-01-02"),
                ("Someone", "an.email@gmail.com", "2024-11-30"),
                ("Someone Else", "an.email@gmail.com", "2024-12-01"),
        ):
            with self.subTest(name=name, email=email, date=date), \
                 self.assertRaises(AttributeError) as cm:
                lib_post_reservation.validate_data(
                     civility='Mme', first_name='Jean', last_name=name, email=email, date=date, paying_seats=3,
                     free_seats=0, gdpr_accepts_use=True,
                     connection='connection is not a correct object, so force validation to fail in time')
            message = cm.exception.args[0]
            # If this exact Exception was raised, we got past the date validation
            self.assertEqual(message, "'str' object has no attribute 'execute'")


    def test_date_validation_date_is_not_OK(self):
        for (last_name, email, date) in (
                ("Name", "test.email@gmail.com", "2099-01-01"),
                ("Name", "test.email@gmail.com", "2099-01-02"),
                ("Someone", "an.email@gmail.com", "2023-02-02"),
        ):
            with self.subTest(last_name=last_name, email=email, date=date), \
                 self.assertRaises(lib_post_reservation.ValidationException) as cm:
                lib_post_reservation.validate_data(
                     civility="Mme", first_name="An", last_name=last_name, email=email, date=date, paying_seats=1, free_seats=0, gdpr_accepts_use=True,
                     connection='connection is not a correct object, so force validation to fail in time')
            message = cm.exception.args[0]
            self.assertTrue(message.startswith("Il n'y a pas de concert"))
            self.assertTrue(date in message)


    def test_generate_payment_QR_code_content(self):
        self.assertEqual(
            lib_post_reservation.generate_payment_QR_code_content(
                12045, # cents, i.e. 120.45€
                "483513812577",
                {"organizer_name": "Music and Food", "organizer_bic": "GABBBEBB", "bank_account": "BE89 3751 0478 0085"}),
            "BCD\n001\n1\nSCT\nGABBBEBB\nMusic and Food\nBE89375104780085\nEUR120.45\n\n483513812577",
        )


    def test_save_data_sqlite3(self):
        configuration = {"dbdir": ":memory:"}
        connection = storage.ensure_connection(configuration)

        new_row = lib_post_reservation.save_data_sqlite3(
            civility='Mr', first_name='Fred', last_name='name', email='email@example.com', date='2099-12-31',
            paying_seats=11, free_seats=12,
            gdpr_accepts_use=True, origin='origin', cents_due=1234, connection_or_root_dir=connection)

        self.assertIsNot(new_row, None)
        self.assertEqual(new_row.name, 'Mr Fred name')
        self.assertEqual(new_row.civility, 'Mr')
        self.assertEqual(new_row.first_name, 'Fred')
        self.assertEqual(new_row.last_name, 'name')
        self.assertEqual(new_row.email, 'email@example.com')
        self.assertEqual(new_row.date, '2099-12-31')
        self.assertEqual(new_row.paying_seats, 11)
        self.assertEqual(new_row.free_seats, 12)
        self.assertEqual(new_row.gdpr_accepts_use, True)
        self.assertEqual(new_row.origin, 'origin')

        fetched_row = storage.Reservation.find_by_bank_id(connection, new_row.bank_id)

        self.assertIsNot(fetched_row, None)
        self.assertEqual(new_row.name, 'Mr Fred name')
        self.assertEqual(new_row.civility, 'Mr')
        self.assertEqual(new_row.first_name, 'Fred')
        self.assertEqual(new_row.last_name, 'name')
        self.assertEqual(fetched_row.email, 'email@example.com')
        self.assertEqual(fetched_row.date, '2099-12-31')
        self.assertEqual(fetched_row.paying_seats, 11)
        self.assertEqual(fetched_row.free_seats, 12)
        self.assertEqual(fetched_row.gdpr_accepts_use, True)
        self.assertEqual(fetched_row.origin, 'origin')
        self.assertGreater(fetched_row.cents_due, 0)

        
if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python3 test_lib_post_reservation.py"
# End:
