import time

from commands import BaseCommand, InstanceCommand
from mixins import SingleInstanceMixin


class Tag(InstanceCommand):
    "Add/Remove/Update Tag on an instance."

    def get_parser(self, prog_name):
        parser = super(Tag, self).get_parser(prog_name)
        parser.add_argument('--rm', action='store_true')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        if not instance:
            raise RuntimeError('Instance not found!')

        if parsed_args.rm:
            tag_name = raw_input('Tag: ')
            if not tag_name or tag_name == 'Name':
                raise RuntimeError('Invalid Tag')

            instance.remove_tag(tag_name)

        else:
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
        self.app.cparser.set('Images', description, image.id)
        self.app.write_config()
        self.app.stdout.write('%s image added to config\n' % image.id)


class Domain(BaseCommand):
    "Add/Update domain_name."

    def get_parser(self, prog_name):
        parser = super(Domain, self).get_parser(prog_name)
        parser.add_argument('-u', '--update')
        return parser

    def take_action(self, parsed_args):
        if not parsed_args.update:
            self.app.stdout.write('%s\n' % self.get_option('General', 'domain'))
            return

        if not self.app.cparser.has_section('General'):
            self.app.cparser.add_section('General')

        self.app.cparser.set('General', 'domain', parsed_args.update)
        self.app.write_config()


class KeyPaths(BaseCommand):
    "Add/Update key_paths."

    def get_parser(self, prog_name):
        parser = super(KeyPaths, self).get_parser(prog_name)
        parser.add_argument('--aws')
        parser.add_argument('--pub')
        return parser

    def take_action(self, parsed_args):
        if not parsed_args.aws and not parsed_args.pub:
            self.app.stdout.write('aws: %s\n' % self.aws_key_path)
            self.app.stdout.write('pub: %s\n' % self.pub_key_path)
            return

        if not self.app.cparser.has_section('General'):
            self.app.cparser.add_section('General')

        if parsed_args.aws:
            self.app.cparser.set('General', 'aws_key_path', self.add_slash(parsed_args.aws))
        if parsed_args.pub:
            self.app.cparser.set('General', 'pub_key_path', self.add_slash(parsed_args.pub))

        self.app.write_config()


class Salt(BaseCommand):
    "Add/Update the salt."

    def get_parser(self, prog_name):
        parser = super(Salt, self).get_parser(prog_name)
        parser.add_argument('-u', '--update')
        return parser

    def take_action(self, parsed_args):
        if not parsed_args.update:
            self.app.stdout.write('%s\n' % self.get_option('General', 'salt'))
            return

        if not self.app.cparser.has_section('General'):
            self.app.cparser.add_section('General')

        self.app.cparser.set('General', 'salt', parsed_args.update)
        self.app.write_config()


class ScriptPath(BaseCommand):
    "Add/Update script_path."

    def get_parser(self, prog_name):
        parser = super(ScriptPath, self).get_parser(prog_name)
        parser.add_argument('-u', '--update')
        return parser

    def take_action(self, parsed_args):
        if not parsed_args.update:
            self.app.stdout.write('%s\n' % self.script_path)
            return

        if not self.app.cparser.has_section('General'):
            self.app.cparser.add_section('General')

        self.app.cparser.set('General', 'script_path', self.add_slash(parsed_args.update))
        self.app.write_config()


class CreateImage(InstanceCommand):
    "Create an Image of an instance."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        name = raw_input('Enter name: ')
        desc = raw_input('Enter desc: ')
        if instance and name and self.sure_check():
            if not desc:
                desc = None
            image_id = instance.create_image(name, desc)
            self.app.stdout.write(image_id)


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
            raise RuntimeError('No image section found!')

        items = self.app.cparser.items('Images')
        if not items:
            raise RuntimeError('No images found')
        images = [{'text': '%s - %s' % (image[0], image[1]), 'obj': image[0]} for image in items]
        image = self.question_maker('Available Images', 'image', images)

        if self.sure_check():
            self.app.cparser.remove_option('Images', image)
            self.app.write_config()
            self.app.stdout.write('%s removed from Images\n' % image)


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

        if self.sure_check():
            snapshot.delete()


class DeleteVolume(BaseCommand):
    "Deletes a volume"

    def take_action(self, parsed_args):
        volumes = [{'text': volume.id, 'obj': volume} for volume in self.app.ec2_conn.get_all_volumes() if volume.status == 'available']
        if not volumes:
            raise RuntimeError('No available volumes found!')
        volume = self.question_maker('Available Volumes', 'volume', volumes)

        if self.sure_check():
            volume.delete()
