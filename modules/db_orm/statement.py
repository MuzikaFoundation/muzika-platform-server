from sqlalchemy import text


class Statement(object):
    """
    This class instance constructs a SQL statement.

    Ex.
    >>> Statement('users').where(user_id=3).select()
    SELECT * FROM `users` WHERE `user_id` = :user_id

    >>> Statement('users').columns('user_id', 'name').where(user_id=3).select()
    SELECT name FROM `users` WHERE `user_id` = :user_id

    >>> Statement('users').order('user_id', 'desc').order('last_login_time', 'desc').where(user_id=3).select()
    SELECT name FROM `users` WHERE `user_id` = :user_id ORDER `user_id` DESC, `last_login_time` DESC

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
        self._select_columns = []
        self._set_columns = {}
        self._where_columns = {}
        self._order_columns = []
        self._limit_cnt = 0

    def columns(self, *args):
        self._select_columns.extend(args)
        return self

    def set(self, **kwargs):
        self._set_columns.update(kwargs)
        return self

    def order(self, column, order):
        self._order_columns.append({
            'column': column,
            'order': order
        })
        return self

    def limit(self, limit_cnt):
        self._limit_cnt = limit_cnt
        return self

    def where(self, **kwargs):
        self._where_columns.update(kwargs)
        return self

    def select(self, connect):
        query = """
            SELECT {select_columns}
            FROM `{table_name}`
            {where_statement}
            {order_statement}
            {limit_statement}
        """.format(
            select_columns=self._select_column_part(*self._select_columns) if self._select_columns else '*',
            table_name=self.table_name,
            where_statement=self._where_part(**self._where_columns),
            order_statement=self._order_part(*self._order_columns) if self._order_columns else '',
            limit_statement=self._limit_part(self._limit_cnt) if self._limit_cnt else ''
        )
        return connect.execute(text(query), **self.fetch_params)

    def insert(self, connect):
        query = """
            INSERT INTO `{table_name}`
            SET
              {set_statement}
        """.format(table_name=self.table_name, set_statement=self._set_part(**self._set_columns))
        return connect.execute(text(query), **self.fetch_params)

    def update(self, connect):
        if len(self._where_columns) == 0:
            raise Exception('[Danger] Muzika DB ORM not allow no-where-condition update query!')

        query = """
            UPDATE `{table_name}`
            SET
              {set_statement}
            {where_statement}
            {order_statement}
            {limit_statement}
        """.format(
            table_name=self.table_name,
            set_statement=self._set_part(**self._set_columns),
            where_statement=self._where_part(**self._where_columns),
            order_statement=self._order_part(*self._order_columns) if self._order_columns else '',
            limit_statement=self._limit_part(self._limit_cnt) if self._limit_cnt else ''
        )
        return connect.execute(text(query), **self.fetch_params)

    def delete(self, connect):
        if len(self._where_columns) == 0:
            raise Exception('[Danger] Muzika DB ORM not allow no-where-condition delete query!')

        query = """
            DELETE FROM `{table_name}`
            {where_statement}
            {order_statement}
            {limit_statement}
        """.format(
            table_name=self.table_name,
            where_statement=self._where_part(**self._where_columns),
            order_statement=self._order_part(*self._order_columns) if self._order_columns else '',
            limit_statement=self._limit_part(self._limit_cnt) if self._limit_cnt else ''
        )
        return connect.execute(text(query), **self.fetch_params)

    @property
    def fetch_params(self):
        params = {}
        params.update({'set_{}'.format(key): value for key, value in self._set_columns.items()})
        params.update({'where_{}'.format(key): value for key, value in self._where_columns.items()})
        return params

    @staticmethod
    def _select_column_part(*args):
        return ', '.join(args)

    @staticmethod
    def _set_part(**kwargs):
        return ', '.join(['{} = :set_{}'.format(column, column) for column in kwargs])

    @staticmethod
    def _where_part_condition(column, value):
        if isinstance(value, list):
            return '`{}` IN :where_{}'.format(column, column)
        elif value is None:
            return '`{}` IS NULL'.format(column)
        else:
            return '`{}` = :where_{}'.format(column, column)

    @staticmethod
    def _where_part(**kwargs):
        if len(kwargs) == 0:
            return ''
        else:
            return ''.join(['WHERE ', ' AND '.join([Statement._where_part_condition(column, kwargs[column])
                                                    for column in kwargs])])

    @staticmethod
    def _order_part(*args):
        if len(args) == 0:
            return ''
        return 'ORDER {}'.format(', '.join(['{} {}'.format(row['column'], row['order']) for row in args]))

    @staticmethod
    def _limit_part(limit_cnt):
        if limit_cnt == 0:
            return ''
        return "LIMIT {}".format(limit_cnt)
