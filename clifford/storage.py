import logging
import os

from boto.exception import S3CreateError, S3ResponseError
from boto.s3.key import Key

from commands import BaseCommand


class CreateBucket(BaseCommand):
    "Create an S3 Bucket."

    def get_parser(self, prog_name):
        parser = super(CreateBucket, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        try:
            self.app.s3_conn.create_bucket(parsed_args.name)
        except S3CreateError as e:
            raise RuntimeError('Unable to create bucket [%s]!' % e.reason)


class DeleteBucket(BaseCommand):
    "Delete an S3 Bucket."

    def get_parser(self, prog_name):
        parser = super(DeleteBucket, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        bucket = self.app.s3_conn.get_bucket(parsed_args.name)
        if bucket and self.sure_check():
            try:
                bucket.delete()
            except S3ResponseError as e:
                raise RuntimeError('Unable to delete bucket [%s]!' % e.reason)


class Download(BaseCommand):
    "Download a file from S3."

    def get_parser(self, prog_name):
        parser = super(Upload, self).get_parser(prog_name)
        parser.add_argument('bucket_name')
        parser.add_argument('key_name')
        return parser

    def take_action(self, parsed_args):
        bucket = self.app.s3_conn.get_bucket(parsed_args.bucket_name)
        if not bucket:
            raise RuntimeError('Bucket not found!')
        if os.path.exists(parsed_args.key_name):
            raise RuntimeError('File already exists!')
        # TODO: seems easier to just use curl/wget, have to think of a good use-case
        raise RuntimeError('NO IMPLEMENTATION YET!')


class Upload(BaseCommand):
    "Upload a file to S3."

    def get_parser(self, prog_name):
        parser = super(Upload, self).get_parser(prog_name)
        parser.add_argument('bucket_name')
        parser.add_argument('filename')
        return parser

    def take_action(self, parsed_args):
        bucket = self.app.s3_conn.get_bucket(parsed_args.bucket_name)
        if not bucket:
            raise RuntimeError('Bucket not found!')
        if not os.path.exists(parsed_args.filename):
            raise RuntimeError('File not found!')

        k = Key(bucket)
        k.key = parsed_args.filename
        k.set_contents_from_filename(parsed_args.filename)
        k.set_acl('bucket-owner-full-control')
        public_choice = raw_input('Make file publicly accessible? ')
        if public_choice.lower() in ['y', 'yes']:
            k.set_acl('public-read')
