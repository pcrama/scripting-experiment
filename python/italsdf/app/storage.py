# -*- coding: utf-8 -*-
import os
import sqlite3
import time
from typing import Any, Callable, Iterable, Union
import uuid

def create_db(configuration: dict[str, Any]) -> sqlite3.Connection:
    root_dir = configuration['dbdir']
    connection = sqlite3.connect(
        root_dir if root_dir == ':memory:' else os.path.join(root_dir, 'db.db'))
    for table in (Csrf, Reservation, Payment):
        try:
            connection.execute(f'SELECT COUNT(*) FROM {table.TABLE_NAME}')
        except Exception as e:
            table.create_in_db(connection)
    return connection


def ensure_connection(connection_or_root_dir: Union[sqlite3.Connection, dict[str, Any]]) -> sqlite3.Connection:
    return (connection_or_root_dir
            if isinstance(connection_or_root_dir, sqlite3.Connection) else
            create_db(connection_or_root_dir))


def default_creation_statement(table_name: str, columns: Iterable[tuple[str, str]]) -> str:
    return f'''CREATE TABLE {table_name} ({", ".join(" ".join(col) for col in columns)})'''



class MiniOrm:
    TABLE_NAME: str
    CREATION_STATEMENTS: Iterable[str]
    SORTABLE_COLUMNS: dict[str, str] = {} # override with column info for `select'
    FILTERABLE_COLUMNS: dict[str, str] = {} # override with column info for `select'

    def __str__(self):
        try:
            parts = ['<', self.TABLE_NAME]
            for col_name, value in self.to_dict().items():
                parts.append(f" {col_name}={value!r}")
            parts.append('>')
            return "".join(parts)
        except Exception:
            return super().__str__()

    def __repr__(self):
        try:
            parts = [self.__class__.__name__, '(']
            for col_name, value in self.to_dict().items():
                parts.append(f"{col_name}={value!r}, ")
            parts.append(')')
            return "".join(parts)
        except Exception:
            return super().__repr__()

    @classmethod
    def create_in_db(cls, connection):
        with connection:
            for s in cls.CREATION_STATEMENTS:
                connection.execute(s)


    @classmethod
    def length(cls, connection, filtering=None):
        params = dict()
        query = [f'SELECT COUNT(*) FROM {cls.TABLE_NAME}']
        if filtering is not None:
            clauses, extra_params = cls.where_clause(filtering)
            query.append(f'WHERE {clauses}')
            params.update(extra_params)
        return connection.execute(' '.join(query), params).fetchone()[0]


    @staticmethod
    def maybe_add_wildcards(x: str) -> str:
        return x if '%' in x else f'%{x}%'


    @staticmethod
    def compare_with_like_lower(x: str) -> tuple[str, str, Callable[[str], str]]:
        return (f'LOWER({x})',
                'like',
                lambda val: MiniOrm.maybe_add_wildcards(val.lower()))


    @staticmethod
    def compare_as_bool(x):
        return (x, '=', lambda val: 1 if val else 0)


    @classmethod
    def select(cls, connection, filtering=None, order_columns=None, limit=None, offset=None):
        params = dict()
        query = [f'SELECT {",".join(col[0] for col in cls.COLUMNS)} FROM {cls.TABLE_NAME}']
        if filtering is not None:
            clauses, extra_params = cls.where_clause(filtering)
            query.append(f'WHERE {clauses}')
            params.update(extra_params)
        if order_columns is not None:
            ordering = ','.join((y for y in (
                cls.column_ordering_clause(x) for x in order_columns)
                                if y is not None))
            if ordering:
                query.append(f'ORDER BY {ordering}')
        if limit is not None:
            query.append('LIMIT :limit')
            params['limit'] = limit
        if offset is not None:
            query.append('OFFSET :offset')
            params['offset'] = offset
        for row in connection.execute(' '.join(query), params):
            yield cls.from_row(row)

    @classmethod
    def from_row(cls, row):
        assert len(row) == len(cls.COLUMNS)
        return cls(**{column_name: elt for ((column_name, _type), elt)
                      in zip(cls.COLUMNS, row)})


    @classmethod
    def column_ordering_clause(cls, col):
        try:
            clause = cls.SORTABLE_COLUMNS[col.lower()]
            asc_or_desc = 'DESC' if col[0].isupper() else 'ASC'
            return f'{clause} {asc_or_desc}'
        except KeyError:
            return None


    @classmethod
    def encode_column_value_for_search(cls, col, val, info):
        try:
            col_value = info[0]
        except Exception:
            col_value = col
        try:
            operator = info[1]
        except Exception:
            operator = '='
        try:
            target_value = info[2](val)
        except Exception:
            target_value = val
        return (col_value, operator, target_value)


    @classmethod
    def where_clause(cls, filtering):
        params = dict()
        clauses = []
        for (col, val) in filtering:
            try:
                info = cls.FILTERABLE_COLUMNS[col]
            except KeyError:
                continue
            var_name = f'filter_{col}'
            col_value, operator, target_value = cls.encode_column_value_for_search(
                col, val, info)
            params[var_name] = target_value
            clauses.append(f'{col_value} {operator} :{var_name}')
        if clauses:
            return ('(' + ' AND '.join(clauses) + ')', params)
        else:
            return ([], {})


