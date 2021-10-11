import cgi
import os
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

def test_save_data():
    pass


def save_data(name, phone, email, data, paying_seats, free_seats, gdpr_accepts_use,
              root_dir):
    def lock_name(bank_id):
        return os.path.join(root_dir, bank_id)
    def get_lock(bank_id):
        os.mkdir(lock_name(bank_id))
    def release_lock(bank_id):
        os.rmdir(lock_name(bank_id))
    def count_reservations():
        return len(glob.glob(os.path.join(root_dir, '*.json')))
    def write_data(data):
        with open(get_lock(bank_id) + '.json', 'w') as f:
            f.write(json.dumps(data))
    return _save_data(
        name, phone, email, data, paying_seats, free_seats, gdpr_accepts_use,
        get_lock, release_lock, count_reservations, write_data,
        time.time, time.sleep, process_id)


def _save_data(name, phone, email, data, paying_seats, free_seats, gdpr_accepts_use,
               get_lock, release_lock, count_reservations, write_data,
               time_time, time_sleep, process_id):
    retry = 3
    while True:
        bank_id = generate_bank_id(time_time(), count_reservations(), process_id)
        try:
            get_lock(bank_id)
        except Exception:
            if retry > 0:
                retry -= 1
                time_sleep(0.01)
            else:
                raise
        write_data({'name': name,
                    'phone': phone,
                    'email': email,
                    'date': date,
                    'paying_seats': paying_seats,
                    'free_seats': free_seats,
                    'gdpr_accepts_use': gdpr_accepts_use,
                    'bank_id': append_bank_id_control_number(bank_id)})
        release_lock(bank_id)


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
