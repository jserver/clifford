import os
import time

from commands import BaseCommand
from main import config
from mixins import LaunchOptionsMixin


class Launch(BaseCommand, LaunchOptionsMixin):
    "Launches an ec2 instance."

    def get_parser(self, prog_name):
        parser = super(Launch, self).get_parser(prog_name)
        parser.add_argument('-y', dest='assume_yes', action='store_true')
        parser.add_argument('--size')
        parser.add_argument('--login')
        parser.add_argument('--image')
        parser.add_argument('--key')
        parser.add_argument('--zone')
        parser.add_argument('--security-groups')
        parser.add_argument('--user-data')
        parser.add_argument('--num', type=int, default=1)
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

        if parsed_args.num > 1:
            plural = 's'
            kwargs['min_count'] = parsed_args.num
            kwargs['max_count'] = parsed_args.num
        else:
            plural = ''

        if not parsed_args.assume_yes and not self.sure_check():
            raise RuntimeError('Instance%s not created!' % plural)

        # Launch this thing
        self.app.stdout.write('Launching instance%s...\n' % plural)
        reservation = image.run(**kwargs)
        time.sleep(10)

        instances = reservation.instances
        time.sleep(10)
        self.app.stdout.write('Add Name tag to instance%s\n' % plural)
        for idx, inst in enumerate(reservation.instances):
            inst.add_tag('Name', parsed_args.name)
            inst.add_tag('Clifford', '%s-%s' % (parsed_args.name, idx + 1))

        cnt = 0
        while cnt < 6:
            cnt += 1
            time.sleep(20)
            ready = True
            for inst in instances:
                status = inst.update()
                if status != 'running':
                    self.app.stdout.write('%s\n' % status)
                    ready = False
                    break
            if ready:
                break
        if cnt == 6:
            raise RuntimeError('All instance%s are not created equal!' % plural)

        time.sleep(20)
        self.app.stdout.write('Instance%s should now be running\n' % plural)
        for inst in instances:
            if config.aws_key_path:
                self.app.stdout.write('ssh -i %s.pem %s@%s\n' % (os.path.join(config.aws_key_path, key.name), parsed_args.login, inst.public_dns_name))
            else:
                self.app.stdout.write('Public DNS: %s\n' % inst.public_dns_name)
