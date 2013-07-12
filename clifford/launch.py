import glob
import time

from commands import BaseCommand


class Launch(BaseCommand):
    "Launches an ec2 instance."

    def get_parser(self, prog_name):
        parser = super(Launch, self).get_parser(prog_name)
        parser.add_argument('-y', dest='assume_yes', action='store_true')
        parser.add_argument('--size')
        parser.add_argument('--image')
        parser.add_argument('--key')
        parser.add_argument('--zone')
        parser.add_argument('--security-groups')
        parser.add_argument('--user-data')
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
            if not self.app.cparser.has_section('Images'):
                raise RuntimeError('No image section found!\n')

            items = self.app.cparser.items('Images')
            image_ids = [item[1] for item in items]
            if not image_ids:
                raise RuntimeError('No images found!')

            images = [{'text': '%s - %s' % (items[image_ids.index(img.id)][0], img.id), 'obj': img} for img in self.app.ec2_conn.get_all_images(image_ids=image_ids)]
            images = sorted(images, key=lambda image: image['text'].lower())
            image = self.question_maker('Available Images', 'image', images)

        # Key selection
        key = None
        all_keys = self.app.ec2_conn.get_all_key_pairs()
        if not all_keys:
            raise RuntimeError('No keys!\n')
        if parsed_args.key and parsed_args.key in [item.name for item in all_keys]:
            key = [item for item in all_keys if item.name == parsed_args.key][0]

        if not key:
            if len(all_keys) == 1:
                key = all_keys[0]
            else:
                key = self.question_maker('Available Keys', 'key',
                        [{'text': item.name, 'obj': item} for item in all_keys])

        # Zone Selection
        if parsed_args.zone == 'NoPreference':
            zone = None
        else:
            all_zones = self.app.ec2_conn.get_all_zones()
            if parsed_args.zone in [item.name for item in all_zones]:
                zone = [item for item in all_zones if item.name == parsed_args.zone][0]
            else:
                zones = [{'text': item.name, 'obj': item} for item in all_zones]
                zones.insert(0, {'text': 'No Preference'})
                zone = self.question_maker('Available Zones', 'zone', zones, start_at=0)

        # Security Group selection
        all_security_groups = self.app.ec2_conn.get_all_security_groups()
        security_group_ids = []
        if not all_security_groups:
            raise RuntimeError('No security groups!\n')

        if parsed_args.security_groups:
            parsed_groups = parsed_args.security_groups.split(',')
            for security_group in all_security_groups:
                for parsed_group in parsed_groups:
                    if parsed_group == security_group.name:
                        security_group_ids.append(security_group.id)

        if not security_group_ids:
            if len(all_security_groups) == 1:
                security_group_ids.append(all_security_groups[0].id)
            else:
                sorted_groups = sorted(all_security_groups, key=lambda group: group.name.lower())
                security_group = self.question_maker('Available Security Groups', 'security group',
                        [{'text': item.name, 'obj': item} for item in sorted_groups])
                security_group_ids.append(security_group.id)

        # user_data script
        if parsed_args.user_data:
            user_data = open('%s/%s' % (self.script_path, parsed_args.user_data), 'r').read()
        elif parsed_args.assume_yes:
            user_data = None
        else:
            script_files = glob.glob('%s/*.sh' % self.script_path)
            scripts = [{'text': 'Skip Step'}]
            scripts.extend([{'text': item[len(self.script_path) + 1:]} for item in script_files])
            script = self.question_maker('Select user-data script', 'script', scripts, start_at=0)
            if script == 'Skip Step':
                user_data = None
            else:
                user_data = open('%s/%s' % (self.script_path, script), 'r').read()

        kwargs = {
            'key_name': key.name,
            'instance_type': instance_type,
            'security_group_ids': security_group_ids,
        }
        if user_data:
            kwargs['user_data'] = user_data
        if hasattr(zone, 'name'):
            kwargs['placement'] = zone.name

        if not parsed_args.assume_yes and not self.sure_check():
            raise RuntimeError('Instance not created!')

        # Launch this thing
        self.app.stdout.write('Launching instance...\n')
        reservation = image.run(**kwargs)
        time.sleep(10)
        instance = reservation.instances[0]

        time.sleep(10)
        self.app.stdout.write('Add Name tag to instance\n')
        instance.add_tag('Name', parsed_args.name)

        while True:
            time.sleep(20)
            status = instance.update()
            if status == 'running':
                break
            self.app.stdout.write('%s\n' % status)

        time.sleep(20)
        self.app.stdout.write('Instance should now be running\n')
        if self.key_path:
            self.app.stdout.write('ssh -i %s/%s.pem %s@%s\n' % (self.key_path, key.name, self.get_user(instance), instance.public_dns_name))
        else:
            self.app.stdout.write('Public DNS: %s\n' % instance.public_dns_name)
