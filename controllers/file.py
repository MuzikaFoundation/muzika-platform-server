
from flask import Blueprint, request
from sqlalchemy import text

from modules.aws import MuzikaS3Bucket
from modules.login import jwt_check
from modules.response import helper
from modules.response.error import ERR
from modules import database as db
import base64
from modules.ipfs import RelayIpfs
from modules.secret import load_secret_json

blueprint = Blueprint('file', __name__, url_prefix='/api')

# load S3 policy.
s3_policy = load_secret_json('aws.json')['s3']


@blueprint.route('/file/profile', methods=['POST'])
@jwt_check
def _upload_profile_image():
    """
    Uploads a profile image.
    """
    user_id = request.user['user_id']

    # if the number of files uploaded is not one
    if len(request.files) != 1:
        return helper.response_err(ERR.INVALID_REQUEST_BODY)

    file = next(iter(request.files.values()))
    file_name = file.filename

    # read with content length size
    read_len = s3_policy['profile']['file_size_limit'] + 1
    file_data = file.read(read_len)

    # if the file size is too big
    if file.tell() == read_len:
        return helper.response_err(ERR.FILE_SIZE_LIMIT_EXCEEDED)

    # check the number of file user uploaded for defending to upload too many files.
    upload_log_stmt = """
        SELECT COUNT(*) AS `cnt` 
        FROM `{}`
        WHERE 
          `user_id` = :user_id AND 
          `created_at` > NOW() - INTERVAL 10 MINUTE AND
          `type` = :file_type
    """.format(db.table.FILES)

    profile_bucket = MuzikaS3Bucket(file_type='profile')
    with db.engine_rdwr.connect() as connection:
        upload_cnt = connection.execute(text(upload_log_stmt), user_id=user_id, file_type='profile').fetchone()['cnt']

        # if profiles were uploaded over 5 times for 10 minutes, block the request.
        if upload_cnt >= 5:
            return helper.response_err(ERR.TOO_MANY_REQUEST)

        file = profile_bucket.put(
            connection=connection,
            name=file_name,
            value=file_data,
            user_id=user_id
        )

        if not file:
            return helper.response_err(ERR.UPLOAD_FAIL)

        return helper.response_ok({
            'file_id': file['file_id']
        })


@blueprint.route('/file', methods=['POST'])
@jwt_check
@helper.deprecated
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