class Reservation(MiniOrm):
    TABLE_NAME = 'reservations'
    COLUMNS = [
        ("name", "TEXT NOT NULL"),
        ("email", "TEXT"),
        ("extra_comment", "TEXT"),
        ("places", "INTEGER CHECK(places > 0)"),
        ("date", "TEXT NOT NULL"),
        ("outside_extra_starter", "INTEGER"),
        ("outside_main_starter", "INTEGER"),
        ("outside_bolo", "INTEGER"),
        ("outside_extra_dish", "INTEGER"),
        ("outside_dessert", "INTEGER"),
        ("inside_extra_starter", "INTEGER CHECK(inside_extra_starter + inside_main_starter = inside_bolo + inside_extra_dish)"),
        ("inside_main_starter", "INTEGER"),
        ("inside_bolo", "INTEGER"),
        ("inside_extra_dish", "INTEGER"),
        ("kids_bolo", "INTEGER"),
        ("kids_extra_dish", "INTEGER"),
        ("gdpr_accepts_use", "INTEGER"),
        ("cents_due", "INTEGER"),
        ("bank_id", "TEXT NOT NULL"),
        ("uuid", "TEXT NOT NULL"),
        ("time", "REAL"),
        ("active", "INTEGER"),
        ("origin", "TEXT"),
    ]
    CREATION_STATEMENTS = [
        default_creation_statement(TABLE_NAME, COLUMNS),
        f'CREATE UNIQUE INDEX index_bank_id_{TABLE_NAME} ON {TABLE_NAME} (bank_id)',
        f'CREATE UNIQUE INDEX index_uuid_{TABLE_NAME} ON {TABLE_NAME} (uuid)']

    def __init__(self,
                 name,
                 email,
                 extra_comment,
                 places,
                 date,
                 outside_extra_starter,
                 outside_main_starter,
                 outside_bolo,
                 outside_extra_dish,
                 outside_dessert,
                 inside_extra_starter,
                 inside_main_starter,
                 inside_bolo,
                 inside_extra_dish,
                 kids_bolo,
                 kids_extra_dish,
                 gdpr_accepts_use,
                 cents_due,
                 bank_id,
                 uuid,
                 time,
                 active,
                 origin):
        # !!! Keep in sync with COLUMNS if you want to use the default !!!
        # !!! from_row implementation !!!
        self.name = name
        self.email = email
        self.extra_comment = extra_comment
        self.places = places
        self.date = date
        self.outside_extra_starter = outside_extra_starter
        self.outside_main_starter = outside_main_starter
        self.outside_bolo = outside_bolo
        self.outside_extra_dish = outside_extra_dish
        self.outside_dessert = outside_dessert
        self.inside_extra_starter = inside_extra_starter
        self.inside_main_starter = inside_main_starter
        self.inside_bolo = inside_bolo
        self.inside_extra_dish = inside_extra_dish
        self.kids_bolo = kids_bolo
        self.kids_extra_dish = kids_extra_dish
        self.gdpr_accepts_use = gdpr_accepts_use
        self.cents_due = cents_due
        self.bank_id = bank_id
        self.uuid = uuid
        self.timestamp = time
        self.active = active
        self.origin = origin

    @property
    def inside_dessert(self):
        return self.inside_bolo + self.inside_extra_dish

    @property
    def kids_dessert(self):
        return self.kids_bolo + self.kids_extra_dish

    def to_dict(self):
        return {
            'name': self.name,
            'email': self.email,
            'extra_comment': self.extra_comment,
            'places': self.places,
            'date': self.date,
            'outside_extra_starter': self.outside_extra_starter,
            'outside_main_starter': self.outside_main_starter,
            'outside_bolo': self.outside_bolo,
            'outside_extra_dish': self.outside_extra_dish,
            'outside_dessert': self.outside_dessert,
            'inside_extra_starter': self.inside_extra_starter,
            'inside_main_starter': self.inside_main_starter,
            'inside_bolo': self.inside_bolo,
            'inside_extra_dish': self.inside_extra_dish,
            'kids_bolo': self.kids_bolo,
            'kids_extra_dish': self.kids_extra_dish,
            'gdpr_accepts_use': self.gdpr_accepts_use,
            'cents_due': self.cents_due,
            'bank_id': self.bank_id,
            'uuid': self.uuid,
            'time': self.timestamp,
            'active': self.active,
            'origin': self.origin}


    def insert_data(self, connection) -> "Reservation":
        connection.execute(
            f'''INSERT INTO {self.TABLE_NAME} VALUES (
                 :name, :email, :extra_comment, :places, :date, :outside_extra_starter, :outside_main_starter,
                 :outside_bolo, :outside_extra_dish, :outside_dessert, :inside_extra_starter,
                 :inside_main_starter, :inside_bolo, :inside_extra_dish,
                 :kids_bolo, :kids_extra_dish,
                 :gdpr_accepts_use, :cents_due, :bank_id, :uuid, :time, :active, :origin)''',
            self.to_dict())
        return self


    @classmethod
    def count_places(cls, connection, name=None, email=None):
        conditions = []
        params = {}
        for (p, n) in ((name, 'name'), (email, 'email')):
            if p is None:
                continue
            conditions.append(f'LOWER({n}) = :{n}')
            params[n] = p.lower()
        terms = ' AND '.join((f'({t})' for t in ('active != 0', ' OR '.join(conditions)) if t))
        return connection.execute(
            f'''SELECT COUNT(*), SUM(places) FROM {cls.TABLE_NAME}
                WHERE {terms}''',
            params
        ).fetchone()


    @classmethod
    def count_starters(cls, connection, name, email):
        return connection.execute(
            f'''SELECT COUNT(*), SUM(outside_extra_starter + outside_main_starter + inside_extra_starter + inside_main_starter)
                FROM {cls.TABLE_NAME}
                WHERE active != 0 AND (LOWER(name) = :name OR LOWER(email) = :email)''',
            {'name': name.lower(), 'email': email.lower()}
        ).fetchone()


    @classmethod
    def count_menu_data(cls, connection, date=None):
        if date is None:
            date_condition = ''
            bindings = {}
        else:
            date_condition = ' AND date = :date'
            bindings = {'date': date}
        return connection.execute(
            f'''SELECT COUNT(*), SUM(outside_main_starter + inside_main_starter), SUM(outside_extra_starter + inside_extra_starter), SUM(outside_bolo + inside_bolo), SUM(outside_extra_dish + inside_extra_dish), SUM(kids_bolo), SUM(kids_extra_dish), SUM(outside_dessert + inside_bolo + inside_extra_dish + kids_bolo + kids_extra_dish) FROM {cls.TABLE_NAME}
                WHERE active != 0{date_condition}''',
            bindings
        ).fetchone()


    @classmethod
    def count_desserts(cls, connection, name, email):
        return connection.execute(
            f'''SELECT COUNT(*), SUM(outside_dessert + inside_bolo + inside_extra_dish + kids_bolo + kids_extra_dish) FROM {cls.TABLE_NAME}
                WHERE active != 0 AND (LOWER(name) = :name OR LOWER(email) = :email)''',
            {'name': name.lower(), 'email': email.lower()}
        ).fetchone()

    def remaining_amount_due_in_cents(self, connection: Union[sqlite3.Cursor, sqlite3.Connection]):
        # TODO: not the most efficient but I have small data sets only anyway (less than 100 rows)
        return self.cents_due - Payment.sum_payments(connection, self.uuid)

    @classmethod
    def summary_by_date(cls, connection):
        return connection.execute(
            f"""SELECT date, SUM(places) FROM {cls.TABLE_NAME}
                WHERE active != 0 GROUP BY date ORDER BY date""")

    @classmethod
    def find_by_bank_id(cls, connection: Union[sqlite3.Cursor, sqlite3.Connection], bank_id: str) -> Union["Reservation", None]:
        row = connection.execute(
            f"""SELECT {','.join(col[0] for col in cls.COLUMNS)} FROM {cls.TABLE_NAME}
                WHERE bank_id = :bank_id""",
            {"bank_id": bank_id}).fetchone()
        return Reservation(*row) if row else None

    @classmethod
    def list_reservations_for_linking_with_payments(cls, connection, exclude_uuid: str) -> Iterable["Reservation"]:
        return [
            Reservation(*row) for row in connection.execute(
            f"""SELECT {','.join(col[0] for col in cls.COLUMNS)} FROM {cls.TABLE_NAME}
                WHERE active != 0 AND uuid != :uuid
                ORDER BY name""",
            {'uuid': exclude_uuid}).fetchall()]

    SORTABLE_COLUMNS = {'name': 'LOWER(name)',
                        'email': 'LOWER(email)',
                        'extra_comment': 'LOWER(extra_comment)',
                        'date': 'date',
                        'time': 'time',
                        'places': 'places',
                        'extra_starter': '(outside_extra_starter + inside_extra_starter)',
                        'main_starter': '(outside_main_starter + inside_main_starter)',
                        'bolo': '(outside_bolo + inside_bolo)',
                        'kids_bolo': 'kids_bolo',
                        'extra_dish': '(outside_extra_dish + inside_extra_dish)',
                        'kids_extra_dish': 'kids_extra_dish',
                        'dessert': '(outside_dessert + inside_bolo + inside_extra_dish + kids_bolo + kids_extra_dish)',
                        'origin': 'LOWER(origin)',
                        'active': 'active'}


    FILTERABLE_COLUMNS = {'name': MiniOrm.compare_with_like_lower('name'),
                          'email': MiniOrm.compare_with_like_lower('email'),
                          'extra_comment': MiniOrm.compare_with_like_lower('extra_comment'),
                          'date': True,
                          'bank_id': True,
                          'uuid': True,
                          'active': MiniOrm.compare_as_bool('active'),
                          'origin': ('LOWER(origin)', '=', str.lower),
                          'gdpr_accepts_use': MiniOrm.compare_as_bool('gdpr_accepts_use')}


