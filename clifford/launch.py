from activity import launcher
from commands import BaseCommand
from main import config
from mixins import LaunchOptionsMixin


class Launch(BaseCommand, LaunchOptionsMixin):
    "Launches an ec2 instance."

    def get_parser(self, prog_name):
        parser = super(Launch, self).get_parser(prog_name)
        parser.add_argument('tag_name')
        return parser

    def take_action(self, parsed_args):
        if '[' in parsed_args.tag_name or ']' in parsed_args.tag_name:
            self.app.stdout.write('Clifford Tag Names may not include brackets')
            return

        instance_type = self.get_instance_type()
        image = self.get_image(return_item=True)
        key = self.get_key()
        zone = self.get_zone()
        security_group_ids = self.get_security_groups()
        user_data = self.get_user_data(assume_yes=False)

        raw_num = raw_input('Number of instances to launch (1)? ')
        if not raw_num or not raw_num.isdigit():
            num = 1
        else:
            num = int(raw_num)

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

        if not self.sure_check():
            raise RuntimeError('Instance(s) not created!')

        launcher(config.aws_key_path, parsed_args.tag_name, build=build, num=num, out=self.app.stdout)
