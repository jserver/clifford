import logging
import time

from cliff.command import Command

from mixins import SureCheckMixin


class Launch(Command, SureCheckMixin):
    "Launches an ec2 instance."

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(Launch, self).get_parser(prog_name)
        parser.add_argument('size')
        return parser

    def take_action(self, parsed_args):
        # Size validation
        # TODO: make this better and configurable?
        if parsed_args.size == 'micro':
            instance_type = 't1.micro'
        elif parsed_args.size == 'small':
            instance_type = 'm1.small'
        elif parsed_args.size in ['t1.micro', 'm1.small']:
            instance_type = parsed_args.size
        else:
            self.app.stdout.write('Unrecognized instance size!\n')
            return

        # Name Input
        # TODO: check for uniqueness of name
        name = raw_input('Enter name of instance: ')
        if not name:
            self.app.stdout.write('No name given!\n')
            return

        # Image selection
        if not self.app.cparser.has_option('Images', 'images'):
            self.app.stdout.write('No images in config!\n')
            return
        image_ids = self.app.cparser.get('Images', 'images')
        image_ids = image_ids.split(',')
        if image_ids:
            images = self.app.ec2_conn.get_all_images(image_ids=image_ids)
        if not images:
            self.app.stdout.write('No images!\n')
            return
        self.app.stdout.write('Available Images\n')
        self.app.stdout.write('----------------\n')
        for index, item in enumerate(images):
            self.app.stdout.write('%s) %s\n' % (index, item.name))
        image_choice = raw_input('Enter number of image: ')
        if not image_choice.isdigit() or int(image_choice) >= len(images):
            self.app.stdout.write('Not a valid image!\n')
            return
        image = images[int(image_choice)]

        # Key selection
        keys = self.app.ec2_conn.get_all_key_pairs()
        if not keys:
            self.app.stdout.write('No keys!\n')
            return
        if len(keys) == 1:
            key = keys[0]
        else:
            self.app.stdout.write('Available Keys\n')
            self.app.stdout.write('--------------\n')
            for index, item in enumerate(keys):
                self.app.stdout.write('%s) %s\n' % (index, item.name))
            key_choice = raw_input('Enter number of key: ')
            if not key_choice.isdigit() or int(key_choice) >= len(keys):
                self.app.stdout.write('Not a valid key!\n')
                return
            key = keys[int(key_choice)]

        # Zone Selection
        zones = self.app.ec2_conn.get_all_zones()
        self.app.stdout.write('Available Zones\n')
        self.app.stdout.write('---------------\n')
        self.app.stdout.write('0) No Preference\n')
        for index, item in enumerate(zones):
            self.app.stdout.write('%s) %s\n' % (index + 1, item))
        zone_choice = raw_input('Enter number of zone: ')
        if not zone_choice.isdigit() or int(zone_choice) > len(zones):
            self.app.stdout.write('Not a valid zone!\n')
            return
        zone_choice = int(zone_choice)
        if zone_choice == 0:
            zone = None
        else:
            zone = zones[zone_choice - 1]

        # Security Group selection
        groups = self.app.ec2_conn.get_all_security_groups()
        if not groups:
            self.app.stdout.write('No security groups!\n')
            return
        if len(groups) == 1:
            security_group = groups[0]
        else:
            self.app.stdout.write('Available Security Groups\n')
            self.app.stdout.write('-------------------------\n')
            for index, item in enumerate(groups):
                self.app.stdout.write('%s) %s\n' % (index, item.name))
            group_choice = raw_input('Enter number of security group: ')
            if not group_choice.isdigit() or int(group_choice) >= len(groups):
                self.app.stdout.write('Not a valid security group!\n')
                return
            security_group = groups[int(group_choice)]

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
        self.app.ec2_conn.create_tags([instance.id], {'Name': name})

        while True:
            time.sleep(20)
            status = instance.update()
            if status == 'running':
                break
            self.app.stdout.write('%s\n' % status)

        time.sleep(20)
        self.app.stdout.write('Instance should now be running\n')
