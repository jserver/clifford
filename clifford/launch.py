import logging
import time

from commands import BaseCommand


class Launch(BaseCommand):
    "Launches an ec2 instance."

    def get_parser(self, prog_name):
        parser = super(Launch, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        # Size selection
        size = self.question_maker('Available Sizes', 'size',
                [{'text': size} for size in ['t1.micro', 'm1.small', 'm1.medium', 'm1.large']])
        instance_type = size['text']

        # Image selection
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
                [{'text': '%s - %s' %(image.id, image.name), 'obj': image} for image in images])

        # Key selection
        keys = self.app.ec2_conn.get_all_key_pairs()
        if not keys:
            raise RuntimeError('No keys!\n')
        if len(keys) == 1:
            key = keys[0]
        else:
            key = self.question_maker('Available Keys', 'key',
                    [{'text': key.name, 'obj': key} for key in keys])

        # Zone Selection
        zones = [{'text': zone.name, 'obj': zone} for zone in self.app.ec2_conn.get_all_zones()]
        zones.insert(0, {'text': 'No Preference', 'obj': None})
        zone = self.question_maker('Available Zones', 'zone', zones, start_at=0)

        # Security Group selection
        security_groups = self.app.ec2_conn.get_all_security_groups()
        if not security_groups:
            raise RuntimeError('No security groups!\n')
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

        if not self.sure_check():
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
