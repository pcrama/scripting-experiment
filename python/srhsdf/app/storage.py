# -*- coding: utf-8 -*-
import os
import sqlite3
import time
from typing import Any, Callable, Generator, Iterable, Iterator, Optional, TypeVar, Union
import uuid


def create_db(configuration: dict[str, Any]) -> sqlite3.Connection:
    root_dir = configuration['dbdir']
    connection = sqlite3.connect(
        root_dir if root_dir == ':memory:' else os.path.join(root_dir, 'db.db'))
    for table in (Csrf, Reservation, Payment):
        try:
            connection.execute(f'SELECT COUNT(*) FROM {table.TABLE_NAME}')
        except Exception:
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
    COLUMNS: list[tuple[str, str]]
    SORTABLE_COLUMNS: dict[str, str] = {} # override with column info for `select'

    FILTERABLE_COLUMNS: dict[str, Union[tuple[()], tuple[str, str, Callable]]] = {} # override with column info for `select'

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

    def assoc_iterable(self) -> Iterator[tuple[str, Any]]:
        return zip((col[0] for col in self.COLUMNS), (getattr(self, col[0]) for col in self.COLUMNS))

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.assoc_iterable()}

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
    def compare_as_bool(x: str) -> tuple[str, str, Callable[[Any], int]]:
        return (x, '=', lambda val: 1 if val else 0)

    T = TypeVar("T", bound="MiniOrm")

    @classmethod
    def select(cls: type[T], connection, filtering=None, order_columns=None, limit=None, offset=None) -> Generator[T, None, None]:
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
    def parse_from_row(cls: type[T], row: list[Any]) -> tuple[Union[T, None], list[Any]]:
        nb_cols = len(cls.COLUMNS)
        if len(row) >= nb_cols:
            return cls(*row[:nb_cols]), row[nb_cols:]
        return (None, row)

    def make_into_row(self) -> list[Any]:
        return []

    @classmethod
    def from_row(cls: type[T], row: list[Any]) -> T:
        obj, tail = cls.parse_from_row(row)
        if obj and not tail:
            return obj
        raise RuntimeError(f"Can't turn {row} into a {cls.__name__}")

    @classmethod
    def column_ordering_clause(cls, col: str, table_id_prefix: Union[str, None]=None) -> Union[str, None]:
        if table_id_prefix and not table_id_prefix.endswith('.'):
            table_id_prefix += '.'
        else:
            table_id_prefix = ''
        try:
            clause = cls.SORTABLE_COLUMNS[col.lower()]
            lower_clause = clause.lower()
            for known_sql_func in ('upper(', 'lower('):
                if lower_clause.startswith(known_sql_func):
                    clause = clause[0:len(known_sql_func)] + table_id_prefix + clause[len(known_sql_func):]
                    break
            else:
                clause = table_id_prefix + clause
            asc_or_desc = 'DESC' if col[0].isupper() else 'ASC'
            return f'{clause} {asc_or_desc}'
        except KeyError:
            return None

    @classmethod
    def encode_column_value_for_search(cls, col: str, val: Any, info: Union[tuple[()], tuple[str, str, Callable]]):
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
    def where_clause(cls, filtering, table_id_prefix=""):
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
            clauses.append(f'{table_id_prefix}{col_value} {operator} :{var_name}')
        if clauses:
            return ('(' + ' AND '.join(clauses) + ')', params)
        else:
            return ([], {})


