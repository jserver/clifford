import logging

from cliff.command import Command

from mixins import PreseedMixin, SingleInstanceMixin


class BaseCommand(Command):

    log = logging.getLogger(__name__)

    def get_option(self, section, option, raise_error=True):
        if not self.app.cparser.has_option(section, option):
            if raise_error:
                raise RuntimeError('No %s set!' % option)
            else:
                return None
        return self.app.cparser.get(section, option)

    def question_maker(self, question, item_type, dict_list, start_at=1):
        self.app.stdout.write(question + '\n')
        self.app.stdout.write('-' * len(question) + '\n')
        for index, item in enumerate(dict_list):
            qnum = index + start_at
            self.app.stdout.write('%s) %s\n' % (qnum, item['text']))
        item_choice = raw_input('Enter number of %s: ' % item_type)
        if not item_choice.isdigit() or int(item_choice) - start_at >= len(dict_list):
            self.app.stdout.write('Not a valid %s!\n' % item_type)
            return {}
        choice = dict_list[int(item_choice) - start_at]
        if 'obj' in choice:
            return choice['obj']
        return choice

    def sure_check(self):
        you_sure = raw_input('Are you sure? ')
        if you_sure.lower() not in ['y', 'yes']:
            return False
        return True


class InstanceCommand(BaseCommand, SingleInstanceMixin):

    def get_parser(self, prog_name):
        parser = super(InstanceCommand, self).get_parser(prog_name)
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('name')
        return parser


class RemoteCommand(InstanceCommand, PreseedMixin):

    def get_parser(self, prog_name):
        parser = super(RemoteCommand, self).get_parser(prog_name)
        parser.add_argument('option')
        return parser


class RemoteUserCommand(InstanceCommand):

    def get_parser(self, prog_name):
        parser = super(RemoteUserCommand, self).get_parser(prog_name)
        parser.add_argument('user')
        return parser
