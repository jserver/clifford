from collections import OrderedDict
import time

from commands import BaseCommand
from main import config


class Reboot(BaseCommand):
    "Reboot an instance."

    def get_parser(self, prog_name):
        parser = super(Reboot, self).get_parser(prog_name)
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('inst_names', nargs='+')
        return parser

    def take_action(self, parsed_args):
        if self.sure_check():
            for name in parsed_args.inst_names:
                instances = self.get_instances(name)
                for inst in instances:
                    self.app.stdout.write('Rebooting %s\n' % inst.tags.get('Name', inst.id))
                    inst.reboot()


class Start(BaseCommand):
    "Start an instance."

    def get_parser(self, prog_name):
        parser = super(Start, self).get_parser(prog_name)
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('inst_names', nargs='+')
        return parser

    def take_action(self, parsed_args):
        if self.sure_check():
            for name in parsed_args.inst_names:
                instances = self.get_instances(name)
                for inst in instances:
                    self.app.stdout.write('Starting %s\n' % inst.tags.get('Name', inst.id))
                    inst.start()


class Stop(BaseCommand):
    "Stop an instance."

    def get_parser(self, prog_name):
        parser = super(Stop, self).get_parser(prog_name)
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('inst_names', nargs='+')
        return parser

    def take_action(self, parsed_args):
        if self.sure_check():
            for name in parsed_args.inst_names:
                instances = self.get_instances(name)
                for inst in instances:
                    self.app.stdout.write('Stopping %s\n' % inst.tags.get('Name', inst.id))
                    inst.stop()


class Terminate(BaseCommand):
    "Terminates an instance."

    def get_parser(self, prog_name):
        parser = super(Terminate, self).get_parser(prog_name)
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('inst_names', nargs='+')
        return parser

    def take_action(self, parsed_args):
        if self.sure_check():
            for name in parsed_args.inst_names:
                instances = self.get_instances(name)
                for inst in instances:
                    self.app.stdout.write('Terminating %s\n' % inst.tags.get('Name', inst.id))
                    inst.terminate()


class CreateImage(BaseCommand):
    "Create an Image of an instance."

    def get_parser(self, prog_name):
        parser = super(CreateImage, self).get_parser(prog_name)
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('inst_name')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.inst_name, parsed_args.arg_is_id)
        name = raw_input('Enter name: ')
        desc = raw_input('Enter desc: ')
        if instance and name and self.sure_check():
            if not desc:
                desc = None
            image_id = instance.create_image(name, desc)
            self.app.stdout.write('Image created: %s\n' % image_id)


class CreateSnapshot(BaseCommand):
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
                    raise RuntimeError('Aborting action!')
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
            raise RuntimeError('Description required!')
        snapshot = volume.create_snapshot(description)
        time.sleep(5)
        if name:
            snapshot.add_tag('Name', name)


class DeleteAwsImage(BaseCommand):
    "Deletes an AWS Image"

    def take_action(self, parsed_args):
        all_images = self.app.ec2_conn.get_all_images(owners='self')
        if not all_images:
            raise RuntimeError('No AWS Images found!')
        images = []
        for image in all_images:
            image_info = '%s - %s' % (image.id, image.name)
            images.append({'text': image_info, 'obj': image})
        image = self.question_maker('Available AWS Images', 'image', images)

        if self.sure_check():
            image.deregister(delete_snapshot=True)


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


class Domain(BaseCommand):
    "Add/Update domain_name."

    def get_parser(self, prog_name):
        parser = super(Domain, self).get_parser(prog_name)
        parser.add_argument('-u', '--update')
        return parser

    def take_action(self, parsed_args):
        if not parsed_args.update:
            self.app.stdout.write('%s\n' % config.get('Domain', '<<Domain not set!>>'))
            return

        config['Domain'] = parsed_args.update
        config.save()


