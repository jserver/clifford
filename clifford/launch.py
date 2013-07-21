from activity import launcher
from commands import BaseCommand
from main import config
from mixins import LaunchOptionsMixin


class Launch(BaseCommand, LaunchOptionsMixin):
    "Launches an ec2 instance."

    def get_parser(self, prog_name):
        parser = super(Launch, self).get_parser(prog_name)
        parser.add_argument('-y', dest='assume_yes', action='store_true')
        parser.add_argument('--project')
        parser.add_argument('--build')
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
        image = self.get_image(parsed_args.image, return_item=True)
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
            kwargs['min_count'] = parsed_args.num
            kwargs['max_count'] = parsed_args.num

        if not parsed_args.assume_yes and not self.sure_check():
            raise RuntimeError('Instance(s) not created!')

        # Launch this thing
        project = parsed_args.project or ''
        build = parsed_args.build or ''
        launcher(image['Id'], project, build, parsed_args.name, config.aws_key_path, parsed_args.login, **kwargs)
