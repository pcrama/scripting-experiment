# -*- coding: utf-8 -*-
import os
import sqlite3

def create_db(configuration):
    root_dir = configuration['dbdir']
    con = sqlite3.connect(os.path.join(root_dir, 'db.db'))
    try:
        con.execute('SELECT COUNT(*) FROM reservations')
    except Exception as e:
        con.execute('''CREATE TABLE reservations
                       (name TEXT NOT NULL,
                        email TEXT,
                        date TEXT NOT NULL,
                        paying_seats INTEGER,
                        free_seats INTEGER,
                        gdpr_accepts_use INTEGER,
                        cents_due INTEGER,
                        bank_id TEXT NOT NULL,
                        uuid TEXT NOT NULL,
                        time REAL)''')
        con.execute('''CREATE UNIQUE INDEX index_bank_id ON reservations (bank_id)''')
    return con


def ensure_connection(connection_or_root_dir):
    return (connection_or_root_dir
            if hasattr(connection_or_root_dir, 'execute') else
            create_db(connection_or_root_dir))


class Reservation:
    def __init__(self, name, email, date, paying_seats, free_seats, gdpr_accepts_use, cents_due, bank_id, uuid_hex, timestamp):
        self.name = name
        self.email = email
        self.date = date
        self.paying_seats = paying_seats
        self.free_seats = free_seats
        self.gdpr_accepts_use = gdpr_accepts_use
        self.cents_due = cents_due
        self.bank_id = bank_id
        self.uuid_hex = uuid_hex
        self.timestamp = timestamp


    def to_dict(self):
        return {'name': self.name,
                'email': self.email,
                'date': self.date,
                'paying_seats': self.paying_seats,
                'free_seats': self.free_seats,
                'gdpr_accepts_use': self.gdpr_accepts_use,
                'cents_due': self.cents_due,
                'bank_id': self.bank_id,
                'uuid': self.uuid_hex,
                'time': self.timestamp}


    def insert_data(self, connection):
        connection.execute(
            '''INSERT INTO reservations VALUES (
                :name, :email, :date, :paying_seats, :free_seats,
                :gdpr_accepts_use, :cents_due, :bank_id, :uuid, :time)''',
            self.to_dict())

    @classmethod
    def select(cls, connection, filter=None, order_columns=None, limit=None, offset=None):
        params = dict()
        query = ['SELECT * FROM reservations']
        if filter is not None:
            query.append('WHERE :filter')
            params['filter'] = filter
        if order_columns is not None:
            query.append('ORDER BY :order_columns')
            params['order_columns'] = order_columns
        if limit is not None:
            query.append('LIMIT :limit')
            params['limit'] = limit
        if offset is not None:
            query.append('OFFSET :offset')
            params['offset'] = offset
        for row in connection.execute(' '.join(query), params):
            yield cls(
                name=row[0],
                email=row[1],
                date=row[2],
                paying_seats=row[3],
                free_seats=row[4],
                gdpr_accepts_use=row[5],
                cents_due=row[6],
                bank_id=row[7],
                uuid_hex=row[8],
                timestamp=row[9])
