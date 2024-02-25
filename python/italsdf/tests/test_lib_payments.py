# -*- coding: utf-8 -*-
import time
import unittest
from unittest.mock import patch

import conftest

try:
    import app.lib_payments as lib_payments
    import app.storage as storage
except ImportError:
    import sys_path_hack
    with sys_path_hack.app_in_path():
        import lib_payments
        import storage


YEAR_PREFIX = time.strftime("%Y")

class GetParametersParsing(unittest.TestCase):
    def test_examples(self):
        for (cgi_parse, expected_filter, expected_offset, expected_limit) in (
                ({}, None, None, None),
                ({"filtering": "abc"}, "abc", None, None),
                ({"filtering": "def", "offset": "3"}, "def", 3, None),
                ({"filtering": "ghilkj", "offset": "0", "limit": "8"}, "ghilkj", 0, 8,),
                ({"fubar": "mno", "offset": "7", "limit": "-11"}, None, 7, -11),
                ({"offset": "-2"}, None, -2, None),
                ({"limit": "9"}, None, None, 9),
                ({"offset": "two", "limit": "22"}, None, None, 22),
                ({"offset": "33", "limit": "three"}, None, 33, None),
        ):
            with self.subTest(
                    cgi_parse=cgi_parse,
                    expected=(expected_filter, expected_offset, expected_limit)
            ), patch("cgi.parse") as patched_cgi_parse:
                patched_cgi_parse.return_value = cgi_parse
                filtering, offset, limit = lib_payments.get_parameters_for_GET()
                self.assertEqual(filtering, expected_filter)
                self.assertEqual(offset, expected_offset)
                self.assertEqual(limit, expected_limit)


class MakePaymentBuilder(unittest.TestCase):
    EXAMPLE_DATA = [
        ['Nº de séquence', "Date d'exécution", 'Date valeur', 'Montant', 'Devise du compte', 'Numéro de compte', 'Type de transaction', 'Contrepartie', 'Nom de la contrepartie', 'Communication', 'Détails', 'Statut', 'Motif du refus'],
        [f'{YEAR_PREFIX}-00127', '28/03/2023', '28/03/2023', '18', 'EUR', 'BE00010001000101', 'Virement en euros', 'BE00020002000202', 'ccccc-ccccccccc', 'Reprise marchandises (viande hachee) souper italien', 'VIREMENT EN EUROS DU COMPTE BE00020002000202 BIC GABBBEBB CCCCC-CCCCCCCCC AV DE LA GARE 76 9999 WAGADOUGOU COMMUNICATION : REPRISE MARCHANDISES (VIANDE HACHEE) SOUPER ITALIEN REFERENCE BANQUE : 23032412000 DATE VALEUR : 28/03/2023', 'Accepté', ''],
        [f'{YEAR_PREFIX}-00126', '26/02/2023', '26/02/2023', '-50.34', 'EUR', 'BE00010001000101', 'Virement en euros', 'BE00030003000303', 'HHHHHHH SSSSSSSS', 'Cotisation', 'VIREMENT EN EUROS DU COMPTE BE00030003000303 BIC GABBBEBB HHHHHHH SSSSSSSS CHEMIN DE LA GARE 123 9999 WAGADOUGOU COMMUNICATION : COTISATION REFERENCE BANQUE : 23032409001 DATE VALEUR : 26/02/2023', 'Accepté', ''],
    ]
    def test_examples(self):
        proto = storage.Payment(rowid=1,
                                timestamp=2.5,
                                amount_in_cents=3,
                                comment="unit test comment",
                                uuid="c0ffee00beef1234",
                                src_id=f"{YEAR_PREFIX}-1000",
                                other_account="BE0101",
                                other_name="Ms Abc",
                                status="Accepté",
                                user="unit-test-user",
                                ip="1.2.3.4",
                                confirmation_timestamp=None,
                                active=False)

        def sub_test(data_row, with_proto, byte_order_mark, expected_dict):
            builder = lib_payments.make_payment_builder(
                [byte_order_mark + self.EXAMPLE_DATA[0][0]] + self.EXAMPLE_DATA[0][1:])
            with self.subTest(data_row=data_row, with_proto=with_proto, byte_order_mark=byte_order_mark):
                self.assertEqual(
                    builder(self.EXAMPLE_DATA[data_row + 1], proto if with_proto else None).to_dict(),
                    expected_dict)

        sub_test(0, False, '', { 'rowid': None,
                                 'timestamp': 1679997600.0,
                                 'confirmation_timestamp': None,
                                 'amount_in_cents': 1800,
                                 'comment': 'Reprise marchandises (viande hachee) souper italien',
                                 'uuid': None,
                                 'src_id': f'{YEAR_PREFIX}-00127',
                                 'other_account': 'BE00020002000202',
                                 'other_name': 'ccccc-ccccccccc',
                                 'status': 'Accepté',
                                 'active': True,
                                 'user': None,
                                 'ip': None})
        sub_test(0, True, '\ufeff', { 'rowid': None,
                                      'timestamp': 1679997600.0,
                                      'confirmation_timestamp': None,
                                      'amount_in_cents': 1800,
                                      'comment': 'Reprise marchandises (viande hachee) souper italien',
                                      'uuid': None,
                                      'src_id': f'{YEAR_PREFIX}-00127',
                                      'other_account': 'BE00020002000202',
                                      'other_name': 'ccccc-ccccccccc',
                                      'status': 'Accepté',
                                      'active': False,
                                      'user': "unit-test-user",
                                      'ip': "1.2.3.4"})
        sub_test(1, False, '', { 'rowid': None,
                                 'timestamp': 1677409200.0,
                                 'confirmation_timestamp': None,
                                 'amount_in_cents': -5034,
                                 'comment': 'Cotisation',
                                 'uuid': None,
                                 'src_id': f'{YEAR_PREFIX}-00126',
                                 'other_account': 'BE00030003000303',
                                 'other_name': 'HHHHHHH SSSSSSSS',
                                 'status': 'Accepté',
                                 'active': True,
                                 'user': None,
                                 'ip': None})


