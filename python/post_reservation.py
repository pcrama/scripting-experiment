import cgi
import contextlib
import os
import glob
import json
import sys
import time

'''
Input:
- name
- phone
- email
- date
- paying_seats
- free_seats
- gdpr_accepts_use

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
'''

def save_data(name, phone, email, date, paying_seats, free_seats, gdpr_accepts_use,
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
