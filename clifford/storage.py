import logging

from cliff.command import Command


class CreateBucket(Command):
    "Create an S3 Bucket."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        pass


class Download(Command):
    "Download a file from S3."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        pass


class Upload(Command):
    "Upload a file to S3."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        pass