class ImportBankStatements(unittest.TestCase):
    bank_statements_csv = [
        "Nº de séquence;Date d'exécution;Date valeur;Montant;Devise du compte;Numéro de compte;Type de transaction;Contrepartie;Nom de la contrepartie;Communication;Détails;Statut;Motif du refus",
        f"{YEAR_PREFIX}-00127;28/03/2023;28/03/2023;18;EUR;BE00010001000101;Virement en euros;BE00020002000202;ccccc-ccccccccc;Reprise marchandises (viande hachee) souper italien;VIREMENT EN EUROS DU COMPTE BE00020002000202 BIC GABBBEBB CCCCC-CCCCCCCCC AV DE LA GARE 76 9999 WAGADOUGOU COMMUNICATION : REPRISE MARCHANDISES (VIANDE HACHEE) SOUPER ITALIEN REFERENCE BANQUE : 23032412002 DATE VALEUR : 28/03/2023;Accepté;",
        f"{YEAR_PREFIX}-00126;28/03/2023;28/03/2023;50;EUR;BE00010001000101;Virement en euros;BE00030003000303;HHHHHHH SSSSSSSS;Cotisation;VIREMENT EN EUROS DU COMPTE BE00030003000303 BIC GABBBEBB HHHHHHH SSSSSSSS CHEMIN DE LA GARE 123 9999 WAGADOUGOU COMMUNICATION : COTISATION REFERENCE BANQUE : 23032409003 DATE VALEUR : 28/03/2023;Accepté;",
        f"{YEAR_PREFIX}-00125;28/03/2023;28/03/2023;54;EUR;BE00010001000101;Virement en euros;BE00040004000404;Mme RRRRRRRRRR GGGGG;Souper italien du 25/03 : 2 x 27;VIREMENT EN EUROS DU COMPTE BE00 0400 0400 0404 BIC GABBBEBB MME RRRRRRRRRR GGGGG RUE DE LA GARE;3 3333 ZANZIBAR COMMUNICATION : SOUPER ITALIEN DU 25/03 : 2 X 27 REFERENCE BANQUE : 23032406004 DATE VALEUR : 28/03/2023;Accepté",
        f"{YEAR_PREFIX}-00124;27/03/2023;27/03/2023;-54;EUR;BE00010001000101;Virement en euros;BE00050005000505;Aaa Bbbbbbbb;Remboursement repas italien Harmonie ( pas venu);VIREMENT EN EUROS AU COMPTE BE00 0500 0500 0505 BIC GABBBEBB VIA MOBILE BANKING AAA BBBBBBBB COMMUNICATION : REMBOURSEMENT REPAS ITALIEN HARMONIE ( PAS VENU) BISES ANDRE REFERENCE BANQUE : 23032430005 DATE VALEUR : 27/03/2023;Accepté;",
        f"{YEAR_PREFIX}-00123;27/03/2023;27/03/2023;15;EUR;BE00010001000101;Paiement par carte;BE060006000606;BANKSYS;068962070000270121363927012136391010271908660328072700000620700000000088000000000000000P2P MOBILE 000;PAIEMENT MOBILE COMPTE DU DONNEUR D'ORDRE : BE06 0006 0006 06 BIC GABBBEBB BANCONTACT REFERENCE BANQUE : 23032427006 DATE VALEUR : 27/03/2023;Accepté;",
        f"{YEAR_PREFIX}-00122;27/03/2023;27/03/2023;57;EUR;BE00010001000101;Virement en euros;BE070007000707;OOOOO QQQQQ;;VIREMENT EN EUROS DU COMPTE BE07 0007 0007 07 BIC GABBBEBB OOOOO QQQQQ CHAUSSEE DE LA GARE 5 1440 6666 PORT-AU-BOUC PAS DE COMMUNICATION REFERENCE BANQUE : 23032424007 DATE VALEUR : 27/03/2023;Accepté;",
        f"{YEAR_PREFIX}-00121;27/03/2023;27/03/2023;60;EUR;BE00010001000101;Virement instantané en euros;BE080008000808;EEEEEEE JJJJJJ;Cotisation Eeeeeee - Jjjjjj;VIREMENT INSTANTANE EN EUROS BE08 0008 0008 08 BIC GABBBEBBXXX EEEEEEE JJJJJJ RUE DE LA MARIEE 50 7777 NEW YORK COMMUNICATION : COTISATION EEEEEEE - JJJJJJ REFERENCE BANQUE : 23032448008 DATE VALEUR : 27/03/2023;Accepté;",
        f"{YEAR_PREFIX}-00120;26/03/2023;26/03/2023;25;EUR;BE00010001000101;Virement instantané en euros;BE090009000909;DDDDDDD VVVVVVVVVVVVVVVVV;Llll Aaaa cotisation;VIREMENT INSTANTANE EN EUROS BE09 0009 0009 09 BIC GABBBEBBXXX DDDDDDD VVVVVVVVVVVVVVVVV RUE DES MIETTES 32 6666 HYDERABAD COMMUNICATION : LLLL AAAA COTISATION REFERENCE BANQUE : 23032445009 DATE VALEUR : 26/03/2023;Accepté;",
        f"{YEAR_PREFIX}-00119;25/03/2023;24/03/2023;27;EUR;BE00010001000101;Virement instantané en euros;BE100010001010;SSSSSS GGGGGGGG;+++671/4235/58049+++;VIREMENT INSTANTANE EN EUROS BE10 0010 0010 10 BIC GABBBEBBXXX SSSSSS GGGGGGGG RUE MARIGNON 43/5 8888 BANDARLOG COMMUNICATION : 671423558049 EXECUTE LE 24/03 REFERENCE BANQUE : 23032442010 DATE VALEUR : 24/03/2023;Accepté;",
        f"{YEAR_PREFIX}-00118;24/03/2023;23/03/2023;16;EUR;BE00010001000101;Virement en euros;BE110011001111;WWWWWWW XXXXXXXX;+++402/9754/33613+++;VIREMENT EN EUROS DU COMPTE BE11 0011 0011 11 BIC GABBBEBB WWWWWWW XXXXXXXX CLOS DE LA GARE 30 8888 BANDARLOG COMMUNICATION : 402975433613 REFERENCE BANQUE : 23032439011 DATE VALEUR : 23/03/2023;Accepté;",
        f"{YEAR_PREFIX}-00117;24/03/2023;24/03/2023;81;EUR;BE00010001000101;Virement en euros;BE202020202020;JAJAJA-BLBLBLBL;+++483/5138/12577+++;VIREMENT EN EUROS DU COMPTE BE20 0013 0492 7256 BIC GABBBEBB JAJAJA-BLBLBLBL AV. DE L'EGLISE 41 8888 BANDARLOG COMMUNICATION : 483513812577 REFERENCE BANQUE : 23032463012 DATE VALEUR : 24/03/2023;Accepté;",
        f"{YEAR_PREFIX}-00116;23/03/2023;23/03/2023;-33.6;EUR;BE00010001000101;Paiement par carte;;;;PAIEMENT AVEC LA CARTE DE DEBIT NUMERO 4871 09XX XXXX 7079 GROENDEKOR BVBA SINT-PIET 23/03/2023 BANCONTACT REFERENCE BANQUE : 23032460013 DATE VALEUR : 23/03/2023;Accepté;",
        f"{YEAR_PREFIX}-00115;23/03/2023;22/03/2023;16;EUR;BE00010001000101;Virement en euros;BE110011001111;WWWWWWW XXXXXXXX;+++476/7706/09825+++;VIREMENT EN EUROS DU COMPTE BE11 0011 0011 11 BIC GABBBEBB WWWWWWW XXXXXXXX CLOS DE LA GARE 30 8888 BANDARLOG COMMUNICATION : 476770609825 REFERENCE BANQUE : 23032457014 DATE VALEUR : 22/03/2023;Accepté;",
        f"{YEAR_PREFIX}-00114;23/03/2023;23/03/2023;54;EUR;BE00010001000101;Virement en euros;BE120012001212;Ggggggggggg Gggggg;852598350718;VIREMENT EN EUROS DU COMPTE BE12 0012 0012 12 BIC GABBBEBB GGGGGGGGGGG GGGGGG PLACE DE LA GARE 12 8888 BANDARLOG COMMUNICATION : 852598350718 REFERENCE BANQUE : 23032454015 DATE VALEUR : 23/03/2023;Accepté;",
        f"{YEAR_PREFIX}-00113;22/03/2023;22/03/2023;-100.87;EUR;BE00010001000101;Virement en euros;BE89375104780085;Unisono;+++323/0086/13607+++;VIREMENT EN EUROS AU COMPTE BE89 3751 0478 0085 BIC GABBBEBB VIA MOBILE BANKING UNISONO COMMUNICATION : 323008613607 REFERENCE BANQUE : 23032478016 DATE VALEUR : 22/03/2023;Accepté;",
        f"{YEAR_PREFIX}-00112;22/03/2023;21/03/2023;25;EUR;BE00010001000101;Virement en euros;BE130013001313;DEDEDEDE DEDED;Cotisation SRH;VIREMENT EN EUROS DU COMPTE BE13 0013 0013 13 BIC GABBBEBB DEDEDEDE DEDED RUE DE L'EGLISE 33 6666 PORT-AU-BOUC COMMUNICATION : COTISATION SRH REFERENCE BANQUE : 23032475017 DATE VALEUR : 21/03/2023;Accepté;",
        f"{YEAR_PREFIX}-00111;22/03/2023;22/03/2023;27;EUR;BE00010001000101;Virement en euros;BE140014001414;SOSOSOS OSOSOS;+++409/5503/55816+++;VIREMENT EN EUROS DU COMPTE BE14 0014 0014 14 BIC GABBBEBB SOSOSOS OSOSOS RUE DES APACHES 42 5555 ZOLLIKON COMMUNICATION : 409550355816 REFERENCE BANQUE : 23032472018 DATE VALEUR : 22/03/2023;Accepté;",
        f"{YEAR_PREFIX}-00110;22/03/2023;22/03/2023;54;EUR;BE00010001000101;Virement en euros;BE150015001515;Iaiaiaiaia Iaia;483421245780;VIREMENT EN EUROS DU COMPTE BE15 0015 0015 15 BIC GABBBEBB IAIAIAIAIA IAIA BOULEVARD DE LA GARE 67 4444 MODANE COMMUNICATION : 483421245780 REFERENCE BANQUE : 23032496019 DATE VALEUR : 22/03/2023;Accepté;",
        f"{YEAR_PREFIX}-00109;21/03/2023;21/03/2023;81;EUR;BE00010001000101;Virement en euros;BE160016001616;SCSCSCSC-XSXSXSXS;+++409/6346/26382+++;VIREMENT EN EUROS DU COMPTE BE16 0016 0016 16 BIC GABBBEBB SCSCSCSC-XSXSXSXS RUE DU PORT 23 8888 BANDARLOG COMMUNICATION : 409634626382 REFERENCE BANQUE : 23032493020 DATE VALEUR : 21/03/2023;Accepté;",
        f"{YEAR_PREFIX}-00108;21/03/2023;21/03/2023;108;EUR;BE00010001000101;Virement en euros;BE170017001717;BOBOBO BOBOBO;+++389/5147/28354+++;VIREMENT EN EUROS DU COMPTE BE17 0017 0017 17 BIC GABBBEBB BOBOBO BOBOBO CLOS DE LA COLLINE 13 8888 BANDARLOG COMMUNICATION : 389514728354 REFERENCE BANQUE : 23032490021 DATE VALEUR : 21/03/2023;Accepté;",
    ]

    def test_non_overlapping_uploads(self):
        configuration = {"dbdir": ":memory:"}
        connection = storage.ensure_connection(configuration)
        first_batch = self.bank_statements_csv[:len(self.bank_statements_csv) // 2]
        assert len(first_batch) > 1, "Pre-condition not met: not enough test data for 1st batch"
        second_batch = [self.bank_statements_csv[0]] + self.bank_statements_csv[len(first_batch):]
        assert len(second_batch) > 1, "Pre-condition not met: not enough test data for 2nd batch"
        lib_payments.import_bank_statements(connection,
                                            "\n".join(first_batch),
                                            "user-test",
                                            "1.2.3.4")
        self.assertEqual(storage.Payment.length(connection), len(first_batch) - 1)

        lib_payments.import_bank_statements(connection,
                                            "\n".join(second_batch),
                                            "other-user-test",
                                            "5.6.7.8")
        self.assertEqual(storage.Payment.length(connection), len(self.bank_statements_csv) - 1)

    def test_overlapping_uploads(self):
        configuration = {"dbdir": ":memory:"}
        connection = storage.ensure_connection(configuration)
        first_batch = self.bank_statements_csv[:6]
        assert len(first_batch) > 1, "Pre-condition not met: not enough test data for 1st batch"
        second_batch = [self.bank_statements_csv[0]] + self.bank_statements_csv[4:]
        assert len(second_batch) > 1, "Pre-condition not met: not enough test data for 2nd batch"
        lib_payments.import_bank_statements(connection,
                                            "\n".join(first_batch),
                                            "user-test",
                                            "1.2.3.4")
        self.assertEqual(storage.Payment.length(connection), len(first_batch) - 1)

        lib_payments.import_bank_statements(connection,
                                            "\n".join(second_batch),
                                            "other-user-test",
                                            "5.6.7.8")
        self.assertEqual(storage.Payment.length(connection), len(self.bank_statements_csv) - 1)


class GetListPaymentsRow(unittest.TestCase):
    def test_payment_possible_bankid_but_no_reservation_match(self):
        configuration = {"dbdir": ":memory:"}
        connection = storage.ensure_connection(configuration)
        with connection:
            conftest.make_reservation(places=1).insert_data(connection)
        src_id = "1"
        for uuid in ('+++671/4235/58049+++', '671423558049'):
            with self.subTest(uuid=uuid):
                src_id += "0"
                with connection:
                    payment = conftest.make_payment(src_id=src_id, comment=uuid, uuid=None).insert_data(connection)
                html_row = lib_payments.get_list_payments_row(connection, payment, None, 'example.com', 'italsdf2024/gestion/list_payments.cgi', 'csrf_token_value')

                self.assertEqual(html_row, (('td', src_id),
                                            ('td', '17/01/2024'),
                                            ('td', 'BE0101'),
                                            ('td', 'Ms Abc'),
                                            ('td', 'Accepté'),
                                            ('td', uuid),
                                            ('td', '30.00'),
                                            ('td', ('div',
                                                    (('form', 'style', 'display: inline', 'method', 'POST',
                                                      'action', 'italsdf2024/gestion/link_payment_and_reservation.cgi'),
                                                     (('input', 'type', 'hidden', 'name', 'csrf_token', 'value', 'csrf_token_value'),),
                                                     (('input', 'type', 'hidden', 'name', 'src_id', 'value', src_id),),
                                                     (('select', 'name', 'reservation_uuid'),
                                                      (('option', 'value', ''), '--- Choisir la réservation correspondante ---'),
                                                      (('option', 'value', 'deadbeef'), '12349876', ' ', 'testing test@example.com')),
                                                     (('input', 'type', 'submit', 'value', 'OK'),)),
                                                    (('form', 'style', 'display: inline', 'method', 'POST',
                                                      'action', 'italsdf2024/gestion/hide_payment.cgi'),
                                                     (('input', 'type', 'hidden', 'name', 'csrf_token', 'value', 'csrf_token_value'),),
                                                     (('input', 'type', 'hidden', 'name', 'src_id', 'value', src_id),),
                                                     (('input', 'type', 'submit', 'value', 'hide'),))))))

    def test_payment_possible_bankid_but_no_reservations_yet(self):
        configuration = {"dbdir": ":memory:"}
        connection = storage.ensure_connection(configuration)
        src_id = "1"
        for uuid in ('+++671/4235/58049+++', '671423558049'):
            with self.subTest(uuid=uuid):
                src_id += "0"
                with connection:
                    payment = conftest.make_payment(src_id=src_id, comment=uuid).insert_data(connection)
                html_row = lib_payments.get_list_payments_row(connection, payment, None, 'example.com', 'italsdf2024/gestion/list_payments.cgi', 'csrf_token_value')

                self.assertEqual(html_row, (('td', src_id),
                                            ('td', '17/01/2024'),
                                            ('td', 'BE0101'),
                                            ('td', 'Ms Abc'),
                                            ('td', 'Accepté'),
                                            ('td', uuid),
                                            ('td', '30.00'),
                                            ('td', "#N/A")))

    def test_payment_not_ok_for_a_reservation(self):
        configuration = {"dbdir": ":memory:"}
        connection = storage.ensure_connection(configuration)
        with connection:
            payment = conftest.make_payment(amount_in_cents=-34).insert_data(connection)
            conftest.make_reservation(places=2, email=None, bank_id='123123123123', name='Mr B', uuid='otheruuid').insert_data(connection)
        html_row = lib_payments.get_list_payments_row(connection, payment, None, 'example.com', '/gestion/list_payments.cgi', 'csrf_token_value')

        self.assertEqual(html_row, (('td', '2023-1000'),
                                    ('td', '17/01/2024'),
                                    ('td', 'BE0101'),
                                    ('td', 'Ms Abc'),
                                    (('td', 'class', 'payment-not-ok'), 'Accepté'),
                                    ('td', 'unit test comment'),
                                    (('td', 'class', 'payment-not-ok'), '-0.34'),
                                    ('td', (('form', 'style', 'display: inline', 'method', 'POST',
                                             'action', '/gestion/link_payment_and_reservation.cgi'),
                                            (('input', 'type', 'hidden', 'name', 'csrf_token', 'value', 'csrf_token_value'),),
                                            (('input', 'type', 'hidden', 'name', 'src_id', 'value', '2023-1000'),),
                                            (('select', 'name', 'reservation_uuid'),
                                             (('option', 'value', ''), '--- Choisir la réservation correspondante ---'),
                                             (('option', 'value', 'otheruuid'), '+++123/1231/23123+++', ' ', 'Mr B')),
                                            (('input', 'type', 'submit', 'value', 'OK'),)))))

    def test_payment_already_linked_to_reservation(self):
        configuration = {"dbdir": ":memory:"}
        connection = storage.ensure_connection(configuration)

        uuid_hex = "abcdef"
        src_id = f"{YEAR_PREFIX}-100"
        for email, expected_text in (("", 'testing'), (" ", "testing"), (None, "testing"), ("a@b.c", "testing a@b.c")):
            uuid_hex += "0"
            src_id += "1"
            with self.subTest(email=email):
                with connection:
                    reservation = conftest.make_reservation(email=email, places=1, bank_id=uuid_hex, uuid=uuid_hex).insert_data(connection)
                    payment = conftest.make_payment(uuid=reservation.uuid, src_id=src_id, confirmation_timestamp=1234.5).insert_data(connection)
                html_row = lib_payments.get_list_payments_row(connection, payment, reservation, 'example.com', 'italsdf2024/gestion/list_payments.cgi', 'csrf_token_value')

                self.assertEqual(html_row, (('td', src_id),
                                            ('td', '17/01/2024'),
                                            ('td', 'BE0101'),
                                            ('td', 'Ms Abc'),
                                            ('td', 'Accepté'),
                                            ('td', 'unit test comment'),
                                            ('td', '30.00'),
                                            ('td',
                                             ('div',
                                              (('form', 'style', 'display: inline', 'method', 'POST', 'action', 'italsdf2024/gestion/link_payment_and_reservation.cgi'),
                                               (('a', 'href', f'https://example.com/italsdf2024/show_reservation.cgi?uuid_hex={uuid_hex}'),
                                                expected_text),
                                               ' ',
                                               (('input', 'type', 'hidden', 'name', 'csrf_token', 'value', 'csrf_token_value'),),
                                               (('input', 'type', 'hidden', 'name', 'src_id', 'value', src_id),),
                                               (('input', 'type', 'hidden', 'name', 'reservation_uuid', 'value', ''),),
                                               (('input', 'type', 'submit', 'value', 'X'),)),
                                              (('a', 'href', f"https://example.com/italsdf2024/gestion/confirm_payment.cgi?uuid_hex={uuid_hex}&src_id={src_id}"),
                                               'send again?')))))


    def test_payment_possible_bankid_and_reservation_match(self):
        configuration = {"dbdir": ":memory:"}
        connection = storage.ensure_connection(configuration)
        with connection:
            conftest.make_reservation(places=2, bank_id='123123123123', name='Mr B', uuid='otheruuid').insert_data(connection)
            conftest.make_reservation(places=1, bank_id='671423558049').insert_data(connection)
        src_id = "1"
        for uuid in ('+++671/4235/58049+++', '671423558049'):
            with self.subTest(uuid=uuid):
                src_id += "0"
                with connection:
                    payment = conftest.make_payment(src_id=src_id, comment=uuid).insert_data(connection)
                html_row = lib_payments.get_list_payments_row(connection, payment, None, 'example.com', 'italsdf2024/gestion/list_payments.cgi', 'csrf_token_value')

                self.assertEqual(
                    html_row, (('td', src_id),
                               ('td', '17/01/2024'),
                               ('td', 'BE0101'),
                               ('td', 'Ms Abc'),
                               ('td', 'Accepté'),
                               ('td', uuid),
                               ('td', '30.00'),
                               ('td',
                                (('form', 'style', 'display: inline', 'method', 'POST',
                                  'action', 'italsdf2024/gestion/link_payment_and_reservation.cgi'),
                                 (('input', 'type', 'hidden', 'name', 'csrf_token', 'value', 'csrf_token_value'),),
                                 (('input', 'type', 'hidden', 'name', 'src_id', 'value', src_id),),
                                 (('select', 'name', 'reservation_uuid'),
                                  (('option', 'value', 'deadbeef', 'selected', 'selected'),
                                   '+++671/4235/58049+++', ' ', 'testing test@example.com'),
                                  (('option', 'value', 'otheruuid'),
                                   '+++123/1231/23123+++', ' ', 'Mr B test@example.com')),
                                 (('input', 'type', 'submit', 'value', 'OK'),)))))


if __name__ == '__main__':
    unittest.main()

# Local Variables:
# compile-command: "python3 test_lib_payments.py"
# End:
