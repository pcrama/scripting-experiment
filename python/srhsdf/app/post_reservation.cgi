#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import contextlib
import glob
import html
import json
import os
import sqlite3
import sys
import time
import uuid

'''
Input:
- name
- phone
- email
- date
- paying_seats
- free_seats
- gdpr_accepts_use
- uuid

Generate bank_id (10 digits, 33 bits):
- time: 7 bits
- number of previous calls: 10 bits
- process ID: os.getpid(), 16 bits

Save:
- name
- phone
- email
- date
- paying_seats
- free_seats
- gdpr_accepts_use
- bank_id
- uuid
- time
'''

try:
    SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
except NameError:
    SCRIPT_DIR = os.path.realpath(os.getcwd())


class Reservation:
    def __init__(self, name, phone, email, date, paying_seats, free_seats, gdpr_accepts_use, bank_id, uuid_hex, timestamp):
        self.name = name
        self.phone = phone
        self.email = email
        self.date = date
        self.paying_seats = paying_seats
        self.free_seats = free_seats
        self.gdpr_accepts_use = gdpr_accepts_use
        self.bank_id = bank_id
        self.uuid_hex = uuid_hex
        self.timestamp = timestamp

    def to_dict(self):
        return {'name': self.name,
                'phone': self.phone,
                'email': self.email,
                'date': self.date,
                'paying_seats': self.paying_seats,
                'free_seats': self.free_seats,
                'gdpr_accepts_use': self.gdpr_accepts_use,
                'bank_id': append_bank_id_control_number(self.bank_id),
                'uuid': self.uuid_hex,
                'time': self.timestamp}


def create_db(root_dir):
    con = sqlite3.connect(os.path.join(root_dir, 'db.db'))
    try:
        con.execute('SELECT COUNT(*) FROM reservations')
    except Exception as e:
        con.execute('''CREATE TABLE reservations
                       (name TEXT NOT NULL,
                        phone TEXT,
                        email TEXT,
                        date TEXT NOT NULL,
                        paying_seats INTEGER,
                        free_seats INTEGER,
                        gdpr_accepts_use INTEGER,
                        bank_id TEXT NOT NULL,
                        uuid TEXT NOT NULL,
                        time REAL)''')
        con.execute('''CREATE UNIQUE INDEX index_bank_id ON reservations (bank_id)''')
    return con


def insert_data(connection, data):
    connection.execute(
        '''INSERT INTO reservations VALUES (
                :name, :phone, :email, :date, :paying_seats, :free_seats,
                :gdpr_accepts_use, :bank_id, :uuid, :time)''',
        data)


def normalize_data(name, phone, email, date, paying_seats, free_seats, gdpr_accepts_use):
    def safe_strip(x):
        if x is None:
            return ''
        else:
            return ' '.join(x.split())
    def safe_non_negative_int_less_or_equal_than_50(x):
        try:
            x = int(x)
            return max(0, min(x, 50))
        except Exception:
            return 0
    name = safe_strip(name)
    phone = ''.join(d for d in safe_strip(phone) if d.isdigit())
    email = safe_strip(email)
    date = safe_strip(date)
    paying_seats = safe_non_negative_int_less_or_equal_than_50(paying_seats)
    free_seats = safe_non_negative_int_less_or_equal_than_50(free_seats)
    try:
        gdpr_accepts_use = gdpr_accepts_use.lower() in ['yes', 'oui', '1', 'true', 'vrai']
    except Exception:
        gdpr_accepts_use = gdpr_accepts_use and gdpr_accepts_use not in [0, False]
    return (name, phone, email, date, paying_seats, free_seats, gdpr_accepts_use)


class ValidationException(Exception):
    pass


def is_test_reservation(name, email):
    return name.lower().startswith('test') and email.lower().endswith('@example.com')


def validate_data(name, phone, email, date, paying_seats, free_seats, gdpr_accepts_use, connection):
    (name, phone, email, date, paying_seats, free_seats, gdpr_accepts_use) = normalize_data(
        name, phone, email, date, paying_seats, free_seats, gdpr_accepts_use)
    if not(name and (phone or email)):
        raise ValidationException('No contact information')
    try:
        at_sign = email.index('@', 1) # email address must contain '@' but may not start with it
        host_dot = email.index('.', at_sign + 1)
    except ValueError:
        email_is_bad = email != ''
    else:
        email_is_bad = False
    if email_is_bad:
        raise ValidationException('Invalid email address')
    if paying_seats + free_seats < 1:
        raise ValidationException('No seats reserved')
    if date not in (('2099-01-01', '2099-01-02')
                    if is_test_reservation(name, email)
                    else ('2021-12-04', '2021-12-05')):
        raise ValidationException('No representation')
    reservations_count, reserved_seats  = connection.execute(
        'SELECT COUNT(*), SUM(paying_seats + free_seats) FROM reservations WHERE LOWER(name) = :name OR LOWER(email) = :email',
        {'name': name.lower(), 'email': email.lower()}
    ).fetchone()
    if (reservations_count or 0) > 10:
        raise ValidationException('Too many distinct reservations')
    if (reserved_seats or 0) + paying_seats + free_seats > 60:
        raise ValidationException('Too many seats reserved')
    return (name, phone, email, date, paying_seats, free_seats, gdpr_accepts_use)


def save_data_sqlite3(name, phone, email, date, paying_seats, free_seats, gdpr_accepts_use,
                      connection_or_root_dir):
    if hasattr(connection_or_root_dir, 'execute'):
        connection = connection_or_root_dir
    else:
        connection = create_db(connection_or_root_dir)
    process_id = os.getpid()
    uuid_hex = uuid.uuid4().hex
    def count_reservations():
        return connection.execute('SELECT COUNT(*) FROM reservations').fetchone()[0]
    retries = 3
    while retries > 0:
        retries -= 1
        timestamp = time.time()
        bank_id = generate_bank_id(timestamp, count_reservations(), process_id)
        try:
            new_row = {'name': name,
                       'phone': phone,
                       'email': email,
                       'date': date,
                       'paying_seats': paying_seats,
                       'free_seats': free_seats,
                       'gdpr_accepts_use': gdpr_accepts_use,
                       'bank_id': append_bank_id_control_number(bank_id),
                       'uuid': uuid_hex,
                       'time': timestamp}
            with connection:
                insert_data(connection, new_row)
            return new_row
        except Exception:
            if retries > 0:
                time.sleep(0.011)
                pass
            else:
                raise


def save_data_file_system(name, phone, email, date, paying_seats, free_seats, gdpr_accepts_use,
                          root_dir):
    def lock_name(bank_id):
        return os.path.join(root_dir, bank_id)
    @contextlib.contextmanager
    def get_lock(bank_id):
        lock = lock_name(bank_id)
        os.mkdir(lock)
        try:
            yield
        finally:
            os.rmdir(lock)
    def count_reservations():
        return len(glob.glob(os.path.join(root_dir, '*.json')))
    def write_data(data):
        with open(lock_name(data['bank_id']) + '.json', 'w') as f:
            f.write(json.dumps(data))
    return _save_data(name, phone, email, date, paying_seats, free_seats,
                      gdpr_accepts_use, uuid.uuid4().hex, get_lock,
                      count_reservations, write_data, time.time, time.sleep,
                      os.getpid())


def test_save_data():
    # Given
    lock_results = [Exception('Mock lock failure'), None]
    lock_attempts = []
    unlock_attempts = []
    @contextlib.contextmanager
    def get_lock(bank_id):
        lock_attempts.append(bank_id)
        result = lock_results.pop(0)
        if result is None:
            try:
                yield
            finally:
                unlock_attempts.append(bank_id)
                if bank_id != lock_attempts[-1]:
                    raise Exception(f"Can't unlock '{bank_id}', expected '{lock_attempts[-1]}")
        else:
            raise result
    reservations_counts = [3, 4]
    def count_reservations():
        return reservations_counts.pop(0)
    written_data = []
    def write_data(data):
        written_data.append(data)
    time_times = [1.08, 1.2]
    def time_time():
        return time_times.pop(0)
    time_sleeps = []
    def time_sleep(seconds):
        time_sleeps.append(seconds)
    # When
    _save_data('name', 'phone', 'email', 'date', 1, 2, True, 'uuid_value',
               get_lock, count_reservations, write_data, time_time,
               time_sleep, 37)
    # Then
    assert not lock_results
    assert lock_attempts == [f'{37 + 65536 * (3 + 1024 * 108):010}', f'{37 + 65536 * (4 + 1024 * 120):010}']
    assert unlock_attempts == [lock_attempts[-1]]
    assert not reservations_counts
    assert written_data == [{'bank_id': '805332586192',
                             'date': 'date',
                             'email': 'email',
                             'free_seats': 2,
                             'gdpr_accepts_use': True,
                             'name': 'name',
                             'paying_seats': 1,
                             'phone': 'phone',
                             'uuid': 'uuid_value',
                             'time': 1.2}]
    assert not time_times
    assert time_sleeps == [0.01]


def _save_data(name, phone, email, date, paying_seats, free_seats,
               gdpr_accepts_use, uuid, get_lock, count_reservations,
               write_data, time_time, time_sleep, process_id):
    '''Save data about reservation request

    Data fields to save: name, phone, email, date, paying_seats, free_seats,
        gdpr_accepts_use, uuid (random number to serve as extra access control
        to prevent enumerating bank_id values, uuid.UUID4().hex)

    Extra field saved: time (timestamp when bank payment ID was generated)

    Dependencies to inject explicitly:
    - get_lock(bank_id: str) -> context: create a lock inside which a new reservation
      is created with the given bank_id
    - count_reservations() -> int: return the number of existing reservations, used
      as input to generate unique bank_id values
    - write_data(data: dict) -> None: writes the data in the dictionary
    - time_time() -> float: get current time
    - time_sleep(float) -> None: sleep after failing to acquire a lock
    - process_id: os.getpid(), used as input to generate unique bank_id values

    '''
    retry = 3
    while retry > 0:
        timestamp = time_time()
        bank_id = generate_bank_id(timestamp, count_reservations(), process_id)
        try:
            retry -= 1
            have_lock = False
            with get_lock(bank_id):
                have_lock = True
                write_data({'name': name,
                            'phone': phone,
                            'email': email,
                            'date': date,
                            'paying_seats': paying_seats,
                            'free_seats': free_seats,
                            'gdpr_accepts_use': gdpr_accepts_use,
                            'bank_id': append_bank_id_control_number(bank_id),
                            'uuid': uuid,
                            'time': timestamp})
        except Exception:
            if have_lock or retry < 1:
                raise
            else:
                time_sleep(0.01)
        else:
            break


def to_bits(n):
    while n > 0:
        if n & 1 == 0:
            yield 0
        else:
            yield 1
        n >>= 1


def generate_bank_id(time_time, number_of_previous_calls, process_id):
    data = [(x & ((1 << b) - 1), b)
            for (x, b)
            in ((round(time_time * 100.0), 7),
                (number_of_previous_calls, 10),
                (process_id, 16))]
    bits = 0
    n = 0
    for (x, b) in data:
        n = (n << b) + x
    return f'{n:010}'


def append_bank_id_control_number(s):
    n = 0
    for c in s:
        if c == '/':
            continue
        elif not c.isdigit():
            raise Exception(f'{c} is not a digit')
        n = (n * 10 + int(c)) % 97
    if n == 0:
        n = 97
    return f'{s}{n:02}'


def html_gen(data):
    def is_tuple(x):
        return type(x) is tuple
    if is_tuple(data):
        tag_name = None
        single_elt = len(data) == 1
        for elt in data:
            if tag_name is None:
                tag = elt
                if is_tuple(tag):
                    tag_name = str(elt[0])
                    attr_values = []
                    for idx in range(1, 2, len(tag)):
                        attr_values.append((tag[idx], html.escape(tag[idx + 1], quote=True)))
                    yield '<' + tag_name + ' ' + ' '.join(f'{x}="{y}"' for (x, y) in attr_values)
                else:
                    tag_name = str(tag)
                    yield f'<{tag_name}'
                yield ('/>' if single_elt else '>')
            else:
                for x in html_gen(elt):
                    yield x
        if not single_elt:
            yield f'</{tag_name}>'
    else:
        yield html.escape(str(data), quote=False)


def html_document(title, body):
    yield '<!DOCTYPE HTML>'
    for x in html_gen((('html', 'lang', 'fr'),
                       ('head',
                        ('title', title),
                        (('meta', 'charset', 'utf-8'),)),
                       ('body', )
                       + body
                       + (('hr', ),
                          ('p',
                           'Retour au ',
                           (('a', 'href', 'https://www.srhbraine.be/'),
                            "site de la Société Royale d'Harmonie de Braine-l'Alleud"),
                           '.')))):
        yield x


