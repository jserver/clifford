from activity import launcher
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
        parser.add_argument('tag_name')
        return parser

    def take_action(self, parsed_args):
        instance_type = self.get_instance_type(parsed_args.size)
        image = self.get_image(parsed_args.image, return_item=True)
        key = self.get_key(parsed_args.key)
        zone = self.get_zone(parsed_args.zone)
        security_group_ids = self.get_security_groups(parsed_args.security_groups)
        user_data = self.get_user_data(parsed_args.user_data, parsed_args.assume_yes)

        build = {
            'Size': instance_type,
            'Login': image['Login'],
            'Image': image['Id'],
            'Key': key.name,
            'SecurityGroups': security_group_ids,
        }
        if hasattr(zone, 'name'):
            build['Zone'] = zone.name
        if user_data:
            build['UserData'] = user_data

        if not parsed_args.assume_yes and not self.sure_check():
            raise RuntimeError('Instance(s) not created!')

        launcher(config.aws_key_path, parsed_args.tag_name, build, num=parsed_args.num)
