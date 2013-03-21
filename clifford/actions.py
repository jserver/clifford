import logging

from cliff.command import Command

from commands import InstanceCommand
from mixins import QuestionableMixin, SureCheckMixin


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


class SetKeyPath(Command):
    "Adds the key_path to config."

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(SetKeyPath, self).get_parser(prog_name)
        parser.add_argument('key_path')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_section('Key Path'):
            self.app.cparser.add_section('Key Path')
        self.app.cparser.set('Key Path', 'key_path', parsed_args.key_path)
        self.app.write_config()


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


class SetScriptPath(Command):
    "Adds the script_path to config."

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(SetScriptPath, self).get_parser(prog_name)
        parser.add_argument('script_path')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_section('Script Path'):
            self.app.cparser.add_section('Script Path')
        self.app.cparser.set('Script Path', 'script_path', parsed_args.script_path)
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


class DeleteImage(Command, QuestionableMixin, SureCheckMixin):
    "Deletes an image"

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Images', 'images'):
            raise RuntimeError('No images found!')

        images_str = self.app.cparser.get('Images', 'images')
        image_ids = images_str.split(',')
        if image_ids:
            images = [{'id': image.id, 'name': image.name} for image in self.app.ec2_conn.get_all_images(image_ids=image_ids)]

        image = self.question_maker('Available Images', 'image', images)

        if image and self.sure_check():
            image_ids.remove(image['id'])
            images = ','.join(image_ids)
            self.app.cparser.set('Images', 'images', images)
            self.app.write_config()
            self.app.stdout.write('%s removed from images\n' % image['name'])

class DeleteVolume(Command, QuestionableMixin, SureCheckMixin):
    "Deletes a volume"

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        volumes = [{'id': volume.id, 'obj': volume, 'name': ''} for volume in self.app.ec2_conn.get_all_volumes() if volume.status == 'available']
        if not volumes:
            raise RuntimeError('No available volumes found!')

        volume = self.question_maker('Available Volumes', 'volume', volumes)

        if volume and self.sure_check():
            volume.obj.delete()
