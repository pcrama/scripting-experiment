# -*- coding: utf-8 -*-
import itertools
import os
import sqlite3
import time
from typing import Any, Callable, Iterable, Iterator, Optional, TypeVar, Union
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
    FILTERABLE_COLUMNS: dict[str, Union[tuple[()], tuple[str, str, Callable[[Any], Any]]]] = {} # override with column info for `select'

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

    T = TypeVar("T", bound="MiniOrm")

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
    def column_ordering_clause(cls, col: str) -> Union[str, None]:
        try:
            clause = cls.SORTABLE_COLUMNS[col.lower()]
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
        

class KidMealCount:
    FIELD_NAMES = ['main_dish', 'extra_dish', 'third_dish', 'main_dessert', 'extra_dessert']
    def __init__(self, main_dish, extra_dish, third_dish, main_dessert, extra_dessert):
        self.main_dish = main_dish
        self.extra_dish = extra_dish
        self.third_dish = third_dish
        self.main_dessert = main_dessert
        self.extra_dessert = extra_dessert

    @classmethod
    def parse_from_row(cls, row):
        nb_fields = 5
        try:
            return cls(*row[:nb_fields]), row[nb_fields:]
        except Exception:
            return None, row

    def validate(self):
        errors = [
            f"{field_name} should be an int in the range 0 to 50, not {value!r}"
            for field_name, value in self.assoc_iterable()
            if not isinstance(value, int) or value < 0 or value > 50
        ]

        if errors:
            return errors

        dishes = self.count_dishes()
        desserts = self.count_desserts()
        if dishes != desserts:
            return [f"{dishes=} <> {desserts=}"]

        return []

    def count_dishes(self):
        return self.main_dish + self.extra_dish + self.third_dish

    def count_desserts(self):
        return self.main_dessert + self.extra_dessert

    def assoc_iterable(self):
        return zip(self.FIELD_NAMES, 
                   (self.main_dish, self.extra_dish, self.third_dish,
                    self.main_dessert, self.extra_dessert))
    
    def to_dict(self):
        return {k: v for k, v in self.assoc_iterable()}

    def make_into_row(self):
        return [
            self.main_dish,
            self.extra_dish,
            self.third_dish,
            self.main_dessert,
            self.extra_dessert,
        ]

    def __repr__(self):
        return f"{self.__class__.__name__}({self.main_dish!r}, {self.extra_dish!r}, {self.third_dish!r}, {self.main_dessert!r}, {self.extra_dessert!r})"


class FullMealCount:
    FIELD_NAMES = ['main_starter', 'extra_starter'] + KidMealCount.FIELD_NAMES
    def __init__(self, main_starter, extra_starter, main_dish, extra_dish, third_dish, main_dessert, extra_dessert):
        self.main_starter = main_starter
        self.extra_starter = extra_starter
        self.main_dish = main_dish
        self.extra_dish = extra_dish
        self.third_dish = third_dish
        self.main_dessert = main_dessert
        self.extra_dessert = extra_dessert

    @classmethod
    def parse_from_row(cls, row):
        nb_fields = 7
        try:
            return cls(*row[:nb_fields]), row[nb_fields:]
        except Exception:
            return None, row

    def make_into_row(self):
        return [self.main_starter, self.extra_starter, self.main_dish, self.extra_dish, self.third_dish, self.main_dessert, self.extra_dessert]

    def __repr__(self):
        return f"{self.__class__.__name__}({self.main_starter!r}, {self.extra_starter!r}, {self.main_dish!r}, {self.extra_dish!r}, {self.third_dish!r}, {self.main_dessert!r}, {self.extra_dessert!r})"

    def validate(self):
        return [
            f"{field_name} should be an int in the range 0 to 50, not {value!r}"
            for field_name, value in self.assoc_iterable()
            if not isinstance(value, int) or value < 0 or value > 50
        ]

    def count_starters(self):
        return self.main_starter + self.extra_starter

    def count_dishes(self):
        return self.main_dish + self.extra_dish + self.third_dish

    def count_desserts(self):
        return self.main_dessert + self.extra_dessert

    def assoc_iterable(self):
        return zip(self.FIELD_NAMES, 
                   (self.main_starter, self.extra_starter,
                    self.main_dish, self.extra_dish, self.third_dish,
                    self.main_dessert, self.extra_dessert))
    
    def to_dict(self):
        return {k: v for k, v in self.assoc_iterable()}


