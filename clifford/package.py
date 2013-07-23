from collections import OrderedDict
from commands import BaseCommand
from main import config


class Bundle(BaseCommand):

    def get_parser(self, prog_name):
        parser = super(Bundle, self).get_parser(prog_name)
        parser.add_argument('--py', dest='is_py_bundle', action='store_true')
        parser.add_argument('-s', '--show', action='store_true')
        parser.add_argument('-a', '--add', action='store_true')
        parser.add_argument('-r', '--remove', action='store_true')
        parser.add_argument('-u', '--update', action='store_true')
        parser.add_argument('bundle_name')
        return parser

    def take_action(self, parsed_args):
        name = parsed_args.bundle_name
        section = 'Bundles' if not parsed_args.is_py_bundle else 'PythonBundles'
        if section not in config:
            config[section] = OrderedDict()

        if parsed_args.add:
            if name in config[section]:
                raise RuntimeError('%s already exists!' % name)

            packages = raw_input('Enter package names: ')
            if not packages:
                raise RuntimeError('No package names given!\n')

            config[section][name] = packages
            config.save()

        else:
            if name not in config[section]:
                raise RuntimeError('No %s %s found!' % (name, section[:-1]))

            if parsed_args.show:
                self.app.stdout.write(config[section][name] + '\n')

            elif parsed_args.update:
                packages = raw_input('Enter package names: ')
                if not packages:
                    raise RuntimeError('No package names given!\n')

                config[section][name] = packages
                config.save()

            elif parsed_args.remove:
                del(config[section][name])
                config.save()


class Group(BaseCommand):

    def get_parser(self, prog_name):
        parser = super(Group, self).get_parser(prog_name)
        parser.add_argument('-s', '--show', action='store_true')
        parser.add_argument('-a', '--add', action='store_true')
        parser.add_argument('-r', '--remove', action='store_true')
        parser.add_argument('-u', '--update', action='store_true')
        parser.add_argument('group_name')
        return parser

    def take_action(self, parsed_args):
        name = parsed_args.group_name
        section = 'Groups'
        if section not in config:
            config[section] = OrderedDict()

        if parsed_args.add:
            if name in config[section]:
                raise RuntimeError('%s already exists!' % name)

            group_items = self.get_group_items()
            if not group_items:
                raise RuntimeError('Nothing to save!\n')

            config[section][name] = group_items
            config.save()

        else:
            if name not in config[section]:
                raise RuntimeError('No %s %s found!' % (name, section[:-1]))

            if parsed_args.show:
                for item in config[section][name]:
                    self.app.stdout.write('[%s] %s\n' % (item['Type'], item['Value']))

            elif parsed_args.update:
                group_items = self.get_group_items()
                if not group_items:
                    raise RuntimeError('Nothing to save!\n')

                config[section][name] = group_items
                config.save()

            elif parsed_args.remove:
                del(config[section][name])
                config.save()

    def get_group_items(self):
        group_items = []
        while True:
            type_options = [{'text': 'Finished'}]
            if 'Bundles' in config and config.bundles.keys():
                type_options.append({'text': 'Bundle'})
            if 'Groups' in config and config.groups.keys():
                type_options.append({'text': 'Group'})
            type_options.append({'text': 'Packages'})

            type_option = self.question_maker('Select item type', 'item_type', type_options, start_at=0)
            if type_option == 'Bundle':
                bundle_options = [{'text': bundle} for bundle in config.bundles.keys()]
                bundle_option = self.question_maker('Select bundle', 'bundle', bundle_options)
                if not bundle_option:
                    self.app.stdout.write('Fail!')
                    continue
                group_items.append({'Type': 'bundle', 'Value': bundle_option})

            elif type_option == 'Group':
                group_options = [{'text': group} for group in config.groups.keys()]
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