def respond_html(data):
    print('Content-Type: text/html; charset=utf-8')
    print('Content-Language: en, fr')
    print()
    for x in data:
        print(x, end='')


def respond_with_validation_error(form, e):
    respond_html(html_document(
        'Données invalides dans le formulaire',
        (('p', "Votre formulaire contient l'erreur suivante:"),
         ('p', (('code', 'lang', 'en'), str(e))))
        + ((('p', 'Formulaire vide.'),)
           if len(form) < 1 else
           (('p', "Voici les données reçues"),
            ('ul',) + tuple(('li', ('code', k), ': ', repr(form[k]))
                         for k in form.keys())))))


def compute_price(paying_seats, date):
    return paying_seats * CONFIGURATION['paying_seat_price']


def respond_with_reservation_failed():
    respond_html(html_document(
        'Erreur interne au serveur',
        (('p',
          "Malheureusement une erreur s'est produite et votre réservation n'a pas été enregistrée.  "
          "Merci de bien vouloir ré-essayer plus tard."),)))



def respond_with_reservation_confirmation(
        name, phone, email, date, paying_seats, free_seats, gdpr_accepts_use, connection):
    try:
        new_row = save_data_sqlite3(
            name, phone, email, date, paying_seats, free_seats, gdpr_accepts_use, connection)
    except Exception:
        cgitb.handler()
        respond_with_reservation_failed()
    price = compute_price(paying_seats, date)
    places = (' pour ',)
    if paying_seats > 0:
        places += (str(paying_seats),
                   ' place payante ' if paying_seats == 1 else ' places payantes ')
    if free_seats > 0:
        if paying_seats > 0:
            places += ('et ',)
        places += (str(free_seats),
                   ' place gratuite ' if free_seats == 1 else ' places gratuites ')
    if paying_seats > 0:
        places += ('au prix de ', str(price), '€')
    places += (' a été enregistrée.',)
    virement = '' \
        if paying_seats < 1 else (
                'p', 'Veuillez effectuer un virement pour ', str(price),
                '€ au compte BExx XXXX YYYY ZZZZ en mentionnant la communication '
                'structurée ', ('code', new_row['bank_id']), '.')
    respond_html(html_document(
        'Réservation effectuée',
        (('p', 'Votre réservation au nom de ', name) + places,
         virement,
         ('p', 'Un tout grand merci pour votre présence le ', date, ': le soutien '
          'de nos auditeurs nous est indispensable!'))))


if __name__ == '__main__':
    # CGI script configuration
    CONFIGURATION_DEFAULTS = {
        'logdir': os.getenv('TEMP', SCRIPT_DIR),
        'dbdir': os.getenv('TEMP', SCRIPT_DIR),
        'cgitb_display': 1,
        'paying_seat_price': 5,
    }
    try:
        with open(os.path.join(SCRIPT_DIR, 'configuration.json')) as f:
            CONFIGURATION = json.load(f)
    except Exception:
        CONFIGURATION = dict()
    for k, v in CONFIGURATION_DEFAULTS.items():
        CONFIGURATION.setdefault(k, v)

    cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

    try:
        db_connection = create_db(CONFIGURATION['dbdir'])

        # Get form data
        form = cgi.FieldStorage()
        name = form.getfirst('name', default='')
        phone = form.getfirst('phone', default='')
        email = form.getfirst('email', default='')
        date = form.getfirst('date', default='')
        paying_seats = form.getfirst('paying_seats', default=0)
        free_seats = form.getfirst('free_seats', default=0)
        gdpr_accepts_use = form.getfirst('gdpr_accepts_use', default=False)
    except Exception:
        # cgitb needs the content-type header
        print('Content-Type: text/html; charset=utf-8')
        print('Content-Language: en')
        print()
        raise

    try:
        (name, phone, email, date, paying_seats, free_seats, gdpr_accepts_use) = validate_data(
            name, phone, email, date, paying_seats, free_seats, gdpr_accepts_use, db_connection)
    except ValidationException as e:
        respond_with_validation_error(form, e)
    else:
        respond_with_reservation_confirmation(
            name, phone, email, date, paying_seats, free_seats, gdpr_accepts_use, db_connection)
