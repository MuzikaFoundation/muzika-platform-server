
"""
 Use muzika database.

 Use session_scope() for getting a session. It manages transaction and exceptions automatically.

 For using read-only database,
 >>> with session_scope() as session:
 >>>     ...

 For using readable and writable database,
 >>> with session_scope(writable=True) as session:
 >>>     ...
"""

import os
import json
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
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

# define session makers
session_rdonly = sessionmaker(bind=engine_rdonly)
session_rdwr = sessionmaker(bind=engine_rdwr)


@contextmanager
def session_scope(writable=False, autocommit=True, autoflush=True):
    if writable:
        session = session_rdonly(autocommit=autocommit, autoflush=autoflush)
    else:
        session = session_rdwr(autocommit=autocommit, autoflush=autoflush)

    try:
        yield session
        if autocommit is False:
            session.commit()
    except Exception:
        if autocommit is False:
            session.rollback()
        raise
    finally:
        session.close()
