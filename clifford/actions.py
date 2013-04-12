import time

from commands import BaseCommand, InstanceCommand
from mixins import SingleInstanceMixin


class DeleteTag(InstanceCommand):
    "Deletes an instance tag."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        if not instance:
            raise RuntimeError('Instance not found!')

        tag_name = raw_input('Tag: ')
        if not tag_name or tag_name == 'Name':
            raise RuntimeError('Invalid Tag')

        instance.remove_tag(tag_name)


class SetTag(InstanceCommand):
    "Sets the value of an instance tag."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        if not instance:
            raise RuntimeError('Instance not found!')

        tag_name = raw_input('Tag: ')
        if not tag_name:
            raise RuntimeError('Invalid Tag')
        value = raw_input('Value: ')
        if not value:
            raise RuntimeError('Invalid Value')

        instance.add_tag(tag_name, value)


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

        self.app.stdout.write('Found the following image:\n')
        self.app.stdout.write('name: %s\n' % image.name)
        self.app.stdout.write('desc: %s\n' % image.description)
        description = raw_input('Enter short description of image: ')
        if not description:
            raise RuntimeError('Description required')

        if not self.app.cparser.has_section('Images'):
            self.app.cparser.add_section('Images')
        self.app.cparser.set('Images', image.id, description)
        self.app.write_config()
        self.app.stdout.write('%s image added to config\n' % image.id)


class SetDomainName(BaseCommand):
    "Adds the domain_name to config."

    def get_parser(self, prog_name):
        parser = super(SetDomainName, self).get_parser(prog_name)
        parser.add_argument('domain_name')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_section('General'):
            self.app.cparser.add_section('General')
        self.app.cparser.set('General', 'domain_name', parsed_args.domain_name)
        self.app.write_config()


class SetKeyPath(BaseCommand):
    "Adds the key_path to config."

    def get_parser(self, prog_name):
        parser = super(SetKeyPath, self).get_parser(prog_name)
        parser.add_argument('key_path')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_section('General'):
            self.app.cparser.add_section('General')
        key_path = parsed_args.key_path
        if key_path[-1:] == '/':
            key_path = key_path[:-1]
        self.app.cparser.set('General', 'key_path', key_path)
        self.app.write_config()


class SetPasswordSalt(BaseCommand):
    "Adds the password_salt to config."

    def get_parser(self, prog_name):
        parser = super(SetPasswordSalt, self).get_parser(prog_name)
        parser.add_argument('password_salt')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_section('General'):
            self.app.cparser.add_section('General')
        self.app.cparser.set('General', 'password_salt', parsed_args.password_salt)
        self.app.write_config()


class SetScriptPath(BaseCommand):
    "Adds the script_path to config."

    def get_parser(self, prog_name):
        parser = super(SetScriptPath, self).get_parser(prog_name)
        parser.add_argument('script_path')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_section('General'):
            self.app.cparser.add_section('General')
        script_path = parsed_args.script_path
        if script_path[-1:] == '/':
            script_path = script_path[:-1]
        self.app.cparser.set('General', 'script_path', script_path)
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
            instance_info = ''
            if volume.attachment_state() == 'attached':
                instance = self.get_instance(volume.attach_data.instance_id, arg_is_id=True)
                instances[instance.id] = instance
                name = instance.tags.get('Name')
                name = '- %s ' % name if name else ''
                instance_info = ' - %s %s- %s' % (instance.id, name, instance.state)
            volumes.append({'text': '%s%s' % (volume.id, instance_info), 'obj': volume})

        volume = self.question_maker('Available Volumes', 'volume', volumes)

        if volume.attachment_state() == 'attached':
            instance = instances[volume.attach_data.instance_id]
            if instance.state == 'running':
                if not self.sure_check('This will stop the attached instance! continue? '):
                    raise RuntimeError('Aborting action')
                self.app.stdout.write('Stopping %s\n' % instance.tags.get('Name', instance.id))
                instance.stop()
                time.sleep(30)
                for i in range(3):
                    status = instance.update()
                    if status == 'stopped':
                        break
                    self.app.stdout.write('%s...\n' % status)
                    time.sleep(20)
                else:
                    raise RuntimeError('Unable to stop instance!')

        name = raw_input('Enter name: ')
        description = raw_input('Enter description: ')
        if not description:
            raise RuntimeError('Description required')
        snapshot = volume.create_snapshot(description)
        time.sleep(5)
        if name:
            snapshot.add_tag('Name', name)


class DeleteImage(BaseCommand):
    "Deletes an image"

    def take_action(self, parsed_args):
        if not self.app.cparser.has_section('Images'):
            raise RuntimeError('No images found!')

        image_ids = self.app.cparser.options('Images')
        if image_ids:
            images = [{'text': '%s - %s' % (image.id, image.name), 'obj': image} for image in self.app.ec2_conn.get_all_images(image_ids=image_ids)]
        image = self.question_maker('Available Images', 'image', images)

        if image and self.sure_check():
            self.app.cparser.remove_option('Images', image.id)
            self.app.write_config()
            self.app.stdout.write('%s removed from Images\n' % image.id)


class DeleteSnapshot(BaseCommand):
    "Deletes a snapshot"

    def take_action(self, parsed_args):
        all_snapshots = self.app.ec2_conn.get_all_snapshots(owner='self')
        if not all_snapshots:
            raise RuntimeError('No snapshots found!')
        snapshots = []
        for snapshot in all_snapshots:
            snapshot_info = snapshot.id
            if snapshot.tags.get('Name'):
                snapshot_info += ' - %s' % snapshot.tags.get('Name')
            snapshots.append({'text': snapshot_info, 'obj': snapshot})
        snapshot = self.question_maker('Available Snapshots', 'snapshot', snapshots)

        if snapshot and self.sure_check():
            snapshot.delete()


class DeleteVolume(BaseCommand):
    "Deletes a volume"

    def take_action(self, parsed_args):
        volumes = [{'text': volume.id, 'obj': volume} for volume in self.app.ec2_conn.get_all_volumes() if volume.status == 'available']
        if not volumes:
            raise RuntimeError('No available volumes found!')
        volume = self.question_maker('Available Volumes', 'volume', volumes)

        if volume and self.sure_check():
            volume.delete()