class Payment(MiniOrm):
    TABLE_NAME = 'payments'
    COLUMNS = (
        ("rowid", "INTEGER NOT NULL PRIMARY KEY"),
        ("timestamp", "REAL"),
        ("amount_in_cents", "INTEGER NOT NULL"),
        ("comment", "TEXT"),
        ("uuid", "TEXT"),
        ("src_id", "TEXT NOT NULL"),
        ("other_account", "TEXT"),
        ("other_name", "TEXT"),
        ("status", "TEXT NOT NULL"),
        ("user", "TEXT NOT NULL"),
        ("ip", "TEXT NOT NULL"),
    )
    CREATION_STATEMENTS = [
        default_creation_statement(TABLE_NAME, COLUMNS),
        f"CREATE INDEX index_uuid_{TABLE_NAME} ON {TABLE_NAME} (uuid)",
        f"CREATE UNIQUE INDEX index_src_id_{TABLE_NAME} ON {TABLE_NAME} (src_id)",
    ]
    SORTABLE_COLUMNS = {
        'other_name': 'LOWER(other_name)',
        'other_account': 'LOWER(other_account)',
        'user': 'LOWER(user)',
        'comment': 'LOWER(comment)',
        'timestamp': 'timestamp',
        'amount_in_cents': 'amount_in_cents',
        'src_id': 'src_id',
        'ip': 'ip',
        'status': 'status',
    }
    FILTERABLE_COLUMNS = {
        'user': MiniOrm.compare_with_like_lower('user'),
        'comment': MiniOrm.compare_with_like_lower('comment'),
        'other_account': MiniOrm.compare_with_like_lower('other_account'),
        'other_name': MiniOrm.compare_with_like_lower('other_name'),
    }

    def __init__(self, rowid, timestamp, amount_in_cents, comment, uuid, src_id, other_account, other_name, status, user, ip):
        self.rowid = rowid
        self.timestamp = timestamp
        self.amount_in_cents = amount_in_cents
        self.comment = comment
        self.uuid = uuid
        self.src_id = src_id
        self.other_account = other_account
        self.other_name = other_name
        self.status = status
        self.user = user
        self.ip = ip

    def to_dict(self):
        return {
            "rowid": self.rowid,
            "timestamp": self.timestamp,
            "amount_in_cents": self.amount_in_cents,
            "comment": self.comment,
            "uuid": self.uuid,
            "src_id": self.src_id,
            "other_account": self.other_account,
            "other_name": self.other_name,
            "status": self.status,
            "user": self.user,
            "ip": self.ip,
        }

    @classmethod
    def find_by_src_id(cls, connection: Union[sqlite3.Cursor, sqlite3.Connection], src_id: str) -> Union["Payment", None]:
        row = connection.execute(
            f"""SELECT {','.join(col[0] for col in cls.COLUMNS)} FROM {cls.TABLE_NAME}
                WHERE src_id = :src_id""",
            {"src_id": src_id}).fetchone()
        return Payment(*row) if row else None

    EMPTY_DB_TIMESTAMP = 1706215670.0 # Arbitrary

    @classmethod
    def max_timestamp(cls, connection: Union[sqlite3.Cursor, sqlite3.Connection]) -> float:
        return connection.execute(
            f"""SELECT MAX(timestamp) FROM {cls.TABLE_NAME}"""
            ).fetchone()[0] or cls.EMPTY_DB_TIMESTAMP

    @classmethod
    def sum_payments(cls, connection, uuid):
        return connection.execute(
            f'''SELECT SUM(amount_in_cents) FROM {cls.TABLE_NAME} WHERE uuid = :uuid''',
            {"uuid": uuid}
        ).fetchone()[0] or 0

    def insert_data(self, connection) -> "Payment":
        connection.execute(
            f'''INSERT INTO {self.TABLE_NAME} VALUES (
                 :rowid, :timestamp, :amount_in_cents, :comment, :uuid, :src_id, :other_account, :other_name, :status, :user, :ip)''',
            self.to_dict())
        return self

    def money_received(self) -> bool:
        return self.status == "Accepté" and self.amount_in_cents is not None and self.amount_in_cents > 0

    @classmethod
    def join_reservations(cls, connection, filtering=None, order_columns=None, limit=None, offset=None):
        # Duplicate of `select', I know :sad:
        params = dict()
        query = [f'SELECT {",".join(f"pys.{col[0]}" for col in cls.COLUMNS)}, {",".join(f"res.{col[0]}" for col in Reservation.COLUMNS)} FROM {cls.TABLE_NAME} as pys LEFT OUTER JOIN {Reservation.TABLE_NAME} as res ON pys.uuid = res.uuid']
        if filtering is not None:
            clauses, extra_params = cls.where_clause(filtering)
            query.append(f'WHERE {clauses}')
            params.update(extra_params)
        if order_columns is not None:
            ordering = ','.join((y for y in (
                cls.column_ordering_clause(x) for x in order_columns)
                                if y is not None))
            if ordering:
                query.append(f'ORDER BY {ordering}')
        if limit is not None:
            query.append('LIMIT :limit')
            params['limit'] = limit
        if offset is not None:
            query.append('OFFSET :offset')
            params['offset'] = offset
        for row in connection.execute(' '.join(query), params):
            payment_row = row[:len(cls.COLUMNS)]
            reservation_row = row[len(cls.COLUMNS):]
            reservation = None if all(col is None or col == "" for col in reservation_row) else Reservation.from_row(reservation_row)
            yield cls.from_row(payment_row), reservation


