
from flask import Blueprint, request
from modules.aws import MuzikaS3Bucket
from modules.login import jwt_check
from modules.response import helper
from modules.response.error import ERR
from modules import database as db
import base64
from modules.ipfs import RelayIpfs

blueprint = Blueprint('file', __name__, url_prefix='/api')


@blueprint.route('/file', methods=['POST'])
@jwt_check
def _upload_file():
    """
    uploads a file. (Only one file is allowed at once)
    """
    user_id = request.user['user_id']
    file_type = request.values.get('type')

    # get files
    if len(request.files) != 1:
        # if the number of file uploaded is not 1,
        return helper.response_err(ERR.INVALID_REQUEST_BODY)

    file = next(iter(request.files.values()))
    file_name = file.filename
    file_data = file.stream.read()

    # get ipfs hash value
    # ipfs = RelayIpfs()
    # ipfs_hash = ipfs.get_connection().add_bytes(file_data)

    # TODO: Download file from IPFS and verify file blob is same with encrypted file_data
    ipfs_hash = request.values.get('ipfs_hash')
    aes_key = request.values.get('aes')

    bucket = MuzikaS3Bucket(file_type=file_type)
    with db.engine_rdwr.begin() as connection:
        file = bucket.put(connection, name=file_name, value=file_data, user_id=user_id,
                          file_type=file_type, content_type=file.content_type, hash=ipfs_hash, aes_key=aes_key)

        if not file:
            return helper.response_err(ERR.UPLOAD_FAIL)

        return helper.response_ok({
            'file_id': file['file_id']
        })
