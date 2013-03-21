import logging

from cliff.command import Command

from mixins import SureCheckMixin


class BundleAdd(Command):

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(BundleAdd, self).get_parser(prog_name)
        parser.add_argument('--py', dest='is_py_bundle', action='store_true')
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        section = 'Bundles' if not is_py_bundle else 'Python Bundles'
        if not self.app.cparser.has_option(section, parsed_args.name):
            raise RuntimeError('Bundle does not exist!\n')
        bundle = self.app.cparser.get(section, parsed_args.name)
        packages = bundle.split(' ')

        new_packages = raw_input('Enter packages to add: ')
        if not new_packages:
            raise RuntimeError('No packages to add!\n')
        new_packages = new_packages.split(' ')
        packages = list(set(packages).union(set(new_packages)))
        packages.sort()
        self.app.cparser.set(section, parsed_args.name, ' '.join(packages))
        self.app.write_config()


class BundleRemove(Command):

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(BundleRemove, self).get_parser(prog_name)
        parser.add_argument('--py', dest='is_py_bundle', action='store_true')
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        section = 'Bundles' if not is_py_bundle else 'Python Bundles'
        if not self.app.cparser.has_option(section, parsed_args.name):
            raise RuntimeError('Bundle does not exist!\n')
        bundle = self.app.cparser.get(section, parsed_args.name)
        packages = bundle.split(' ')

        packages_to_remove = raw_input('Enter packages to remove: ')
        if not packages_to_remove:
            raise RuntimeError('No packages to remove!\n')
        packages_to_remove = packages_to_remove.split(' ')
        packages = list(set(packages).difference(set(packages_to_remove)))
        packages.sort()
        self.app.cparser.set(section, parsed_args.name, ' '.join(packages))
        self.app.write_config()


class CreateBundle(Command):

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(CreateBundle, self).get_parser(prog_name)
        parser.add_argument('--py', dest='is_py_bundle', action='store_true')
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        section = 'Bundles' if not is_py_bundle else 'Python Bundles'
        if self.app.cparser.has_option(section, parsed_args.name):
            raise RuntimeError('Bundle already exists!\n')
        packages = raw_input('Enter package names: ')
        if not packages:
            raise RuntimeError('No package names given!\n')
        if not self.app.cparser.has_section(section):
            self.app.cparser.add_section(section)
        self.app.cparser.set(section, parsed_args.name, packages)
        self.app.write_config()


class CreateGroup(Command):

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(CreateGroup, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        if self.app.cparser.has_option('Groups', parsed_args.name):
            raise RuntimeError('Group already exists!\n')
        bundles = raw_input('Enter bundles: ')
        if not bundles:
            raise RuntimeError('No bundles given!\n')
        if not self.app.cparser.has_section('Groups'):
            self.app.cparser.add_section('Groups')
        self.app.cparser.set('Groups', parsed_args.name, bundles)
        self.app.write_config()


class DeleteBundle(Command, SureCheckMixin):

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(DeleteBundle, self).get_parser(prog_name)
        parser.add_argument('--py', dest='is_py_bundle', action='store_true')
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        section = 'Bundles' if not is_py_bundle else 'Python Bundles'
        if not self.app.cparser.has_option(section, parsed_args.name):
            raise RuntimeError('Bundle does not exist!\n')
        if self.sure_check():
            self.app.cparser.remove_option(section, parsed_args.name)
            self.app.write_config()


class DeleteGroup(Command, SureCheckMixin):

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(DeleteGroup, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Groups', parsed_args.name):
            raise RuntimeError('Group does not exist!\n')
        if self.sure_check():
            self.app.cparser.remove_option('Groups', parsed_args.name)
            self.app.write_config()


class GroupAdd(Command):

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(GroupAdd, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Groups', parsed_args.name):
            raise RuntimeError('Group does not exist!\n')
        group = self.app.cparser.get('Groups', parsed_args.name)
        bundles = group.split(' ')

        new_bundles = raw_input('Enter bundles to add: ')
        if not new_bundles:
            raise RuntimeError('No new bundles given!\n')
        new_bundles = new_bundles.split(' ')
        for new_bundle in new_bundles:
            if new_bundle not in bundles:
                bundles.append(new_bundle)
        self.app.cparser.set('Groups', parsed_args.name, ' '.join(bundles))
        self.app.write_config()


class GroupRemove(Command):

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(GroupRemove, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Groups', parsed_args.name):
            raise RuntimeError('Group does not exist!\n')
        group = self.app.cparser.get('Groups', parsed_args.name)
        bundles = group.split(' ')

        bundles_to_remove = raw_input('Enter bundles to remove: ')
        if not bundles_to_remove:
            raise RuntimeError('No bundles to remove!\n')
        bundles_to_remove = bundles_to_remove.split(' ')
        for bundle_to_remove in bundles_to_remove:
            if bundle_to_remove in bundles:
                bundles.remove(bundle_to_remove)
        self.app.cparser.set('Groups', parsed_args.name, ' '.join(bundles))
        self.app.write_config()
