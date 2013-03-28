import logging
import time

from commands import BaseCommand
from mixins import SingleInstanceMixin


class BuildBox(BaseCommand, SingleInstanceMixin):
    "Launch and bootstrap a new ec2 instance"

    def get_parser(self, prog_name):
        parser = super(BuildBox, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        build = self.question_maker('Select Build', 'build',
                [{'text': build[:-1 * len('.build')]} for build in self.app.cparser.sections() if build.endswith('.build')])
        if not self.app.cparser.has_section('%s.build' % build):
            raise RuntimeError('No build with that name in config!\n')

        if not self.sure_check():
            return

        option_list = self.app.cparser.options('%s.build' % build)
        options = {}
        for option in option_list:
            options[option] = self.app.cparser.get('%s.build' % build, option)

        cmd = 'launch -y'
        cmd += ' --size %s' % options['size']
        cmd += ' --image %s' % options['image']
        cmd += ' --key %s' % options['key']
        cmd += ' --zone %s' % options['zone']
        cmd += ' --security_group %s' % options['security_group']
        cmd += ' ' + parsed_args.name
        self.app.run_subcommand(cmd.split(' '))

        instance = self.get_instance(parsed_args.name)
        if not instance:
            raise RuntimeError('Cannot find instance')

        if 'upgrade' in options and options['upgrade'] in ['upgrade', 'dist-upgrade']:
            cmd = 'remote upgrade -y'
            cmd += ' --id %s' % instance.id
            if options['upgrade'] == 'upgrade':
                cmd += ' --upgrade'
            if options['upgrade'] == 'dist-upgrade':
                cmd += ' --dist-upgrade'
            self.app.run_subcommand(cmd.split(' '))

        if 'group' in options:
            cmd = 'remote group install -y'
            cmd += ' --id %s' % instance.id
            cmd += ' ' + options['group']
            self.app.run_subcommand(cmd.split(' '))

        if 'easy_install' in options:
            cmd = 'remote easy_install -y'
            cmd += ' --id %s' % instance.id
            cmd += ' ' + options['easy_install']
            self.app.run_subcommand(cmd.split(' '))

        if 'user_name' in options:
            cmd = 'remote create user -y'
            cmd += ' --id %s' % instance.id
            cmd += ' ' + options['user_name']
            if 'user_fullname' in options:
                cmd += ' --fullname %s' % options['user_fullname']
            else:
                cmd += ' --fullname %s' + options['user_name']
            self.app.run_subcommand(cmd.split(' '))


class Launch(BaseCommand):
    "Launches an ec2 instance."

    def get_parser(self, prog_name):
        parser = super(Launch, self).get_parser(prog_name)
        parser.add_argument('-y', dest='assume_yes', action='store_true')
        parser.add_argument('--size')
        parser.add_argument('--image')
        parser.add_argument('--key')
        parser.add_argument('--zone')
        parser.add_argument('--security_group')
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        # Size selection
        SIZES = ['t1.micro', 'm1.small', 'm1.medium', 'm1.large']
        if parsed_args.size and parsed_args.size in SIZES:
            instance_type = parsed_args.size
        else:
            instance_type = self.question_maker('Available Sizes', 'size',
                    [{'text': size} for size in SIZES])

        # Image selection
        image = None
        if parsed_args.image:
            try:
                image = self.app.ec2_conn.get_image(image_id=parsed_args.image)
            except:
                pass

        if not image:
            if not self.app.cparser.has_option('Images', 'images'):
                raise RuntimeError('No images in config!\n')

            image_ids = self.app.cparser.get('Images', 'images')
            image_ids = image_ids.split(',')
            if image_ids:
                images = self.app.ec2_conn.get_all_images(image_ids=image_ids)
            if not images:
                raise RuntimeError('No images!\n')

            images = sorted(images, key=lambda image: image.name.lower())
            image = self.question_maker('Available Images', 'image',
                    [{'text': '%s - %s' % (image.id, image.name), 'obj': image} for image in images])

        # Key selection
        key = None
        all_keys = self.app.ec2_conn.get_all_key_pairs()
        if not all_keys:
            raise RuntimeError('No keys!\n')
        if parsed_args.key and parsed_args.key in [key.name for key in all_keys]:
            key = [key for key in all_keys if key.name == parsed_args.key][0]

        if not key:
            if len(all_keys) == 1:
                key = all_keys[0]
            else:
                key = self.question_maker('Available Keys', 'key',
                        [{'text': key.name, 'obj': key} for key in all_keys])

        # Zone Selection
        if parsed_args.zone == 'No Preference':
            pass
        else:
            all_zones = self.app.ec2_conn.get_all_zones()
            if parsed_args.zone in [zone.name for zone in all_zones]:
                zone = [zone for zone in all_zones if zone.name == parsed_args.zone][0]
            else:
                zones = [{'text': zone.name, 'obj': zone} for zone in all_zones]
                zones.insert(0, {'text': 'No Preference'})
                zone = self.question_maker('Available Zones', 'zone', zones, start_at=0)

        # Security Group selection
        security_groups = self.app.ec2_conn.get_all_security_groups()
        if not security_groups:
            raise RuntimeError('No security groups!\n')
        if parsed_args.security_group and parsed_args.security_group in [security_group.name for security_group in security_groups]:
            security_group = [item for item in security_groups if security_group.name == parsed_args.security_group][0]
        else:
            if len(security_groups) == 1:
                security_group = security_groups[0]
            else:
                security_groups = sorted(security_groups, key=lambda group: group.name.lower())
                security_group = self.question_maker('Available Security Groups', 'security group',
                        [{'text': security_group.name, 'obj': security_group} for security_group in security_groups])

        kwargs = {
            'key_name': key.name,
            'instance_type': instance_type,
            'security_group_ids': [security_group.id],
        }
        if zone:
            kwargs['placement'] = zone.name

        # user-data
        # TODO: should at least give the option

        if not parsed_args.assume_yes and not self.sure_check():
            raise RuntimeError('Instance not created!')

        # Launch this thing
        self.app.stdout.write('Launching instance...\n')
        reservation = image.run(**kwargs)
        time.sleep(10)
        instance = reservation.instances[0]

        time.sleep(10)
        self.app.stdout.write('Tagging instance...\n')
        self.app.ec2_conn.create_tags([instance.id], {'Name': parsed_args.name})

        while True:
            time.sleep(20)
            status = instance.update()
            if status == 'running':
                break
            self.app.stdout.write('%s\n' % status)

        time.sleep(20)
        self.app.stdout.write('Instance should now be running\n')
        if self.app.cparser.has_option('Key Path', 'key_path'):
            key_path = self.app.cparser.get('Key Path', 'key_path')
            self.app.stdout.write('ssh -i %s/%s.pem ubuntu@%s\n' % (key_path, key.name, instance.public_dns_name))
        else:
            self.app.stdout.write('Public DNS: %s\n' % instance.public_dns_name)
