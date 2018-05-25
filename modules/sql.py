

class Columns(object):
    """
    This class helps to construct a part of statement for columns update or condition.

    Example

    Add columns
    >>> columns = sql.Columns(column_1='a', column_2='b')

    Add additional columns
    >>> columns(column_3='c', column_4=123)

    construct set statement
    >>> columns.set_statement
    'column_1 = :column_1, column_2 = :column_2, ... , column_4 = :column_4'

    construct condition statement
    >>> columns.where_statement
    'WHERE column_1 = :column_1 AND column_2 = :column_2 AND ... AND column_4 = :column_4

    construct fetch params
    >>> columns.fetch_params
    {
        "column_1": 'a',
        "column_2": 'b',
        "column_3": 'c',
        "column_4": 123
    }
    """
    def __init__(self, **columns):
        self.columns = columns

    @property
    def set_statement(self):
        """
        Return a setting part of SQL statement like as
        column_1 = :column_1, column_2 = :column_2, ..
        """
        return ', '.join(['`{}` = :{}'.format(column, column) for column in self.columns])

    @property
    def where_statement(self):
        """
        Return a where part of SQL statement like as

        1. If no columns
         => ""

        2. If one column
         => "WHERE `column_1` = :column_1"

        3. If multi columns
         => "WHERE `column_1` = :column_1 AND `column_2` = :column_2 AND ..
        """
        if not len(self.columns):
            # if no columns, return empty string
            return ""
        else:
            return 'WHERE {}'.format(' AND '.join(['`{}` = :{}'.format(column, column) for column in self.columns]))

    @property
    def fetch_params(self):
        return self.columns

    def update(self, **kwargs):
        self.columns.update(kwargs)

    def __call__(self, **kwargs):
        self.update(**kwargs)
