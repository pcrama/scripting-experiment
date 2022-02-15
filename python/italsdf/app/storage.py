# -*- coding: utf-8 -*-
import os
import sqlite3
import time
import uuid

def create_db(configuration):
    root_dir = configuration['dbdir']
    connection = sqlite3.connect(os.path.join(root_dir, 'db.db'))
    for table in (Csrf, Reservation):
        try:
            connection.execute(f'SELECT COUNT(*) FROM {table.TABLE_NAME}')
        except Exception as e:
            table.create_in_db(connection)
    return connection


def ensure_connection(connection_or_root_dir):
    return (connection_or_root_dir
            if hasattr(connection_or_root_dir, 'execute') else
            create_db(connection_or_root_dir))


class MiniOrm:
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
    def maybe_add_wildcards(x):
        return x if '%' in x else f'%{x}%'


    @staticmethod
    def compare_with_like_lower(x):
        return (f'LOWER({x})',
                'like',
                lambda val: MiniOrm.maybe_add_wildcards(val.lower()))


    @staticmethod
    def compare_as_bool(x):
        return (x, '=', lambda val: 1 if val else 0)



class Reservation(MiniOrm):
    TABLE_NAME = 'reservations'

    CREATION_STATEMENTS = [
        f'''CREATE TABLE {TABLE_NAME}
            (name TEXT NOT NULL,
             email TEXT,
             places INTEGER,
             date TEXT NOT NULL,
             fondus INTEGER,
             assiettes INTEGER,
             bolo INTEGER,
             scampis INTEGER,
             pannacotta INTEGER,
             tranches INTEGER,
             gdpr_accepts_use INTEGER,
             uuid TEXT NOT NULL,
             time REAL,
             active INTEGER,
             origin TEXT)''']

    def __init__(self,
                 name,
                 email,
                 places,
                 date,
                 fondus,
                 assiettes,
                 bolo,
                 scampis,
                 pannacotta,
                 tranches,
                 gdpr_accepts_use,
                 uuid,
                 time,
                 active,
                 origin):
        self.name = name
        self.email = email
        self.places = places
        self.date = date
        self.fondus = fondus
        self.assiettes = assiettes
        self.bolo = bolo
        self.scampis = scampis
        self.pannacotta = pannacotta
        self.tranches = tranches
        self.gdpr_accepts_use = gdpr_accepts_use
        self.uuid = uuid
        self.timestamp = time
        self.active = active
        self.origin = origin


    def to_dict(self):
        return {
            'name': self.name,
            'email': self.email,
            'places': self.places,
            'date': self.date,
            'fondus': self.fondus,
            'assiettes': self.assiettes,
            'bolo': self.bolo,
            'scampis': self.scampis,
            'pannacotta': self.pannacotta,
            'tranches': self.tranches,
            'gdpr_accepts_use': self.gdpr_accepts_use,
            'uuid': self.uuid,
            'time': self.timestamp,
            'active': self.active,
            'origin': self.origin}


    def insert_data(self, connection):
        connection.execute(
            f'''INSERT INTO {self.TABLE_NAME} VALUES (
                 :name, :email, :places, :date, :fondus, :assiettes, :bolo,
                 :scampis, :pannacotta, :tranches, :gdpr_accepts_use,
                 :uuid, :time, :active, :origin)''',
            self.to_dict())


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
            f'''SELECT COUNT(*), SUM(fondus + assiettes) FROM {cls.TABLE_NAME}
                WHERE active != 0 AND (LOWER(name) = :name OR LOWER(email) = :email)''',
            {'name': name.lower(), 'email': email.lower()}
        ).fetchone()


    @classmethod
    def count_main_meals(cls, connection, name, email):
        return connection.execute(
            f'''SELECT COUNT(*), SUM(bolo + scampis) FROM {cls.TABLE_NAME}
                WHERE active != 0 AND (LOWER(name) = :name OR LOWER(email) = :email)''',
            {'name': name.lower(), 'email': email.lower()}
        ).fetchone()


    @classmethod
    def count_desserts(cls, connection, name, email):
        return connection.execute(
            f'''SELECT COUNT(*), SUM(pannacotta + tranches) FROM {cls.TABLE_NAME}
                WHERE active != 0 AND (LOWER(name) = :name OR LOWER(email) = :email)''',
            {'name': name.lower(), 'email': email.lower()}
        ).fetchone()


    @classmethod
    def summary_by_date(cls, connection):
        return connection.execute(
            f"""SELECT date, SUM(places) FROM {cls.TABLE_NAME}
                WHERE active != 0 GROUP BY date ORDER BY date""")


    SORTABLE_COLUMNS = {'name': 'LOWER(name)',
                        'email': 'LOWER(email)',
                        'date': 'date',
                        'time': 'time',
                        'places': 'places',
                        'fondus': 'fondus',
                        'assiettes': 'assiettes',
                        'bolo': 'bolo',
                        'scampis': 'scampis',
                        'pannacotta': 'pannacotta',
                        'tranches': 'tranches',
                        'origin': 'LOWER(origin)',
                        'active': 'active'}


    FILTERABLE_COLUMNS = {'name': MiniOrm.compare_with_like_lower('name'),
                          'email': MiniOrm.compare_with_like_lower('email'),
                          'date': True,
                          'uuid': True,
                          'bank_id': ('bank_id', 'like'),
                          'active': MiniOrm.compare_as_bool('active'),
                          'origin': ('LOWER(origin)', '=', str.lower),
                          'gdpr_accepts_use': MiniOrm.compare_as_bool('gdpr_accepts_use')}


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


    @classmethod
    def select(cls, connection, filtering=None, order_columns=None, limit=None, offset=None):
        params = dict()
        query = [f'SELECT * FROM {cls.TABLE_NAME}']
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
            yield cls(
                name=row[0],
                email=row[1],
                places=row[2],
                date=row[3],
                fondus=row[4],
                assiettes=row[5],
                bolo=row[6],
                scampis=row[7],
                pannacotta=row[8],
                tranches=row[9],
                gdpr_accepts_use=row[10] != 0,
                uuid=row[11],
                time=row[12],
                active=row[13] != 0,
                origin=row[14])


class Csrf(MiniOrm):
    TABLE_NAME = 'csrfs'
    SESSION_IN_SECONDS = 7200
    CREATION_STATEMENTS = [
        f'''CREATE TABLE {TABLE_NAME}
            (token TEXT NOT NULL PRIMARY KEY,
             timestamp REAL,
             user TEXT NOT NULL,
             ip TEXT NOT NULL)''']

    def __init__(self, token=None, timestamp=None, user=None, ip=None):
        self.token = token or uuid.uuid4().hex
        self.timestamp = timestamp or time.time()
        self.user = user or os.getenv('REMOTE_USER')
        self.ip = ip or os.getenv('REMOTE_ADDR')


    @classmethod
    def gc(cls, connection):
        connection.execute(
            f'DELETE FROM {cls.TABLE_NAME} WHERE timestamp <= 0')


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
    def get(cls, connection, token):
        try:
            data = connection.execute(
                f'SELECT * from {cls.TABLE_NAME} '
                'WHERE token = :token AND timestamp > :timestamp',
                {'token': token,
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
