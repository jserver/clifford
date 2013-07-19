from collections import OrderedDict
from commands import BaseCommand


class Bundle(BaseCommand):

    def get_parser(self, prog_name):
        parser = super(Bundle, self).get_parser(prog_name)
        parser.add_argument('--py', dest='is_py_bundle', action='store_true')
        parser.add_argument('-s', '--show', action='store_true')
        parser.add_argument('-c', '--create', action='store_true')
        parser.add_argument('-d', '--delete', action='store_true')
        parser.add_argument('-u', '--update', action='store_true')
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        section = 'Bundles' if not parsed_args.is_py_bundle else 'PythonBundles'
        if section not in self.app.config:
            self.app.config[section] = OrderedDict()

        if parsed_args.create:
            if parsed_args.name in self.app.config[section]:
                raise RuntimeError('%s already exists!' % parsed_args.name)

            packages = raw_input('Enter package names: ')
            if not packages:
                raise RuntimeError('No package names given!\n')

            self.app.config[section][parsed_args.name] = packages
            self.app.write_config()

        else:
            if parsed_args.name not in self.app.config[section]:
                raise RuntimeError('No %s %s found!' % (parsed_args.name, section[:-1]))

            if parsed_args.show:
                self.app.stdout.write(self.app.config[section][parsed_args.name] + '\n')

            elif parsed_args.update:
                packages = raw_input('Enter package names: ')
                if not packages:
                    raise RuntimeError('No package names given!\n')

                self.app.config[section][parsed_args.name] = packages
                self.app.write_config()

            elif parsed_args.delete:
                del(self.app.config[section][parsed_args.name])
                self.app.write_config()


class Group(BaseCommand):

    def get_parser(self, prog_name):
        parser = super(Group, self).get_parser(prog_name)
        parser.add_argument('-s', '--show', action='store_true')
        parser.add_argument('-c', '--create', action='store_true')
        parser.add_argument('-d', '--delete', action='store_true')
        parser.add_argument('-u', '--update', action='store_true')
        parser.add_argument('name')
        return parser

    def get_group_items(self):
        group_items = []
        while True:
            type_options = [{'text': 'Finished'}]
            if 'Bundles' in self.app.config and self.app.config['Bundles'].keys():
                type_options.append({'text': 'Bundle'})
            if 'Groups' in self.app.config and self.app.config['Groups'].keys():
                type_options.append({'text': 'Group'})
            type_options.append({'text': 'Packages'})

            type_option = self.question_maker('Select item type', 'item_type', type_options, start_at=0)
            if type_option == 'Bundle':
                bundle_options = [{'text': bundle} for bundle in self.app.config['Bundles'].keys()]
                bundle_option = self.question_maker('Select bundle', 'bundle', bundle_options)
                if not bundle_option:
                    self.app.stdout.write('Fail!')
                    continue
                group_items.append({'Type': 'bundle', 'Value': bundle_option})

            elif type_option == 'Group':
                group_options = [{'text': group} for group in self.app.config['Groups'].keys()]
                group_option = self.question_maker('Select group', 'group', group_options)
                if not group_option:
                    self.app.stdout.write('Fail!')
                    continue
                group_items.append({'Type': 'group', 'Value': group_option})

            elif type_option == 'Packages':
                package = raw_input('Enter package names: ')
                if not package:
                    self.app.stdout.write('Fail!')
                    continue
                group_items.append({'Type': 'packages', 'Value': package})

            else:
                break

        return group_items

    def take_action(self, parsed_args):
        section = 'Groups'
        if section not in self.app.config:
            self.app.config[section] = OrderedDict()

        if parsed_args.create:
            if parsed_args.name in self.app.config[section]:
                raise RuntimeError('%s already exists!' % parsed_args.name)

            group_items = self.get_group_items()
            if not group_items:
                raise RuntimeError('Nothing to save!\n')

            self.app.config[section][parsed_args.name] = group_items
            self.app.write_config()

        else:
            if parsed_args.name not in self.app.config[section]:
                raise RuntimeError('No %s %s found!' % (parsed_args.name, section[:-1]))

            if parsed_args.show:
                for item in self.app.config[section][parsed_args.name]:
                    self.app.stdout.write('[%s] %s\n' % (item['Type'], item['Value']))

            elif parsed_args.update:
                group_items = self.get_group_items()
                if not group_items:
                    raise RuntimeError('Nothing to save!\n')

                self.app.config[section][parsed_args.name] = group_items
                self.app.write_config()

            elif parsed_args.delete:
                del(self.app.config[section][parsed_args.name])
                self.app.write_config()
