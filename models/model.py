
from sqlalchemy.ext.declarative import declarative_base


class Base(object):
    def as_dict(self):
        return {key: getattr(self, key) for key in self.__mapper__.c.keys()}


Base = declarative_base(cls=Base)