class Reservation(MiniOrm):
    TABLE_NAME = 'reservations'
    COLUMNS = [
        ("name", "TEXT NOT NULL"),
        ("email", "TEXT"),
        ("date", "TEXT NOT NULL"),
        ("paying_seats", "INTEGER"),
        ("free_seats", "INTEGER"),
        ("gdpr_accepts_use", "INTEGER"),
        ("cents_due", "INTEGER CHECK(cents_due >= 0)"),
        ("bank_id", "TEXT NOT NULL"),
        ("uuid", "TEXT NOT NULL"),
        ("timestamp", "REAL"),
        ("active", "INTEGER"),
        ("origin", "TEXT"),
    ]
    CREATION_STATEMENTS = [
        default_creation_statement(TABLE_NAME, COLUMNS),
        f'CREATE UNIQUE INDEX index_bank_id_{TABLE_NAME} ON {TABLE_NAME} (bank_id)',
        f'CREATE UNIQUE INDEX index_uuid_{TABLE_NAME} ON {TABLE_NAME} (uuid)']

    def __init__(self, name, email, date, paying_seats, free_seats, gdpr_accepts_use, cents_due, bank_id, uuid, timestamp, active, origin):
        # !!! Keep in sync with COLUMNS if you want to use the default !!!
        # !!! from_row implementation !!!
        self.name = name
        self.email = email
        self.date = date
        self.paying_seats = paying_seats
        self.free_seats = free_seats
        self.gdpr_accepts_use = gdpr_accepts_use
        self.cents_due = cents_due
        self.bank_id = bank_id
        self.uuid = uuid
        self.timestamp = timestamp
        self.active = active
        self.origin = origin

    def insert_data(self, connection) -> "Reservation":
        connection.execute(
            f'''INSERT INTO {self.TABLE_NAME} VALUES (
                    {",".join(":" + name for name, _ in self.assoc_iterable())}
                )''',
            self.to_dict())
        return self

    @classmethod
    def count_reservations(cls, connection: Union[sqlite3.Cursor, sqlite3.Connection], name: str, email: str) -> tuple[int, int]:
        return connection.execute(
            f'''SELECT COUNT(*), SUM(paying_seats + free_seats) FROM {cls.TABLE_NAME}
                WHERE LOWER(name) = :name OR LOWER(email) = :email''',
            {'name': name.lower(), 'email': email.lower()}
        ).fetchone()

    def remaining_amount_due_in_cents(self, connection: Union[sqlite3.Cursor, sqlite3.Connection]):
        # TODO: not the most efficient but I have small data sets only anyway (less than 100 rows)
        return self.cents_due - Payment.sum_payments(connection, self.uuid)

    @classmethod
    def summary_by_date(cls, connection):
        return connection.execute(
            f"""SELECT date, SUM(paying_seats + free_seats) FROM {cls.TABLE_NAME}
                WHERE active != 0 GROUP BY date ORDER BY date""")

    @classmethod
    def find_by_bank_id(cls, connection: Union[sqlite3.Cursor, sqlite3.Connection], bank_id: str) -> Union["Reservation", None]:
        row = connection.execute(
            f"""SELECT {','.join(col[0] for col in cls.COLUMNS)} FROM {cls.TABLE_NAME}
                WHERE bank_id = :bank_id""",
            {"bank_id": bank_id}).fetchone()
        return Reservation.from_row(row) if row else None

    @classmethod
    def find_by_uuid(cls, connection: Union[sqlite3.Cursor, sqlite3.Connection], uuid: str) -> Union["Reservation", None]:
        row = connection.execute(
            f"""SELECT {','.join(col[0] for col in cls.COLUMNS)} FROM {cls.TABLE_NAME}
                WHERE uuid = :uuid""",
            {"uuid": uuid}).fetchone()
        return Reservation.from_row(row) if row else None

    @classmethod
    def list_reservations_for_linking_with_payments(cls, connection, exclude_uuid: str) -> Iterable["Reservation"]:
        return [
            Reservation.from_row(row) for row in connection.execute(
            f"""SELECT {','.join(col[0] for col in cls.COLUMNS)} FROM {cls.TABLE_NAME}
                WHERE active != 0 AND uuid != :uuid
                ORDER BY name""",
            {'uuid': exclude_uuid}).fetchall()]

    SORTABLE_COLUMNS = {'name': 'LOWER(name)',
                        'email': 'LOWER(email)',
                        'date': 'date',
                        'time': 'time',
                        'paying_seats': 'paying_seats',
                        'free_seats': 'free_seats',
                        'bank_id': 'bank_id',
                        'origin': 'LOWER(origin)',
                        'active': 'active'}


    FILTERABLE_COLUMNS = {'name': MiniOrm.compare_with_like_lower('name'),
                          'email': MiniOrm.compare_with_like_lower('email'),
                          'date': (),
                          'bank_id': (),
                          'uuid': (),
                          'active': MiniOrm.compare_as_bool('active'),
                          # 'origin': ('LOWER(origin)', '=', str.lower),
                          'gdpr_accepts_use': MiniOrm.compare_as_bool('gdpr_accepts_use')}


