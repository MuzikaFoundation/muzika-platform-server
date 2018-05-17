
"""
 This module helps to load secret configuration from secret directory.

 Secret files have private data such as password, private key, access key, and etc.
"""

import os
import json

SECRET_DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), '..', 'secret')


def load_secret_json(file_name):
    # Having no .json extension, attach .json
    _, ext = os.path.splitext(file_name)
    if ext != '.json':
        file_name += '.json'

    try:
        with open(os.path.join(SECRET_DATA_DIRECTORY, file_name)) as file:
            return json.loads(file.read())
    except FileNotFoundError:
        # if file does not exist
        return None
    except json.decoder.JSONDecodeError:
        # if invalid json file
        return None
