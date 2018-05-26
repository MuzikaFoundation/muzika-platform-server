from sqlalchemy import text


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

    def select(self, connect):
        query = """
            SELECT {select_columns}
            FROM `{table_name}`
            {where_statement}
        """.format(
            select_columns=self._select_column_part(*self.select_columns) if self.select_columns else '*',
            table_name=self.table_name,
            where_statement=self._where_part(**self.where_columns)
        )
        return connect.execute(text(query), **self.fetch_params)

    def insert(self, connect):
        query = """
            INSERT INTO `{table_name}`
            SET
              {set_statement}
        """.format(table_name=self.table_name, set_statement=self._set_part(**self.set_columns))
        return connect.execute(text(query), **self.fetch_params)

    def update(self, connect):
        query = """
            UPDATE `{table_name}`
            SET
              {set_statement}
            {where_statement}
        """.format(
            table_name=self.table_name,
            set_statement=self._set_part(**self.set_columns),
            where_statement=self._where_part(**self.where_columns)
        )
        return connect.execute(text(query), **self.fetch_params)

    def delete(self, connect):
        query = """
            DELETE FROM `{table_name}`
            {where_statement}
        """.format(
            table_name=self.table_name,
            where_statement=self._where_part(**self.where_columns)
        )
        return connect.execute(text(query), **self.fetch_params)

    @property
    def fetch_params(self):
        params = {}
        params.update({'set_{}'.format(key): value for key, value in self.set_columns.items()})
        params.update({'where_{}'.format(key): value for key, value in self.where_columns.items()})
        return params

    @staticmethod
    def _select_column_part(*args):
        return ', '.join(args)

    @staticmethod
    def _set_part(**kwargs):
        return ', '.join(['{} = :set_{}'.format(column, column) for column in kwargs])

    @staticmethod
    def _where_part(**kwargs):
        if len(kwargs) == 0:
            return ''
        else:
            return ''.join(['WHERE ', ' AND '.join(['`{}` = :where_{}'.format(column, column) for column in kwargs])])
