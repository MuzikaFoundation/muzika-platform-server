
import argparse
import os

import boto3

secret_files = [
    'aws.json',
    'database.json',
    'jwt.json',
]

args = argparse.ArgumentParser()

args.add_argument('--upload', help="Upload secret files to S3 bucket.", default=False, action='store_true')
args.add_argument('--download', help="Download secret files from S3 bucket.", default=False, action='store_true')
args.add_argument('--bucket', help="The name of S3 bucket", required=True)
args.add_argument('--profile', help="The name of aws credentials profile name", default=None)
args = args.parse_args()

if (args.upload and args.download) or (not args.upload and not args.download):
    print('Select only one of uploading or downloading.')

session = boto3.Session() if args.profile is None else boto3.Session(profile_name=args.profile)
s3 = session.client('s3')

if args.upload:
    for secret_file in secret_files:
        file_path = os.path.join(os.path.dirname(__file__), '..', 'secret', secret_file)
        with open(file_path) as f:
            s3.put_object(
                Bucket=args.bucket,
                Key='secret/{}'.format(secret_file),
                Body=f.read(),
                ContentType='application/json'
            )

if args.download:
    for secret_file in secret_files:
        file_path = os.path.join(os.path.dirname(__file__), '..', 'secret', secret_file)
        with open(file_path, 'w+') as f:
            obj = s3.get_object(
                Bucket=args.bucket,
                Key='secret/{}'.format(secret_file)
            )
            f.write(obj['Body'].read().decode('utf-8'))
