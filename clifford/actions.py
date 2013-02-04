import logging

from cliff.command import Command

from commands import InstanceCommand


class Terminate(InstanceCommand):
    "Terminates an instance."

    def take_action(self, parsed_args):
        instance = self.get_box(parsed_args.name)
        if instance and self.sure_check():
            self.log.info('Terminating %s' % parsed_args.name)
            instance.terminate()


class Reboot(InstanceCommand):
    "Reboot an instance."

    def take_action(self, parsed_args):
        instance = self.get_box(parsed_args.name)
        if instance and self.sure_check():
            self.log.info('Rebooting %s' % parsed_args.name)
            instance.reboot()


class Stop(InstanceCommand):
    "Stop an instance."

    def take_action(self, parsed_args):
        instance = self.get_box(parsed_args.name)
        if instance and self.sure_check():
            self.log.info('Stopping %s' % parsed_args.name)
            instance.stop()


class Start(InstanceCommand):
    "Start an instance."

    def take_action(self, parsed_args):
        instance = self.get_box(parsed_args.name)
        if instance and self.sure_check():
            self.log.info('Starting %s' % parsed_args.name)
            instance.start()


class AddImage(Command):
    "Adds an image to config."

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(AddImage, self).get_parser(prog_name)
        parser.add_argument('ami_id')
        return parser

    def take_action(self, parsed_args):
        image = self.app.ec2_conn.get_image(parsed_args.ami_id)
        if not image:
            self.log.info('Image Not Found')
            return

        if not self.app.cparser.has_section('Images'):
            self.app.cparser.add_section('Images')
        if self.app.cparser.has_option('Images', 'images'):
            images = self.app.cparser.get('Images', 'images')
            images += ',' + image.id
            self.app.cparser.set('Images', 'images', images)
        else:
            self.app.cparser.set('Images', 'images', image.id)
        self.app.write_config()
        self.log.info('%s image added to config' % image.name)


class AddOwner(Command):
    "Adds an owner to config."

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(AddOwner, self).get_parser(prog_name)
        parser.add_argument('name')
        parser.add_argument('owner_id')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_section('Owners'):
            self.app.cparser.add_section('Owners')
        self.app.cparser.set('Owners', parsed_args.name, parsed_args.owner_id)
        self.app.write_config()
