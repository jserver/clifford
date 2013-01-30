import logging

from cliff.command import Command


class Launch(Command):
    "Launches an ec2 instance."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        self.log.info('sending launch greeting')
        self.log.debug('debugging launch')
        self.app.stdout.write('hi launch!\n')
