
"""
 boto3 gets access key ID and secret access key from secrets directory or aws credentials file. If aws.json exists in
 the "secret" directory, it uses the configuration in it (credential object in json file), and if not, use aws
 credentials file. If aws credentials file used, the profile name should be "muzika".

 For creating aws credentials file, install AWS CLI and use the command like below.

 > aws configure --profile muzika
 > ...
"""

import boto3
from sqlalchemy import text

from modules.secret import load_secret_json

aws_config = load_secret_json('aws')
_credential = aws_config.get('credential')

# if credential is not configured in secret json file
if _credential is None:
    # load credentials from credentials profile (muzika profile)
    session = boto3.Session()
else:
    # else, configure from secret json file
    session = boto3.Session(**_credential)


class MuzikaS3Bucket(object):
    """
    This class loads configuration from secret file and helps to put or to get objects from S3 bucket.
    """
    file_type = None
    config = None

    def __init__(self, **kwargs):
        self.file_type = kwargs.get('file_type')
        if self.file_type:
            self.config = aws_config['s3'][self.file_type]

    def put(self, connection, name, value, user_id=None, file_type=None, content_type='', hash=None, expired_at=None):
        from time import time
        import os
        import hashlib
        # get config from member variable or parameter
        file_type = file_type or self.file_type
        config = self.config or aws_config[file_type]

        # check file extension
        valid_exts = config['ext']
        _, ext = os.path.splitext(name)
        ext = ext.split('.')[-1]

        if ext not in valid_exts:
            # if file extension is not allowed, don't put it to the bucket
            return None

        # get file size and check limitation
        file_size_limit = config['file_size_limit']
        file_len = len(value)
        if file_len > file_size_limit:
            # if file size is over the limitation, don't put it to the bucket
            return None

        # get configuration
        bucket = config['bucket']
        directory = config['directory']
        # if hash value is not set, calculate file hash value
        file_hash = hash or hashlib.sha256(value).hexdigest()

        object_key = '{}-{}.{}'.format(str(int(time() * 100)), file_hash, ext)
        if directory:
            object_key = ''.join([directory, '/', object_key])

        put_query_str = """
            INSERT INTO `files`
            SET
              `user_id` = :user_id,
              `type` = :file_type,
              `s3_bucket` = :s3_bucket,
              `object_key` = :object_key,
              `file_name` = :file_name,
              `file_size` = :file_size,
              `hash` = :file_hash,
              `expired_at` = :expired_at
        """

        s3 = session.client('s3')

        # insert the file information into the db
        connection.execute(
            text(put_query_str),
            user_id=user_id,
            file_type=file_type,
            s3_bucket=bucket,
            object_key=object_key,
            file_name=name,
            file_size=file_len,
            file_hash=file_hash,
            expired_at=expired_at
        )

        # upload to the S3 bucket
        s3.put_object(
            Bucket=bucket,
            Key=object_key,
            Body=value,
            ContentType=content_type
        )

        return {
            'file_type': file_type,
            'file_hash': file_hash,
            'file_size': file_len,
            's3_bucket': bucket,
            'object_key': object_key,
            'content_type': content_type
        }
