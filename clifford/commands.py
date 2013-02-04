import logging

from cliff.command import Command

from mixins import SingleBoxMixin


class InstanceCommand(Command, SingleBoxMixin):

    log = logging.getLogger(__name__)

    def sure_check(self):
        you_sure = raw_input('Are you sure? ')
        if you_sure.lower() not in ['y', 'yes']:
            return False
        return True

    def get_parser(self, prog_name):
        parser = super(InstanceCommand, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser



