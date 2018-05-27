
from flask import Blueprint, request
from modules.aws import MuzikaS3Bucket
from modules.login import jwt_check
from modules.response import helper
from modules.response import error_constants as ER
from modules import database as db
from modules.ipfs import RelayIpfs

blueprint = Blueprint('file', __name__, url_prefix='/api')


@blueprint.route('/file', methods=['POST'])
@jwt_check
def _upload_file():
    """
    uploads a file. (Only one file is allowed at once)
    """
    user_id = request.user['user_id']
    file_type = request.args.get('type')

    # get files
    if len(request.files) != 1:
        # if the number of file uploaded is not 1,
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    file = next(iter(request.files.values()))
    file_name = file.filename
    file_data = file.stream.read()

    # get ipfs hash value
    ipfs = RelayIpfs()
    file_hash = ipfs.get_connection().add_bytes(file_data)

    bucket = MuzikaS3Bucket(file_type=file_type)
    with db.engine_rdwr.begin() as connection:
        file = bucket.put(connection, name=file_name, value=file_data, user_id=user_id,
                          file_type=file_type, content_type=file.content_type, hash=file_hash)

        if not file:
            return helper.response_err(ER.UPLOAD_FAIL, ER.UPLOAD_FAIL_MSG)

        return helper.response_ok({'file_id': file['file_id']})
