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
         outside_main_starter, outside_extra_starter, outside_main_dish, outside_extra_dish, outside_third_dish, outside_main_dessert, outside_extra_dessert,
         inside_main_starter, inside_extra_starter, inside_main_dish, inside_extra_dish, inside_third_dish, inside_main_dessert, inside_extra_dessert,
         kids_main_dish, kids_extra_dish, kids_third_dish, kids_main_dessert, kids_extra_dessert,
         gdpr_accepts_use) = lib_post_reservation.normalize_data(
             'name', 'email', 'extra_comment', '1', 'date', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', 'yes')
        self.assertEqual(name, 'name')
        self.assertEqual(email, 'email')
        self.assertEqual(extra_comment, 'extra_comment')
        self.assertEqual(places, 1)
        self.assertEqual(date, 'date')
        self.assertEqual(outside_main_starter, 2)
        self.assertEqual(outside_extra_starter, 3)
        self.assertEqual(outside_main_dish, 4)
        self.assertEqual(outside_extra_dish, 5)
        self.assertEqual(outside_third_dish, 6)
        self.assertEqual(outside_main_dessert, 7)
        self.assertEqual(outside_extra_dessert, 8)
        self.assertEqual(inside_main_starter, 9)
        self.assertEqual(inside_extra_starter, 10)
        self.assertEqual(inside_main_dish, 11)
        self.assertEqual(inside_extra_dish, 12)
        self.assertEqual(inside_third_dish, 13)
        self.assertEqual(inside_main_dessert, 14)
        self.assertEqual(inside_extra_dessert, 15)
        self.assertEqual(kids_main_dish, 16)
        self.assertEqual(kids_extra_dish, 17)
        self.assertEqual(kids_third_dish, 18)
        self.assertEqual(kids_main_dessert, 19)
        self.assertEqual(kids_extra_dessert, 20)
        self.assertIs(gdpr_accepts_use, True)


    def test_string_normalization(self):
        for (string_in, expected) in (
                (" spaces outside are trimmed \t", "spaces outside are trimmed"),
                ("spaces   inside\tare \t normalized", "spaces inside are normalized"),
                (None, ""),
        ):
            with self.subTest(string_in=string_in):
                (name, email, extra_comment, places, date,
                 outside_main_starter, outside_extra_starter, outside_main_dish, outside_extra_dish, outside_third_dish, outside_main_dessert, outside_extra_dessert,
                 inside_main_starter, inside_extra_starter, inside_main_dish, inside_extra_dish, inside_third_dish, inside_main_dessert, inside_extra_dessert,
                 kids_main_dish, kids_extra_dish, kids_third_dish, kids_main_dessert, kids_extra_dessert,
                 gdpr_accepts_use) = lib_post_reservation.normalize_data(
                     string_in, string_in, string_in, 'places', string_in,
                     'outside_main_starter', 'outside_extra_starter', 'outside_main_dish', 'outside_extra_dish', 'outside_third_dish', 'outside_main_dessert', 'outside_extra_dessert',
                     'inside_main_starter', 'inside_extra_starter', 'inside_main_dish', 'inside_extra_dish', 'inside_third_dish', 'inside_main_dessert', 'inside_extra_dessert',
                     'kids_main_dish', 'kids_extra_dish', 'kids_third_dish', 'kids_main_dessert', 'kids_extra_dessert',
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
                 outside_main_starter, outside_extra_starter, outside_main_dish, outside_extra_dish, outside_third_dish, outside_main_dessert, outside_extra_dessert,
                 inside_main_starter, inside_extra_starter, inside_main_dish, inside_extra_dish, inside_third_dish, inside_main_dessert, inside_extra_dessert,
                 kids_main_dish, kids_extra_dish, kids_third_dish, kids_main_dessert, kids_extra_dessert,
                 gdpr_accepts_use) = lib_post_reservation.normalize_data(
                     "name", "email", "extra_comment", places=string_in, date="date",
                     outside_main_starter=string_in, outside_extra_starter=string_in, outside_main_dish=string_in, outside_extra_dish=string_in, outside_third_dish=string_in, outside_main_dessert=string_in, outside_extra_dessert=string_in,
                     inside_main_starter=string_in, inside_extra_starter=string_in, inside_main_dish=string_in, inside_extra_dish=string_in, inside_third_dish=string_in, inside_main_dessert=string_in, inside_extra_dessert=string_in,
                     kids_main_dish=string_in, kids_extra_dish=string_in, kids_third_dish=string_in, kids_main_dessert=string_in, kids_extra_dessert=string_in,
                     gdpr_accepts_use="gdpr_accepts_use")
                self.assertEqual(places, expected)
                self.assertEqual(outside_main_starter, expected)
                self.assertEqual(outside_extra_starter, expected)
                self.assertEqual(outside_main_dish, expected)
                self.assertEqual(outside_extra_dish, expected)
                self.assertEqual(outside_third_dish, expected)
                self.assertEqual(outside_main_dessert, expected)
                self.assertEqual(outside_extra_dessert, expected)
                self.assertEqual(inside_main_starter, expected)
                self.assertEqual(inside_extra_starter, expected)
                self.assertEqual(inside_main_dish, expected)
                self.assertEqual(inside_extra_dish, expected)
                self.assertEqual(inside_third_dish, expected)
                self.assertEqual(inside_main_dessert, expected)
                self.assertEqual(inside_extra_dessert, expected)
                self.assertEqual(kids_main_dish, expected)
                self.assertEqual(kids_extra_dish, expected)
                self.assertEqual(kids_third_dish, expected)
                self.assertEqual(kids_main_dessert, expected)
                self.assertEqual(kids_extra_dessert, expected)



class ValidateDate(unittest.TestCase):
    def test_name_and_email_are_mandatory(self):
        for name, email in ((None, "email"), ("", "email"), (" ", "email"), ("name", None), ("name", ""), ("name", " "), (None, None)):
            with self.subTest(name=name, email=email):
                with self.assertRaises(lib_post_reservation.ValidationException):
                    lib_post_reservation.validate_data(
                        name, email, 'extra_comment', 'places', 'date',
                        'outside_main_starter', 'outside_extra_starter', 'outside_main_dish', 'outside_extra_dish', 'outside_third_dish', 'outside_main_dessert', 'outside_extra_dessert',
                        'inside_main_starter', 'inside_extra_starter', 'inside_main_dish', 'inside_extra_dish', 'inside_third_dish', 'inside_main_dessert', 'inside_extra_dessert',
                        'kids_main_dish', 'kids_extra_dish', 'kids_third_dish', 'kids_main_dessert', 'kids_extra_dessert',
                        'gdpr_accepts_use', 'connection')


    def test_invalid_email_rejected(self):
        for email in ("a@", "a @b", "a @ b . com", "a@b", "example.com"):
            with self.subTest(email=email):
                with self.assertRaises(lib_post_reservation.ValidationException) as cm:
                    lib_post_reservation.validate_data(
                        'name', email, 'extra_comment', 'places', 'date',
                        'outside_main_starter', 'outside_extra_starter', 'outside_main_dish', 'outside_extra_dish', 'outside_third_dish', 'outside_main_dessert', 'outside_extra_dessert',
                        'inside_main_starter', 'inside_extra_starter', 'inside_main_dish', 'inside_extra_dish', 'inside_third_dish', 'inside_main_dessert', 'inside_extra_dessert',
                        'kids_main_dish', 'kids_extra_dish', 'kids_third_dish', 'kids_main_dessert', 'kids_extra_dessert',
                        'gdpr_accepts_use', 'connection')
                message = cm.exception.args[0]
                self.assertTrue("email" in message and "format" in message)


    def test_date_validation_date_is_OK(self):
        for (name, email, date) in (
                ("Test Name", "test.email@example.com", "2099-01-01"),
                ("Test Name", "test.email@example.com", "2099-01-02"),
                ("Someone", "an.email@gmail.com", "2024-03-23"),
        ):
            with self.subTest(name=name, email=email, date=date), \
                 self.assertRaises(AttributeError) as cm:
                lib_post_reservation.validate_data(
                     name=name, email=email, extra_comment="extra_comment", places=3, date=date,
                     outside_main_starter=0, outside_extra_starter=0, outside_main_dish=0, outside_extra_dish=0, outside_third_dish=0, outside_main_dessert=0, outside_extra_dessert=0,
                     inside_main_starter=1, inside_extra_starter=0, inside_main_dish=1, inside_extra_dish=0, inside_third_dish=0, inside_main_dessert=1, inside_extra_dessert=0,
                     kids_main_dish=1, kids_extra_dish=0, kids_third_dish=0, kids_main_dessert=0, kids_extra_dessert=1,
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
                     outside_main_starter=0, outside_extra_starter=0, outside_main_dish=0, outside_extra_dish=0, outside_third_dish=0, outside_main_dessert=0, outside_extra_dessert=0,
                     inside_main_starter=1, inside_extra_starter=0, inside_main_dish=1, inside_extra_dish=0, inside_third_dish=0, inside_main_dessert=1, inside_extra_dessert=0,
                     kids_main_dish=1, kids_extra_dish=0, kids_third_dish=0, kids_main_dessert=0, kids_extra_dessert=1,
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


    def test_save_data_sqlite3(self):
        configuration = {"dbdir": ":memory:"}
        connection = storage.ensure_connection(configuration)

        new_row = lib_post_reservation.save_data_sqlite3(
            name='name', email='email@example.com', extra_comment='extra_comment', places=1, date='2099-12-31',
            outside_main_starter=11, outside_extra_starter=12, outside_main_dish=13, outside_extra_dish=14, outside_third_dish=15, outside_main_dessert=24, outside_extra_dessert=25,
            inside_main_starter=20, inside_extra_starter=1, inside_main_dish=16, inside_extra_dish=2, inside_third_dish=3, inside_main_dessert=17, inside_extra_dessert=4,
            kids_main_dish=7, kids_extra_dish=5, kids_third_dish=6, kids_main_dessert=8, kids_extra_dessert=10,
            gdpr_accepts_use=True, origin='origin', connection_or_root_dir=connection)

        self.assertIsNot(new_row, None)
        self.assertEqual(new_row.name, 'name')
        self.assertEqual(new_row.email, 'email@example.com')
        self.assertEqual(new_row.extra_comment, 'extra_comment')
        self.assertEqual(new_row.places, 1)
        self.assertEqual(new_row.date, '2099-12-31')
        self.assertEqual(new_row.outside.main_starter, 11)
        self.assertEqual(new_row.outside.extra_starter, 12)
        self.assertEqual(new_row.outside.main_dish, 13)
        self.assertEqual(new_row.outside.extra_dish, 14)
        self.assertEqual(new_row.outside.third_dish, 15)
        self.assertEqual(new_row.outside.main_dessert, 24)
        self.assertEqual(new_row.outside.extra_dessert, 25)
        self.assertEqual(new_row.inside.main_starter, 20)
        self.assertEqual(new_row.inside.extra_starter, 1)
        self.assertEqual(new_row.inside.main_dish, 16)
        self.assertEqual(new_row.inside.extra_dish, 2)
        self.assertEqual(new_row.inside.third_dish, 3)
        self.assertEqual(new_row.inside.main_dessert, 17)
        self.assertEqual(new_row.inside.extra_dessert, 4)
        self.assertEqual(new_row.kids.main_dish, 7)
        self.assertEqual(new_row.kids.extra_dish, 5)
        self.assertEqual(new_row.kids.third_dish, 6)
        self.assertEqual(new_row.kids.main_dessert, 8)
        self.assertEqual(new_row.kids.extra_dessert, 10)
        self.assertEqual(new_row.gdpr_accepts_use, True)
        self.assertEqual(new_row.origin, 'origin')

        fetched_row = storage.Reservation.find_by_bank_id(connection, new_row.bank_id)

        self.assertIsNot(fetched_row, None)
        self.assertEqual(fetched_row.name, 'name')
        self.assertEqual(fetched_row.email, 'email@example.com')
        self.assertEqual(fetched_row.extra_comment, 'extra_comment')
        self.assertEqual(fetched_row.places, 1)
        self.assertEqual(fetched_row.date, '2099-12-31')
        self.assertEqual(fetched_row.outside.main_starter, 11)
        self.assertEqual(fetched_row.outside.extra_starter, 12)
        self.assertEqual(fetched_row.outside.main_dish, 13)
        self.assertEqual(fetched_row.outside.extra_dish, 14)
        self.assertEqual(fetched_row.outside.third_dish, 15)
        self.assertEqual(fetched_row.outside.main_dessert, 24)
        self.assertEqual(fetched_row.outside.extra_dessert, 25)
        self.assertEqual(fetched_row.inside.main_starter, 20)
        self.assertEqual(fetched_row.inside.extra_starter, 1)
        self.assertEqual(fetched_row.inside.main_dish, 16)
        self.assertEqual(fetched_row.inside.extra_dish, 2)
        self.assertEqual(fetched_row.inside.third_dish, 3)
        self.assertEqual(fetched_row.inside.main_dessert, 17)
        self.assertEqual(fetched_row.inside.extra_dessert, 4)
        self.assertEqual(fetched_row.kids.main_dish, 7)
        self.assertEqual(fetched_row.kids.extra_dish, 5)
        self.assertEqual(fetched_row.kids.third_dish, 6)
        self.assertEqual(fetched_row.kids.main_dessert, 8)
        self.assertEqual(fetched_row.kids.extra_dessert, 10)
        self.assertEqual(fetched_row.gdpr_accepts_use, True)
        self.assertEqual(fetched_row.origin, 'origin')
        self.assertGreater(fetched_row.cents_due, 0)

        
if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python3 test_lib_post_reservation.py"
# End:
