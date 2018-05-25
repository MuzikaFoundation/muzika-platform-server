
"""
 Use muzika database.

 For using database for read-only,
 >>> with engine_rdonly.connect() as connection:
 >>>     ...

 For using database for read-writable,
 >>> with engine_rdwr.connect() as connection:
 >>>     ...

"""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import RowProxy, ResultProxy
from sqlalchemy.engine.url import URL

from modules.secret import load_secret_json

__all__ = [
    'engine_rdonly', 'engine_rdwr'
]

db_secret = load_secret_json('database')

try:
    rdonly_db_url = URL(**db_secret['db_rdonly'])
except KeyError:
    rdonly_db_url = URL(**db_secret['db_rdwr'])
rdwr_db_url = URL(**db_secret['db_rdwr'])

# define database engines
engine_rdonly = create_engine(rdonly_db_url, encoding='utf-8', pool_recycle=290)
engine_rdwr = create_engine(rdwr_db_url, encoding='utf-8', pool_recycle=290)


def to_relation_model(row: RowProxy):
    """
    Returns a dict that represents a row in database. Since a row can be related with other table, it can be
    represented like

    {
      "model_id": 1,
      ...

      "other_relation": {
        "other_relation_id": 4
        ...
      }
    }

    Write SQL query as

    SELECT `a`.*, "!b", `b`.* FROM `a_table`
        INNER JOIN `b_table`
        ON (...)
        ...
    ...

    And the function that has the parameter with the RowProxy instance which is the result row from SQLAlchemy
    execution, it returns a dict like

    {
      "a_column_1": ..
      "a_column_2": ..
      "b": {
        "b_column_1": ..
        "b_column_2": ..
        ...
      }
      ...
    }
    """
    builder = {}
    sub = {}
    current = None

    if isinstance(row, RowProxy):
        columns = list(zip(row.keys(), row))
    elif row is None:
        return None

    for key, value in row:
        if key[0] == '!':
            if current is None:
                builder.update(sub)
            else:
                builder.update({current: sub})
            sub = {}
            current = key[1:]

        else:
            sub.update({key: value})

    if current is None:
        builder.update(sub)
    else:
        builder.update({current: sub})

    return builder


def to_relation_model_list(rows: ResultProxy):
    return [to_relation_model(r) for r in rows]


class Statement(object):
    """
    This class instance constructs a SQL statement.

    Ex.
    >>> Statement('users').where(user_id=3).select()
    SELECT * FROM `users` WHERE `user_id` = :user_id

    >>> Statement('users').columns('user_id', 'name').where(user_id=3).select()
    SELECT name FROM `users` WHERE `user_id` = :user_id

    >>> s = Statement('users').set(name='test', test=123).where(user_id=3).update()
    UPDATE `users` SET name = :name, test = :test WHERE user_id = :user_id

    >>> s.fetch_params
    {'name': 'test', 'test': 123, 'user_id': 3}

    # TODO : conflict if the same key exists in set and where columns
    Never use the same column in set and where columns like at present.
    >>> Statement('users').set(user_id=4).where(user_id=3).update()
    """
    def __init__(self, table_name):
        self.table_name = table_name
        self.select_columns = []
        self.set_columns = {}
        self.where_columns = {}

    def columns(self, *args):
        self.select_columns.extend(args)
        return self

    def set(self, **kwargs):
        self.set_columns.update(kwargs)
        return self

    def where(self, **kwargs):
        self.where_columns.update(kwargs)
        return self

    def select(self):
        return """
            SELECT {select_columns}
            FROM `{table_name}`
            {where_statement}
        """.format(
            select_columns=self._select_column_part(*self.select_columns) if self.select_columns else '*',
            table_name=self.table_name,
            where_statement=self._where_part(**self.where_columns)
        )

    def insert(self):
        return """
            INSERT INTO `{table_name}`
            SET
              {set_statement}
        """.format(table_name=self.table_name, set_statement=self._set_part(**self.set_columns))

    def update(self):
        return """
            UPDATE `{table_name}`
            SET
              {set_statement}
            {where_statement}
        """.format(
            table_name=self.table_name,
            set_statement=self._set_part(**self.set_columns),
            where_statement=self._where_part(**self.where_columns)
        )

    def delete(self):
        return """
            DELETE FROM `{table_name}`
            {where_statement}
        """.format(
            table_name=self.table_name,
            where_statement=self._where_part(**self.where_columns)
        )

    @property
    def fetch_params(self):
        params = {}
        params.update(self.set_columns)
        params.update(self.where_columns)
        return params

    @staticmethod
    def _select_column_part(*args):
        return ', '.join(args)

    @staticmethod
    def _set_part(**kwargs):
        return ', '.join(['{} = :{}'.format(column, column) for column in kwargs])

    @staticmethod
    def _where_part(**kwargs):
        if len(kwargs) == 0:
            return ''
        else:
            return ''.join(['WHERE ', ' AND '.join(['{} = :{}'.format(column, column) for column in kwargs])])