class Csrf(MiniOrm):
    TABLE_NAME = 'csrfs'
    SESSION_IN_SECONDS = 7200
    COLUMNS = (
        ("token", "TEXT NOT NULL PRIMARY KEY"),
        ("timestamp", "REAL"),
        ("user", "TEXT NOT NULL"),
        ("ip", "TEXT NOT NULL"),
    )
    CREATION_STATEMENTS = [default_creation_statement(TABLE_NAME, COLUMNS)]

    def __init__(self, token=None, timestamp=None, user=None, ip=None):
        self.token = token or uuid.uuid4().hex
        self.timestamp = timestamp or time.time()
        self.user = user or os.getenv('REMOTE_USER')
        self.ip = ip or os.getenv('REMOTE_ADDR')


    @classmethod
    def gc(cls, connection):
        connection.execute(
            f'DELETE FROM {cls.TABLE_NAME} WHERE timestamp <= :timestamp',
            {'timestamp': time.time() - 3 * cls.SESSION_IN_SECONDS})

    def save(self, connection):
        with connection:
            connection.execute(
                f'INSERT OR REPLACE INTO {self.TABLE_NAME} VALUES '
                '(:token, :timestamp, :user, :ip)',
                {'token': self.token,
                 'timestamp': time.time(),
                 'user': self.user,
                 'ip': self.ip})
            self.gc(connection)


    @classmethod
    def new(cls, connection):
        result = cls()
        result.save(connection)
        return result


    @classmethod
    def validate_and_update(cls, connection, token, user, ip):
        try:
            data = connection.execute(
                f'SELECT * from {cls.TABLE_NAME} '
                'WHERE token = :token AND user = :user AND ip = :ip AND timestamp > :timestamp',
                {'token': token,
                 'user': user,
                 'ip': ip,
                 'timestamp': time.time() - cls.SESSION_IN_SECONDS}
            ).fetchone()
            result = cls(token=data[0], timestamp=data[1], user=data[2], ip=data[3])
            result.save(connection)
            return result
        except Exception:
            raise KeyError(token)


    @classmethod
    def get_by_user_and_ip(cls, connection, user, ip):
        try:
            data = connection.execute(
                f'SELECT * from {cls.TABLE_NAME} '
                'WHERE user = :user AND ip = :ip '
                'ORDER BY timestamp DESC '
                'LIMIT 1',
                {'user': user,
                 'ip': ip}
            ).fetchone()
            result = cls(token=data[0], timestamp=data[1], user=data[2], ip=data[3])
        except Exception:
            result = cls(user=user, ip=ip)
        result.save(connection)
        return result
