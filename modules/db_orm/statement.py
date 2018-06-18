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
        self._join_mode = False
        self._join_columns = []

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

    def inner_join(self, table, on):
        return self.join(table, on, 'inner')

    def left_join(self, table, on):
        return self.join(table, on, 'left')

    def join(self, table, on, join_type):
        # .inner_join('users', 'user_id')
        # .inner_join(('music_contracts', 'music_payments'),
        #             'contract_address')
        # .inner_join(('users', 'music_payments'),
        #             ('user_id', 'payer_id'))

        #
        # .inner_join('users',
        #             ('user_id', 'owner_id'))

        self._join_mode = True
        self._join_columns.append({
            'join_type': join_type,
            'left_table': table[0] if isinstance(table, tuple) else table,
            'left_on': on[0] if isinstance(on, tuple) else on,
            'right_table': table[1] if isinstance(table, tuple) else self.table_name,
            'right_on': on[1] if isinstance(on, tuple) else on
        })
        return self

    def limit(self, limit_cnt):
        self._limit_cnt = limit_cnt
        return self

    def where(self, **kwargs):
        return self.where_advanced(self.table_name, **kwargs)

    def where_advanced(self, table, **kwargs):
        if table not in self._where_columns:
            self._where_columns[table] = {}
        self._where_columns[table].update(kwargs)
        return self

    def select(self, connect, execute=True):
        query = """
            SELECT {select_columns}
            FROM {table_name}
            {join_statement}
            {where_statement}
            {order_statement}
            {limit_statement}
        """.format(
            select_columns=self._select_column_part(*self._select_columns),
            table_name=self._get_table(),
            join_statement=self._join_part(),
            where_statement=self._where_part(),
            order_statement=self._order_part(*self._order_columns) if self._order_columns else '',
            limit_statement=self._limit_part(self._limit_cnt) if self._limit_cnt else ''
        )
        return connect.execute(text(query), **self.fetch_params) if execute is True else query

    def insert(self, connect, execute=True):
        query = """
            INSERT INTO {table_name} SET {set_statement}
        """.format(table_name=self._get_table(), set_statement=self._set_part(**self._set_columns))
        return connect.execute(text(query), **self.fetch_params)

    def update(self, connect, execute=True):
        if len(self._where_columns) == 0:
            raise Exception('[Danger] Muzika DB ORM not allow no-where-condition update query!')

        query = """
            UPDATE {table_name}
            SET
              {set_statement}
            {where_statement}
            {order_statement}
            {limit_statement}
        """.format(
            table_name=self._get_table(),
            set_statement=self._set_part(**self._set_columns),
            where_statement=self._where_part(),
            order_statement=self._order_part(*self._order_columns) if self._order_columns else '',
            limit_statement=self._limit_part(self._limit_cnt) if self._limit_cnt else ''
        )
        return connect.execute(text(query), **self.fetch_params) if execute is True else query

    def delete(self, connect, execute=True):
        if len(self._where_columns) == 0:
            raise Exception('[Danger] Muzika DB ORM not allow no-where-condition delete query!')

        query = """
            DELETE FROM {table_name}
            {where_statement}
            {order_statement}
            {limit_statement}
        """.format(
            table_name=self._get_table(),
            where_statement=self._where_part(),
            order_statement=self._order_part(*self._order_columns) if self._order_columns else '',
            limit_statement=self._limit_part(self._limit_cnt) if self._limit_cnt else ''
        )
        return connect.execute(text(query), **self.fetch_params) if execute is True else query

    @property
    def fetch_params(self):
        params = {}
        params.update({'set_{}'.format(self._column_parse(key)[0]): value for key, value in self._set_columns.items()})
        for table, columns in self._where_columns.items():
            params.update({'where_{}'.format(self._column_parse(key)[0]): value for key, value in columns.items()})
        return params

    @staticmethod
    def _get_table_alias(table):
        return ''.join([word[0] for word in table.split('_')])

    def _get_table(self, table=None):
        if table is None:
            table = self.table_name

        if self._join_mode is True:
            return '`{}` `{}`'.format(table, self._get_table_alias(table))
        else:
            return '`{}`'.format(table)

    def _select_column_part(self, *args):
        if not args:
            args = ['*']
        return ', '.join([self._column_parse(column)[0] for column in args])

    # variable 'column' could be tuple or string. ex) tuple(table, column) or column
    def _column_parse(self, column):
        if self._join_mode is True:  # If ORM include Join condition
            table = self.table_name if not isinstance(column, tuple) else column[0]
            table_alias = self._get_table_alias(table)

            if not isinstance(column, tuple):
                column = column
                if column[0] == '!':
                    return "'{}'".format(column), column
            else:
                column = column[1]
            column_name = '`{}`.{}'.format(table_alias, column)
            column_param = '{}_{}'.format(table_alias, column)
        else:
            column_name = '{}'.format(column)
            column_param = column

        return column_name, column_param

    def _join_part(self):
        join_query = []
        for condition in self._join_columns:
            where_conditions = '{} = {}'.format(self._column_parse((condition.get('left_table'),
                                                                    condition.get('left_on')))[0],
                                                self._column_parse((condition.get('right_table'),
                                                                    condition.get('right_on')))[0])
            join_query.append('{} JOIN {} ON ({})'.format(condition.get('join_type').upper(),  # INNER or LEFT
                                                          self._get_table(condition.get('left_table')),
                                                          # define alias table
                                                          where_conditions))  # ON condition
        return ' '.join(join_query)

    def _set_part(self, **kwargs):
        return ', '.join(['{} = :set_{}'.format(*self._column_parse(column)) for column in kwargs])

    def _where_part_condition(self, column, value):
        column_name, column_param = self._column_parse(column)

        if isinstance(value, list):
            return '{} IN :where_{}'.format(column_name, column_param)
        elif value is None:
            return '{} IS NULL'.format(column_name)
        else:
            return '{} = :where_{}'.format(column_name, column_param)

    def _where_part(self):
        if not len(self._where_columns.keys()):
            return ''

        where_query = ['WHERE ']
        for table in self._where_columns.keys():
            where_query.append(''.join([' AND '.join([self._where_part_condition((table, column)
                                                                                 if self._join_mode or self.table_name != table else column,
                                                                                 self._where_columns[table][column])
                                                      for column in self._where_columns[table]])]))
        return ''.join(where_query)

    def _order_part(self, *args):
        if len(args) == 0:
            return ''
        return 'ORDER BY {}'.format(
            ', '.join(['{} {}'.format(self._column_parse(row['column'])[0], row['order']) for row in args]))

    @staticmethod
    def _limit_part(limit_cnt):
        if limit_cnt == 0:
            return ''
        return "LIMIT {}".format(limit_cnt)
