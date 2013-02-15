import logging

from cliff.command import Command

from commands import InstanceCommand
from mixins import SureCheckMixin


class Terminate(InstanceCommand):
    "Terminates an instance."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        if instance and self.sure_check():
            self.app.stdout.write('Terminating %s\n' % parsed_args.name)
            instance.terminate()


class Reboot(InstanceCommand):
    "Reboot an instance."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        if instance and self.sure_check():
            self.app.stdout.write('Rebooting %s\n' % parsed_args.name)
            instance.reboot()


class Stop(InstanceCommand):
    "Stop an instance."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        if instance and self.sure_check():
            self.app.stdout.write('Stopping %s\n' % parsed_args.name)
            instance.stop()


class Start(InstanceCommand):
    "Start an instance."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        if instance and self.sure_check():
            self.app.stdout.write('Starting %s\n' % parsed_args.name)
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
            raise RuntimeError('Image not found!')

        if not self.app.cparser.has_section('Images'):
            self.app.cparser.add_section('Images')
        if self.app.cparser.has_option('Images', 'images'):
            images = self.app.cparser.get('Images', 'images')
            images += ',' + image.id
            self.app.cparser.set('Images', 'images', images)
        else:
            self.app.cparser.set('Images', 'images', image.id)
        self.app.write_config()
        self.app.stdout.write('%s image added to config\n' % image.name)


class SetOwner(Command):
    "Adds owner to config."

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(SetOwner, self).get_parser(prog_name)
        parser.add_argument('owner_id')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_section('Owner'):
            self.app.cparser.add_section('Owner')
        self.app.cparser.set('Owner', 'owner', parsed_args.owner_id)
        self.app.write_config()


class CreateImage(InstanceCommand):
    "Create an Image of an instance."

    def take_action(self, parsed_args):
        pass


class CreateSnapshot(Command):
    "Create a snapshot of a volume."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        pass


class DeleteVolume(Command, SureCheckMixin):
    "Deletes a volume"

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        volumes = [volume for volume in self.app.ec2_conn.get_all_volumes() if volume.status == 'available']
        if not volumes:
            raise RuntimeError('No volumes found!')

        self.app.stdout.write('Available Volumes\n')
        self.app.stdout.write('-----------------\n')
        for index, item in enumerate(volumes):
            self.app.stdout.write('%s) %s\n' % (index, item.id))
        volume_choice = raw_input('Enter number of volume: ')
        if not volume_choice.isdigit() or int(volume_choice) >= len(volumes):
            self.app.stdout.write('Not a valid volume!\n')
            return
        volume = volumes[int(volume_choice)]
        if self.sure_check():
            volume.delete()
