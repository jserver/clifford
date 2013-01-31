import logging

from cliff.command import Command


class Launch(Command):
    "Launches an ec2 instance."

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(Launch, self).get_parser(prog_name)
        parser.add_argument('size')
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        self.log.info('sending launch greeting')
        self.log.debug('debugging launch')
        self.app.stdout.write('hi launch!\n')
