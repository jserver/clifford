import time

from commands import BaseCommand, InstanceCommand
from mixins import SingleInstanceMixin


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


class AddImage(BaseCommand):
    "Adds an image to config."

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


class SetKeyPath(BaseCommand):
    "Adds the key_path to config."

    def get_parser(self, prog_name):
        parser = super(SetKeyPath, self).get_parser(prog_name)
        parser.add_argument('key_path')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_section('Key Path'):
            self.app.cparser.add_section('Key Path')
        key_path = parsed_args.key_path
        if key_path[-1:] == '/':
            key_path = key_path[:-1]
        self.app.cparser.set('Key Path', 'key_path', key_path)
        self.app.write_config()


class SetOwner(BaseCommand):
    "Adds owner to config."

    def get_parser(self, prog_name):
        parser = super(SetOwner, self).get_parser(prog_name)
        parser.add_argument('owner_id')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_section('Owner'):
            self.app.cparser.add_section('Owner')
        self.app.cparser.set('Owner', 'owner', parsed_args.owner_id)
        self.app.write_config()


class SetScriptPath(BaseCommand):
    "Adds the script_path to config."

    def get_parser(self, prog_name):
        parser = super(SetScriptPath, self).get_parser(prog_name)
        parser.add_argument('script_path')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_section('Script Path'):
            self.app.cparser.add_section('Script Path')
        script_path = parsed_args.script_path
        if script_path[-1:] == '/':
            script_path = script_path[:-1]
        self.app.cparser.set('Script Path', 'script_path', script_path)
        self.app.write_config()


class CreateImage(InstanceCommand):
    "Create an Image of an instance."

    def take_action(self, parsed_args):
        pass


class CreateSnapshot(BaseCommand, SingleInstanceMixin):
    "Create a snapshot of a volume."

    def take_action(self, parsed_args):
        all_volumes = self.app.ec2_conn.get_all_volumes()
        volumes = []
        instances = {}
        for volume in all_volumes:
            instance_id = ''
            if volume.attachment_state() == 'attached':
                instance = self.get_instance(volume.attach_data.instance_id, arg_is_id=True)
                instances[instance.id] = instance
                instance_id = ' - ' + instance.id + ' - ' + instance.tags.get('Name')
            volumes.append({'text': '%s%s' % (volume.id, instance_id), 'obj': volume})

        volume = self.question_maker('Available Volumes', 'volume', volumes)

        if volume.attachment_state() == 'attached' and instances[volume.attach_data.instance_id].state == 'running':
            self.app.stdout.write('Stopping %s' % instances[volume.attach_data.instance_id].tags.get('Name'))
            instances[volume.attach_data.instance_id].stop()
            time.sleep(20)

        volume.create_snapshot('A really cool snapshot')


class DeleteImage(BaseCommand):
    "Deletes an image"

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Images', 'images'):
            raise RuntimeError('No images found!')

        images_str = self.app.cparser.get('Images', 'images')
        image_ids = images_str.split(',')
        if image_ids:
            images = [{'text': '%s - %s' % (image.id, image.name)} for image in self.app.ec2_conn.get_all_images(image_ids=image_ids)]
        image = self.question_maker('Available Images', 'image', images)

        if image and self.sure_check():
            image_ids.remove(image['id'])
            images = ','.join(image_ids)
            self.app.cparser.set('Images', 'images', images)
            self.app.write_config()
            self.app.stdout.write('%s removed from images\n' % image['name'])


class DeleteVolume(BaseCommand):
    "Deletes a volume"

    def take_action(self, parsed_args):
        volumes = [{'text': volume.id, 'obj': volume} for volume in self.app.ec2_conn.get_all_volumes() if volume.status == 'available']
        if not volumes:
            raise RuntimeError('No available volumes found!')
        volume = self.question_maker('Available Volumes', 'volume', volumes)

        if volume and self.sure_check():
            volume.obj.delete()