class MenuCount(FullMealCount):
    def validate(self):
        errors = super().validate()
        if errors:
            return errors

        starters = self.count_starters()
        dishes = self.count_dishes()
        desserts = self.count_desserts()
        if starters != dishes:
            return [f"{starters=} <> {dishes=}"]
        if dishes != desserts:
            return [f"{dishes=} <> {desserts=}"]

        return []
        

class Reservation(MiniOrm):
    TABLE_NAME = 'reservations'
    COLUMNS = [
        ("name", "TEXT NOT NULL"),
        ("email", "TEXT"),
        ("extra_comment", "TEXT"),
        ("places", "INTEGER CHECK(places > 0)"),
        ("date", "TEXT NOT NULL"),
        *((f"outside_{k}", "INTEGER") for k in FullMealCount.FIELD_NAMES),
        *((f"inside_{k}", "INTEGER") for k in MenuCount.FIELD_NAMES),
        *((f"kids_{k}", f"INTEGER CHECK(kids_{k} = 0)" if k in {"extra_dish", "third_dish"} else "INTEGER") for k in KidMealCount.FIELD_NAMES),
        # ("inside_extra_starter", "INTEGER CHECK(inside_extra_starter + inside_main_starter = inside_main_dish + inside_extra_dish)"),
        ("gdpr_accepts_use", "INTEGER"),
        ("cents_due", "INTEGER CHECK(cents_due >= 0)"),
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
                 outside: FullMealCount,
                 inside: MenuCount,
                 kids: KidMealCount,
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
        self.outside = outside
        self.inside = inside
        self.kids = kids
        self.gdpr_accepts_use = gdpr_accepts_use
        self.cents_due = cents_due
        self.bank_id = bank_id
        self.uuid = uuid
        self.timestamp = time
        self.active = active
        self.origin = origin


    @classmethod
    def parse_from_row(cls, row):
        prefix_len = 5
        suffix_len = 7
        if len(row) < prefix_len + suffix_len:
            return None, row

        try:
            prefix = row[:prefix_len]
            outside, tail = FullMealCount.parse_from_row(row[prefix_len:])
            if not outside:
                return None, row
            inside, tail = MenuCount.parse_from_row(tail)
            if not inside:
                return None, row
            kids, tail = KidMealCount.parse_from_row(tail)
            if not kids:
                return None, row
            if len(tail) < suffix_len:
                return None, row
            return cls(*prefix, outside, inside, kids, *tail[:suffix_len]), tail[suffix_len:]
        except Exception:
            return (None, row)


    def make_into_row(self):
        return [self.name,
                self.email,
                self.extra_comment,
                self.places,
                self.date,
                *self.outside.make_into_row(),
                *self.inside.make_into_row(),
                *self.kids.make_into_row(),
                self.gdpr_accepts_use,
                self.cents_due,
                self.bank_id,
                self.uuid,
                self.timestamp,
                self.active,
                self.origin]


    def assoc_iterable(self):
        return itertools.chain(
            (('name', self.name),
             ('email', self.email),
             ('extra_comment', self.extra_comment),
             ('places', self.places),
             ('date', self.date)),
            ((f"outside_{col}", val) for col, val in self.outside.assoc_iterable()),
            ((f"inside_{col}", val) for col, val in self.inside.assoc_iterable()),
            ((f"kids_{col}", val) for col, val in self.kids.assoc_iterable()),
            (('gdpr_accepts_use', self.gdpr_accepts_use),
             ('cents_due', self.cents_due),
             ('bank_id', self.bank_id),
             ('uuid', self.uuid),
             ('timestamp', self.timestamp),
             ('active', self.active),
             ('origin', self.origin)))
            
    def to_dict(self):
        return {k: v for k, v in self.assoc_iterable()}

    def insert_data(self, connection) -> "Reservation":
        connection.execute(
            f'''INSERT INTO {self.TABLE_NAME} VALUES (
                    {",".join(":" + name for name, _ in self.assoc_iterable())}
                )''',
            self.to_dict())
        return self

    def validate(self):
        return self.inside.validate() + self.outside.validate() + self.kids.validate()

    @classmethod
    def count_places(cls, connection, name: Optional[str]=None, email: Optional[str]=None) -> tuple[int, int]:
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
    def count_menu_data(cls, connection, date: Optional[str]=None) -> tuple[int, int, int, int, int, int, int, int, int, int, int]:
        if date is None:
            date_condition = ''
            bindings = {}
        else:
            date_condition = ' AND date = :date'
            bindings = {'date': date}
        return connection.execute(
            f'''SELECT COUNT(*), SUM(outside_main_starter + inside_main_starter), SUM(outside_extra_starter + inside_extra_starter), SUM(outside_main_dish + inside_main_dish), SUM(outside_extra_dish + inside_extra_dish), SUM(outside_third_dish + inside_third_dish), SUM(kids_main_dish), SUM(kids_extra_dish), SUM(kids_third_dish), SUM(outside_main_dessert + inside_main_dessert + kids_main_dessert), SUM(outside_extra_dessert + inside_extra_dessert + kids_extra_dessert) FROM {cls.TABLE_NAME}
                WHERE active != 0{date_condition}''',
            bindings
        ).fetchone()

    @classmethod
    def count_some_desserts(cls, connection, name: str, email: str, dessert_type: str) -> tuple[int, int]:
        return connection.execute(
            f'''SELECT COUNT(*), SUM(outside_{dessert_type}_dessert + inside_{dessert_type}_dessert + kids_{dessert_type}_dessert) FROM {cls.TABLE_NAME}
                WHERE active != 0 AND (LOWER(name) = :name OR LOWER(email) = :email)''',
            {'name': name.lower(), 'email': email.lower()}
        ).fetchone()

    @classmethod
    def count_main_desserts(cls, connection, name: str, email: str) -> tuple[int, int]:
        return cls.count_some_desserts(connection, name, email, 'main')

    @classmethod
    def count_extra_desserts(cls, connection, name: str, email: str) -> tuple[int, int]:
        return cls.count_some_desserts(connection, name, email, 'extra')

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
                        'extra_comment': 'LOWER(extra_comment)',
                        'date': 'date',
                        'time': 'time',
                        'places': 'places',
                        'extra_starter': '(outside_extra_starter + inside_extra_starter)',
                        'main_starter': '(outside_main_starter + inside_main_starter)',
                        'main_dish': '(outside_main_dish + inside_main_dish)',
                        'kids_main_dish': 'kids_main_dish',
                        'extra_dish': '(outside_extra_dish + inside_extra_dish)',
                        'kids_extra_dish': 'kids_extra_dish',
                        'third_dish': '(outside_third_dish + inside_third_dish)',
                        'kids_third_dish': 'kids_third_dish',
                        'main_dessert': '(outside_main_dessert + inside_main_dessert + kids_main_dessert)',
                        'extra_dessert': '(outside_extra_dessert + inside_extra_dessert + kids_extra_dessert)',
                        'origin': 'LOWER(origin)',
                        'active': 'active'}


    FILTERABLE_COLUMNS = {'name': MiniOrm.compare_with_like_lower('name'),
                          'email': MiniOrm.compare_with_like_lower('email'),
                          'extra_comment': MiniOrm.compare_with_like_lower('extra_comment'),
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
        ("src_id", "TEXT NOT NULL"),
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
        'active': MiniOrm.compare_as_bool('active'),
    }

    def __init__(self, rowid, timestamp, amount_in_cents, comment, uuid, src_id, other_account, other_name, status, user, ip, confirmation_timestamp, active):
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
        self.confirmation_timestamp = confirmation_timestamp
        self.active = active

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
        cursor = connection.cursor()
        cursor.execute(
            f'''INSERT INTO {self.TABLE_NAME} VALUES (
                 :rowid, :timestamp, :amount_in_cents, :comment, :uuid, :src_id, :other_account, :other_name, :status, :user, :ip, :confirmation_timestamp, :active)
             ''',
            self.to_dict())
        self.rowid = cursor.lastrowid
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
            payment, reservation_row = cls.parse_from_row(row)
            if not payment:
                raise RuntimeError("Unable to create Payment from DB data")
            if all(col is None or col == "" for col in reservation_row):
                reservation = None
            else:
                reservation, tail = Reservation.parse_from_row(reservation_row)
                if not reservation or tail:
                    raise RuntimeError(f"Unable to create Reservation from DB data joined to Payment({payment.src_id})")
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
        self.user = user or os.environ['REMOTE_USER']
        self.ip = ip or os.environ['REMOTE_ADDR']


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
            result = cls(token=data[0], timestamp=time.time(), user=data[2], ip=data[3])
        except Exception:
            result = cls(user=user, ip=ip)
        result.save(connection)
        return result