class Image(BaseCommand):
    "Adds an image to config."

    def get_parser(self, prog_name):
        parser = super(Image, self).get_parser(prog_name)
        parser.add_argument('-a', '--add')
        parser.add_argument('-r', '--remove', action='store_true')
        return parser

    def take_action(self, parsed_args):
        if not parsed_args.add and not parsed_args.remove:
            raise RuntimeError('Use -a <ami_id> to add or -r to remove images!')

        if parsed_args.add:
            image = self.app.ec2_conn.get_image(parsed_args.add)
            if not image:
                raise RuntimeError('Image not found!')

            self.app.stdout.write('Found the following image:\n')
            self.app.stdout.write('  Name: %s\n' % image.name)
            self.app.stdout.write('  Desc: %s\n' % image.description)

            login = raw_input('Enter login: ')
            if not login:
                raise RuntimeError('Login required!')

            name = raw_input('Enter nickname of image: ')
            if not name:
                raise RuntimeError('Nickname required!')
            if name in config.images:
                raise RuntimeError('Nickname already in use!')

            img = OrderedDict()
            img['Id'] = image.id
            img['Login'] = login
            img['Name'] = image.name
            config.images[name] = img
            config['Images'] = OrderedDict(sorted(config.images.items(), key=lambda i: i[0].lower()))
            config.save()

        elif parsed_args.remove:
            images = config.images
            if not images:
                raise RuntimeError('No Images found!')

            items = [{'text': '%s - %s' % (key, images[key]['Id']), 'obj': key} for key in images.keys()]
            image = self.question_maker('Available Images', 'image', items)

            if self.sure_check():
                del(images[image])
                config.save()


class KeyPaths(BaseCommand):
    "Add/Update key_paths."

    def get_parser(self, prog_name):
        parser = super(KeyPaths, self).get_parser(prog_name)
        parser.add_argument('--aws')
        parser.add_argument('--pub')
        return parser

    def take_action(self, parsed_args):
        if not parsed_args.aws and not parsed_args.pub:
            self.app.stdout.write('aws: %s\n' % config.aws_key_path)
            self.app.stdout.write('pub: %s\n' % config.pub_key_path)
            return

        if parsed_args.aws:
            config['AwsKeyPath'] = parsed_args.aws
        if parsed_args.pub:
            config['PubKeyPath'] = parsed_args.pub

        config.save()


class Salt(BaseCommand):
    "Add/Update the salt."

    def get_parser(self, prog_name):
        parser = super(Salt, self).get_parser(prog_name)
        parser.add_argument('-u', '--update')
        return parser

    def take_action(self, parsed_args):
        if not parsed_args.update:
            self.app.stdout.write('%s\n' % config.get('Salt', '<<Salt not set!>>'))
            return

        config['Salt'] = parsed_args.update
        config.save()


class ScriptPath(BaseCommand):
    "Add/Update script_path."

    def get_parser(self, prog_name):
        parser = super(ScriptPath, self).get_parser(prog_name)
        parser.add_argument('-u', '--update')
        return parser

    def take_action(self, parsed_args):
        if not parsed_args.update:
            self.app.stdout.write('%s\n' % config.script_path)
            return

        config['ScriptPath'] = parsed_args.update
        config.save()


class Tag(BaseCommand):
    "Add/Remove/Update Tag on an instance."

    def get_parser(self, prog_name):
        parser = super(Tag, self).get_parser(prog_name)
        parser.add_argument('-d', '--delete', action='store_true')
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('inst_name')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.inst_name, parsed_args.arg_is_id)
        if not instance:
            raise RuntimeError('Instance not found!')

        if parsed_args.delete:
            tag_name = raw_input('Tag: ')
            if not tag_name or tag_name == 'Name':
                raise RuntimeError('Invalid Tag!')

            instance.remove_tag(tag_name)

        else:
            tag_name = raw_input('Tag: ')
            if not tag_name:
                raise RuntimeError('Invalid Tag!')
            value = raw_input('Value: ')
            if not value:
                raise RuntimeError('Invalid Value!')

            instance.add_tag(tag_name, value)
