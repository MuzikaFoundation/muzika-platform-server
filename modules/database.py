
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


def delete_sql(table_name, data_dict, connect):
    qry_delete = "DELETE FROM {} WHERE ".format(table_name)
    query_list = []
    for key, val in data_dict.items():
        query_list.append("{} = :{}".format(key, key))
    qry_delete = qry_delete + ' AND '.join(query_list)

    return connect.execute(text(qry_delete), data_dict)


def insert_sql(table_name, data_dict, connect):
    qry_insert = "INSERT INTO {} SET ".format(table_name)
    query_list = []
    for key, val in data_dict.items():
        query_list.append("{} = :{}".format(key, key))
    qry_insert = qry_insert + ', '.join(query_list)

    return connect.execute(text(qry_insert), data_dict)


def update_sql(table_name, where_dict, data_dict, connect):
    update_query_str = "UPDATE `{}` SET ".format(table_name)
    query_list = []
    for key, val in data_dict.items():
        query_list.append(" {} = :{} ".format(key, key))
    update_query_str = update_query_str + ', '.join(query_list)

    where_str_arr = []
    for key, val in where_dict.items():
        where_str_arr.append("`{}` = :{}".format(key, key))
    update_query_str = update_query_str + ' WHERE ' + ' AND '.join(where_str_arr)

    return connect.execute(text(update_query_str), data_dict)
