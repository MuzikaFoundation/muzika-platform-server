import decimal
from datetime import datetime

import flask.json


class FlaskJSONEncoder(flask.json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            # Convert decimal instances to strings.
            return str(obj)
        if isinstance(obj, datetime):
            # Convert datetime to string
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        return super(FlaskJSONEncoder, self).default(obj)
