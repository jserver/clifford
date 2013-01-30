import logging

from cliff.command import Command


class InstanceCommand(Command):
    def get_parser(self, prog_name):
        parser = super(InstanceCommand, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def get_box(self, name):
        reservations = self.app.ec2_conn.get_all_instances(filters={'tag:Name': name})
        for res in reservations:
            if not res.instances:
                self.log.error('No instances wth name %s' % name)
            elif len(res.instances) > 1:
                self.log.error('More than one instance has name %s' % name)
            else:
                return res.instances[0]
            return None


class Terminate(InstanceCommand):
    "Terminates an instance."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        instance = self.get_box(parsed_args.name)
        if instance:
            self.log.info('Terminating %s' % parsed_args.name)
            instance.terminate()


class Reboot(InstanceCommand):
    "Reboots an instance."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        instance = self.get_box(parsed_args.name)
        if instance:
            self.log.info('Rebooting %s' % parsed_args.name)
            instance.reboot()


class Stop(InstanceCommand):
    "Stops an instance."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        instance = self.get_box(parsed_args.name)
        if instance:
            self.log.info('Stopping %s' % parsed_args.name)
            instance.stop()


class Start(InstanceCommand):
    "Starts an instance."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        instance = self.get_box(parsed_args.name)
        if instance:
            self.log.info('Starting %s' % parsed_args.name)
            instance.start()
