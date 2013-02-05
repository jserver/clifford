import logging

from cliff.command import Command

from mixins import SingleBoxMixin, SureCheckMixin


class InstanceCommand(Command, SingleBoxMixin, SureCheckMixin):

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(InstanceCommand, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser
