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
        (name, email, extra_comment, places, date,
         outside_main_starter, outside_extra_starter, outside_bolo, outside_extra_dish, outside_dessert,
         inside_main_starter, inside_extra_starter, inside_bolo, inside_extra_dish,
         kids_bolo, kids_extra_dish,
         gdpr_accepts_use) = lib_post_reservation.normalize_data(
             'name', 'email', 'extra_comment', '1', 'date', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', 'yes')
        self.assertEqual(name, 'name')
        self.assertEqual(email, 'email')
        self.assertEqual(extra_comment, 'extra_comment')
        self.assertEqual(places, 1)
        self.assertEqual(date, 'date')
        self.assertEqual(outside_main_starter, 2)
        self.assertEqual(outside_extra_starter, 3)
        self.assertEqual(outside_bolo, 4)
        self.assertEqual(outside_extra_dish, 5)
        self.assertEqual(outside_dessert, 6)
        self.assertEqual(inside_main_starter, 7)
        self.assertEqual(inside_extra_starter, 8)
        self.assertEqual(inside_bolo, 9)
        self.assertEqual(inside_extra_dish, 10)
        self.assertEqual(kids_bolo, 11)
        self.assertEqual(kids_extra_dish, 12)
        self.assertIs(gdpr_accepts_use, True)


    def test_string_normalization(self):
        for (string_in, expected) in (
                (" spaces outside are trimmed \t", "spaces outside are trimmed"),
                ("spaces   inside\tare \t normalized", "spaces inside are normalized"),
                (None, ""),
        ):
            with self.subTest(string_in=string_in):
                (name, email, extra_comment, places, date,
                 outside_main_starter, outside_extra_starter, outside_bolo, outside_extra_dish, outside_dessert,
                 inside_main_starter, inside_extra_starter, inside_bolo, inside_extra_dish,
                 kids_bolo, kids_extra_dish,
                 gdpr_accepts_use) = lib_post_reservation.normalize_data(
                     string_in, string_in, string_in, 'places', string_in,
                     'outside_main_starter', 'outside_extra_starter', 'outside_bolo', 'outside_extra_dish', 'outside_dessert',
                     'inside_main_starter', 'inside_extra_starter', 'inside_bolo', 'inside_extra_dish',
                     'kids_bolo', 'kids_extra_dish',
                     'gdpr_accepts_use')
                self.assertEqual(name, expected)
                self.assertEqual(email, expected)
                self.assertEqual(extra_comment, expected)
                self.assertEqual(date, date)


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
                (name, email, extra_comment, places, date,
                 outside_main_starter, outside_extra_starter, outside_bolo, outside_extra_dish, outside_dessert,
                 inside_main_starter, inside_extra_starter, inside_bolo, inside_extra_dish,
                 kids_bolo, kids_extra_dish,
                 gdpr_accepts_use) = lib_post_reservation.normalize_data(
                     "name", "email", "extra_comment", places=string_in, date="date",
                     outside_main_starter=string_in, outside_extra_starter=string_in, outside_bolo=string_in,
                     outside_extra_dish=string_in, outside_dessert=string_in,
                     inside_main_starter=string_in, inside_extra_starter=string_in, inside_bolo=string_in,
                     inside_extra_dish=string_in, kids_bolo=string_in, kids_extra_dish=string_in,
                     gdpr_accepts_use="gdpr_accepts_use")
                self.assertEqual(places, expected)
                self.assertEqual(outside_main_starter, expected)
                self.assertEqual(outside_extra_starter, expected)
                self.assertEqual(outside_bolo, expected)
                self.assertEqual(outside_extra_dish, expected)
                self.assertEqual(outside_dessert, expected)
                self.assertEqual(inside_main_starter, expected)
                self.assertEqual(inside_extra_starter, expected)
                self.assertEqual(inside_bolo, expected)
                self.assertEqual(inside_extra_dish, expected)
                self.assertEqual(kids_bolo, expected)
                self.assertEqual(kids_extra_dish, expected)


class ValidateDate(unittest.TestCase):
    def test_name_and_email_are_mandatory(self):
        for name, email in ((None, "email"), ("", "email"), (" ", "email"), ("name", None), ("name", ""), ("name", " "), (None, None)):
            with self.subTest(name=name, email=email):
                with self.assertRaises(lib_post_reservation.ValidationException):
                    lib_post_reservation.validate_data(
                        name, email, 'extra_comment', 'places', 'date',
                        'outside_main_starter', 'outside_extra_starter', 'outside_bolo', 'outside_extra_dish',
                        'outside_dessert', 'inside_main_starter', 'inside_extra_starter', 'inside_bolo',
                        'inside_extra_dish', 'kids_bolo', 'kids_extra_dish',
                        'gdpr_accepts_use', 'connection')


    def test_invalid_email_rejected(self):
        for email in ("a@", "a @b", "a @ b . com", "a@b", "example.com"):
            with self.subTest(email=email):
                with self.assertRaises(lib_post_reservation.ValidationException) as cm:
                    lib_post_reservation.validate_data(
                        'name', email, 'extra_comment', 'places', 'date',
                        'outside_main_starter', 'outside_extra_starter', 'outside_bolo', 'outside_extra_dish',
                        'outside_dessert', 'inside_main_starter', 'inside_extra_starter', 'inside_bolo',
                        'inside_extra_dish', 'kids_bolo', 'kids_extra_dish',
                        'gdpr_accepts_use', 'connection')
                message = cm.exception.args[0]
                self.assertTrue("email" in message and "format" in message)


    def test_date_validation_date_is_OK(self):
        for (name, email, date) in (
                ("Test Name", "test.email@example.com", "2099-01-01"),
                ("Test Name", "test.email@example.com", "2099-01-02"),
                ("Someone", "an.email@gmail.com", "2023-03-25"),
        ):
            with self.subTest(name=name, email=email, date=date), \
                 self.assertRaises(AttributeError) as cm:
                lib_post_reservation.validate_data(
                     name=name, email=email, extra_comment="extra_comment", places=3, date=date,
                     outside_main_starter=0, outside_extra_starter=0, outside_bolo=0, outside_extra_dish=0, outside_dessert=0,
                     inside_main_starter=1, inside_extra_starter=0, inside_bolo=1, inside_extra_dish=0,
                     kids_bolo=1, kids_extra_dish=0,
                     gdpr_accepts_use=True,
                     connection='connection is not a correct object, so force validation to fail in time')
            message = cm.exception.args[0]
            # If this exact Exception was raised, we got past the date validation
            self.assertEqual(message, "'str' object has no attribute 'execute'")


    def test_date_validation_date_is_not_OK(self):
        for (name, email, date) in (
                ("Name", "test.email@gmail.com", "2099-01-01"),
                ("Name", "test.email@gmail.com", "2099-01-02"),
                ("Someone", "an.email@gmail.com", "2023-02-02"),
        ):
            with self.subTest(name=name, email=email, date=date), \
                 self.assertRaises(lib_post_reservation.ValidationException) as cm:
                lib_post_reservation.validate_data(
                     name=name, email=email, extra_comment="extra_comment", places=3, date=date,
                     outside_main_starter=0, outside_extra_starter=0, outside_bolo=0, outside_extra_dish=0, outside_dessert=0,
                     inside_main_starter=1, inside_extra_starter=3, inside_bolo=1, inside_extra_dish=0,
                     kids_bolo=1, kids_extra_dish=0,
                     gdpr_accepts_use=True,
                     connection='connection is not a correct object, so force validation to fail in time')
            message = cm.exception.args[0]
            self.assertTrue(message.startswith("Il n'y a pas de repas italien"))
            self.assertTrue(date in message)


    def test_generate_payment_QR_code_content(self):
        self.assertEqual(
            lib_post_reservation.generate_payment_QR_code_content(
                12045, # cents, i.e. 120.45€
                "483513812577",
                {"organizer_name": "Music and Food", "organizer_bic": "GABBBEBB", "bank_account": "BE89 3751 0478 0085"}),
            "BCD\n001\n1\nSCT\nGABBBEBB\nMusic and Food\nBE89375104780085\nEUR120.45\n483513812577\n483513812577",
        )


if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python3 test_lib_post_reservation.py"
# End:
