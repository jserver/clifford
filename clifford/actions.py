import logging

from cliff.command import Command

from mixins import SingleBoxMixin


class InstanceCommand(Command, SingleBoxMixin):

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(InstanceCommand, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser


class Terminate(InstanceCommand):
    "Terminates an instance."

    def take_action(self, parsed_args):
        instance = self.get_box(parsed_args.name)
        if instance:
            self.log.info('Terminating %s' % parsed_args.name)
            instance.terminate()


class Reboot(InstanceCommand):

    def take_action(self, parsed_args):
        instance = self.get_box(parsed_args.name)
        if instance:
            self.log.info('Rebooting %s' % parsed_args.name)
            instance.reboot()


class Stop(InstanceCommand):

    def take_action(self, parsed_args):
        instance = self.get_box(parsed_args.name)
        if instance:
            self.log.info('Stopping %s' % parsed_args.name)
            instance.stop()


class Start(InstanceCommand):

    def take_action(self, parsed_args):
        instance = self.get_box(parsed_args.name)
        if instance:
            self.log.info('Starting %s' % parsed_args.name)
            instance.start()
