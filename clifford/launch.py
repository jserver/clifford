import time

from commands import BaseCommand
from mixins import LaunchOptionsMixin


class Launch(BaseCommand, LaunchOptionsMixin):
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
        instance_type = self.get_instance_type(parsed_args.size)
        image = self.get_image(parsed_args.image)
        key = self.get_key(parsed_args.key)
        zone = self.get_zone(parsed_args.zone)
        security_group_ids = self.get_security_groups(parsed_args.security_groups)
        user_data = self.get_user_data(parsed_args.user_data, parsed_args.assume_yes)

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
        if self.aws_key_path:
            self.app.stdout.write('ssh -i %s/%s.pem %s@%s\n' % (self.aws_key_path, key.name, self.get_user(instance), instance.public_dns_name))
        else:
            self.app.stdout.write('Public DNS: %s\n' % instance.public_dns_name)