class Payment(MiniOrm):
    TABLE_NAME = 'payments'
    COLUMNS = [
        ("rowid", "INTEGER NOT NULL PRIMARY KEY"),
        ("timestamp", "REAL"),
        ("amount_in_cents", "INTEGER NOT NULL"),
        ("comment", "TEXT"),
        ("uuid", "TEXT"),
        # sometimes, payments appear wihtout src_id and it takes hours and a new download to get the real value
        ("src_id", "TEXT"),
        ("bank_ref", "TEXT NOT NULL"),
        ("other_account", "TEXT"),
        ("other_name", "TEXT"),
        ("status", "TEXT NOT NULL"),
        ("user", "TEXT NOT NULL"),
        ("ip", "TEXT NOT NULL"),
        ("confirmation_timestamp", "REAL"),
        ("active", "INTEGER"),
    ]
    CREATION_STATEMENTS = [
        default_creation_statement(TABLE_NAME, COLUMNS),
        f"CREATE INDEX index_uuid_{TABLE_NAME} ON {TABLE_NAME} (uuid)",
        f"CREATE INDEX index_src_id_{TABLE_NAME} ON {TABLE_NAME} (src_id)",
        f"CREATE UNIQUE INDEX index_bank_ref_{TABLE_NAME} ON {TABLE_NAME} (bank_ref)",
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
        'active': MiniOrm.compare_as_bool('active'),
    }

    def __init__(self, rowid, timestamp, amount_in_cents, comment, uuid, src_id, bank_ref, other_account, other_name, status, user, ip, confirmation_timestamp, active):
        self.rowid = rowid
        self.timestamp = timestamp
        self.amount_in_cents = amount_in_cents
        self.comment = comment
        self.uuid = uuid
        self.src_id = src_id
        self.bank_ref = bank_ref
        self.other_account = other_account
        self.other_name = other_name
        self.status = status
        self.user = user
        self.ip = ip
        self.confirmation_timestamp = confirmation_timestamp
        self.active = active

    @classmethod
    def find_by_bank_ref(cls, connection: Union[sqlite3.Cursor, sqlite3.Connection], bank_ref: str) -> Union["Payment", None]:
        row = connection.execute(
            f"""SELECT {','.join(col[0] for col in cls.COLUMNS)} FROM {cls.TABLE_NAME} WHERE bank_ref = :bank_ref""",
            {"bank_ref": bank_ref}).fetchone()
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
        cursor = connection.cursor()
        cursor.execute(
            f'''INSERT INTO {self.TABLE_NAME} VALUES (
                 :rowid, :timestamp, :amount_in_cents, :comment, :uuid, :src_id, :bank_ref, :other_account, :other_name, :status, :user, :ip, :confirmation_timestamp, :active)
             ''',
            self.to_dict())
        self.rowid = cursor.lastrowid
        return self

    def update_src_id(self, connection, src_id:str) -> "Payment":
        self.src_id = src_id
        connection.execute(
            f'''UPDATE {self.TABLE_NAME} SET src_id = :src_id WHERE rowid = :rowid''',
            {"src_id": self.src_id, "rowid": self.rowid})
        return self

    def update_confirmation_timestamp(self, connection, confirmation_timestamp: Optional[float]) -> "Payment":
        self.confirmation_timestamp = confirmation_timestamp
        connection.execute(
            f'''UPDATE {self.TABLE_NAME} SET confirmation_timestamp = :confirmation_timestamp
                WHERE rowid = :rowid''',
            {"confirmation_timestamp": self.confirmation_timestamp,
             "rowid": self.rowid})
        return self

    def update_uuid(self, connection, uuid: Union[str, None], user: str, ip: str) -> "Payment":
        if not user or not ip:
            raise ValueError(f"{user=} and {ip=} are mandatory")
        self.uuid = uuid
        self.user = user
        self.ip = ip
        self.timestamp = time.time()
        connection.execute(
            f'''UPDATE {self.TABLE_NAME} SET uuid = :uuid, user = :user, ip = :ip, timestamp = :timestamp, confirmation_timestamp = NULL
                WHERE rowid = :rowid''',
            {"uuid": self.uuid if self.uuid else None,
             "user": self.user,
             "ip": self.ip,
             "timestamp": self.timestamp,
             "rowid": self.rowid})
        return self

    def hide(self, connection, user: str, ip: str) -> "Payment":
        if not user or not ip:
            raise ValueError(f"{user=} and {ip=} are mandatory")
        self.active = False
        self.user = user
        self.ip = ip
        self.timestamp = time.time()
        connection.execute(
            f'''UPDATE {self.TABLE_NAME} SET active = 0, user = :user, ip = :ip, timestamp = :timestamp
                WHERE rowid = :rowid''',
            {"user": self.user,
             "ip": self.ip,
             "timestamp": self.timestamp,
             "rowid": self.rowid})
        return self

    def money_received(self) -> bool:
        return self.status == "Accepté" and self.amount_in_cents is not None and self.amount_in_cents > 0

    @classmethod
    def join_reservations(cls, connection, filtering=None, order_columns=None, limit=None, offset=None):
        # Duplicate of `select', I know :sad:
        params = dict()
        query = [f'SELECT {",".join(f"pys.{col[0]}" for col in cls.COLUMNS)}, {",".join(f"res.{col[0]}" for col in Reservation.COLUMNS)} FROM {cls.TABLE_NAME} as pys LEFT OUTER JOIN {Reservation.TABLE_NAME} as res ON pys.uuid = res.uuid']
        if filtering is not None:
            clauses, extra_params = cls.where_clause(filtering, table_id_prefix="pys.")
            query.append(f'WHERE {clauses}')
            params.update(extra_params)
        if order_columns is not None:
            ordering = ','.join((y for y in (
                cls.column_ordering_clause(x, table_id_prefix='pys') for x in order_columns)
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
            payment, reservation_row = cls.parse_from_row(row)
            if not payment:
                raise RuntimeError("Unable to create Payment from DB data")
            if all(col is None or col == "" for col in reservation_row):
                reservation = None
            else:
                reservation, tail = Reservation.parse_from_row(reservation_row)
                if not reservation or tail:
                    indic = f"src_id={payment.src_id!r}" if payment.src_id else f"bank_ref={payment.bank_ref!r}"
                    raise RuntimeError(f"Unable to create Reservation from DB data joined to Payment({indic})")
            yield payment, reservation


class Csrf(MiniOrm):
    TABLE_NAME = 'csrfs'
    SESSION_IN_SECONDS = 7200
    COLUMNS = [
        ("token", "TEXT NOT NULL PRIMARY KEY"),
        ("timestamp", "REAL"),
        ("user", "TEXT NOT NULL"),
        ("ip", "TEXT NOT NULL"),
    ]
    CREATION_STATEMENTS = [default_creation_statement(TABLE_NAME, COLUMNS)]
    token: str
    timestamp: float
    user: str
    ip: str

    def __init__(self, token=None, timestamp=None, user=None, ip=None):
        self.token = token or uuid.uuid4().hex
        self.timestamp = timestamp or time.time()
        self.user = user or os.getenv('REMOTE_USER')
        self.ip = ip or os.getenv('REMOTE_ADDR')


    @classmethod
    def gc(cls, connection) -> None:
        connection.execute(
            f'DELETE FROM {cls.TABLE_NAME} WHERE timestamp <= :timestamp',
            {'timestamp': time.time() - 3 * cls.SESSION_IN_SECONDS})

    def save(self, connection) -> None:
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
    def new(cls, connection) -> "Csrf":
        result = cls()
        result.save(connection)
        return result


    @classmethod
    def validate_and_update(cls, connection, token: str, user: str, ip: str) -> "Csrf":
        try:
            data = connection.execute(
                f'SELECT * from {cls.TABLE_NAME} '
                'WHERE token = :token AND user = :user AND ip = :ip AND timestamp > :timestamp',
                {'token': token,
                 'user': user,
                 'ip': ip,
                 'timestamp': time.time() - cls.SESSION_IN_SECONDS}
            ).fetchone()
            result = cls(token=data[0], timestamp=time.time(), user=data[2], ip=data[3])
            result.save(connection)
            return result
        except Exception:
            raise KeyError(token)

    @classmethod
    def get_by_user_and_ip(cls, connection, user: str, ip: str) -> "Csrf":
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
