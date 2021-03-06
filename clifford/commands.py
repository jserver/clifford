import logging

from cliff.command import Command

from mixins import PreseedMixin, InstanceMixin


def enum(**enums):
    return type('Enum', (), enums)


class BaseCommand(Command, InstanceMixin):
    Bld = enum(SIZE='Size', LOGIN='Login', IMAGE='Image', KEY='Key',
               SECURITY_GROUPS='SecurityGroups', ZONE='Zone', USER_DATA='UserData',
               UPGRADE='Upgrade', GROUP='Group', PIP='Pip')

    log = logging.getLogger(__name__)

    def is_ok(self, name):
        if not name:
            return False
        reservations = self.app.ec2_conn.get_all_instances()
        for reservation in reservations:
            for instance in reservation.instances:
                if name == instance.tags.get('Name', ''):
                    return False
        return True

    def question_maker(self, question, item_type, dict_list, start_at=1, multiple_answers=False):
        self.app.stdout.write(question + '\n')
        self.app.stdout.write('-' * len(question) + '\n')
        for index, item in enumerate(dict_list):
            qnum = index + start_at
            self.app.stdout.write('%s) %s\n' % (qnum, item['text']))

        if multiple_answers:
            item_choices = raw_input('Enter comma separated choices: ')
            item_choices = [choice.strip() for choice in item_choices.split(',')]
            choices = []
            for item_choice in item_choices:
                if not item_choice.isdigit() or int(item_choice) - start_at >= len(dict_list):
                    raise RuntimeError('Not a valid %s!\n' % item_type)
                item = dict_list[int(item_choice) - start_at]
                if 'obj' in item:
                    choices.append(item['obj'])
                else:
                    choices.append(item['text'])
            return choices

        else:
            item_choice = raw_input('Enter number of %s: ' % item_type)
            if not item_choice.isdigit() or int(item_choice) - start_at >= len(dict_list):
                raise RuntimeError('Not a valid %s!\n' % item_type)
            choice = dict_list[int(item_choice) - start_at]
            if 'obj' in choice:
                return choice['obj']
            return choice['text']

    def sure_check(self, question='Are you sure? '):
        you_sure = raw_input(question)
        if you_sure.lower() not in ['y', 'yes']:
            return False
        return True

    def printOutError(self, out, error):
        for line in out.readlines():
            self.app.stdout.write('OUT: %s' % line)
        for line in error.readlines():
            self.app.stdout.write('ERROR: %s' % line)


class RemoteCommand(BaseCommand, PreseedMixin):

    def get_parser(self, prog_name):
        parser = super(RemoteCommand, self).get_parser(prog_name)
        parser.add_argument('option')
        return parser


class RemoteUserCommand(BaseCommand):

    def get_parser(self, prog_name):
        parser = super(RemoteUserCommand, self).get_parser(prog_name)
        parser.add_argument('user')
        return parser
