
"""
 Defines error codes and error messages for the server response.
"""

INVALID_REQUEST_BODY = 401
INVALID_REQUEST_BODY_MSG = "Invalid request body."

INVALID_SIGNATURE = 402
INVALID_SIGNATURE_MSG = "Invalid signature."

NOT_EXIST = 403
NOT_EXIST_MSG = "Object does not exist."

AUTHENTICATION_FAILED = 404
AUTHENTICATION_FAILED_MSG = "Failed to authenticate."

ALREADY_EXIST = 405
ALREADY_EXIST_MSG = "Already exists."

UPLOAD_FAIL = 406
UPLOAD_FAIL_MSG = "Failed to upload the file."

TX_HASH_DUPLICATED = 407
TX_HASH_DUPLICATED_MSG = "tx hash already exists"

INVALID_TX_HASH = 408
INVALID_TX_HASH_MSG = "tx hash already exists"

TOO_LONG_PARAMETER = 409
TOO_LONG_PARAMETER_MSG = 'too long parameter'

TOO_SHORT_PARAMETER = 410
TOO_SHORT_PARAMETER_MSG = 'too short parameter'