
"""
 Use muzika database.

 For using database for read-only,
 >>> with engine_rdonly.connect() as connection:
 >>>     ...

 For using database for read-writable,
 >>> with engine_rdwr.connect() as connection:
 >>>     ...

"""

import os
import json

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL

__all__ = [
    'engine_rdonly', 'engine_rdwr'
]

with open(os.path.join(os.path.dirname(__file__), '../secret/database.json')) as db_secret_file:
    db_secret = json.loads(db_secret_file.read())

try:
    rdonly_db_url = URL(**db_secret['db_rdonly'])
except KeyError:
    rdonly_db_url = URL(**db_secret['db_rdwr'])
rdwr_db_url = URL(**db_secret['db_rdwr'])

# define database engines
engine_rdonly = create_engine(rdonly_db_url, encoding='utf-8', pool_recycle=290)
engine_rdwr = create_engine(rdwr_db_url, encoding='utf-8', pool_recycle=290)
