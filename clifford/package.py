import logging

from cliff.command import Command

from mixins import SureCheckMixin


class CreateGroup(Command):

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(CreateGroup, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        if self.app.cparser.has_option('Groups', parsed_args.name):
            raise RuntimeError('Group already exists!\n')
        packages = raw_input('Enter packages: ')
        if not packages:
            raise RuntimeError('No packages given!\n')
        if not self.app.cparser.has_section('Groups'):
            self.app.cparser.add_section('Groups')
        self.app.cparser.set('Groups', parsed_args.name, packages)
        self.app.write_config()


class CreatePackage(Command):

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(CreatePackage, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        if self.app.cparser.has_option('Packages', parsed_args.name):
            raise RuntimeError('Package already exists!\n')
        package_names = raw_input('Enter package names: ')
        if not package_names:
            raise RuntimeError('No package names given!\n')
        if not self.app.cparser.has_section('Packages'):
            self.app.cparser.add_section('Packages')
        self.app.cparser.set('Packages', parsed_args.name, package_names)
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


class DeletePackage(Command, SureCheckMixin):

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(DeletePackage, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Packages', parsed_args.name):
            raise RuntimeError('Package does not exist!\n')
        if self.sure_check():
            self.app.cparser.remove_option('Packages', parsed_args.name)
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
        packages = self.app.cparser.get('Groups', parsed_args.name)
        packages = packages.split(' ')

        new_packages = raw_input('Enter packages to add: ')
        if not new_packages:
            raise RuntimeError('No new packages given!\n')
        new_packages = new_packages.split(' ')
        for new_package in new_packages:
            if new_package not in packages:
                packages.append(new_package)
        self.app.cparser.set('Groups', parsed_args.name, ' '.join(packages))
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
        packages = self.app.cparser.get('Groups', parsed_args.name)
        packages = packages.split(' ')

        packages_to_remove = raw_input('Enter packages to remove: ')
        if not packages_to_remove:
            raise RuntimeError('No packages given to remove!\n')
        packages_to_remove = packages_to_remove.split(' ')
        for package_to_remove in packages_to_remove:
            if package_to_remove in packages:
                packages.remove(package_to_remove)
        self.app.cparser.set('Groups', parsed_args.name, ' '.join(packages))
        self.app.write_config()


class PackageAdd(Command):

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(PackageAdd, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Packages', parsed_args.name):
            raise RuntimeError('Package does not exist!\n')
        packages = self.app.cparser.get('Packages', parsed_args.name)
        packages = packages.split(' ')

        new_packages = raw_input('Enter package names to add: ')
        if not new_packages:
            raise RuntimeError('No new package names given!\n')
        new_packages = new_packages.split(' ')
        packages = list(set(packages).union(set(new_packages)))
        packages.sort()
        self.app.cparser.set('Packages', parsed_args.name, ' '.join(packages))
        self.app.write_config()


class PackageRemove(Command):

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(PackageRemove, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Packages', parsed_args.name):
            raise RuntimeError('Package does not exist!\n')
        packages = self.app.cparser.get('Packages', parsed_args.name)
        packages = packages.split(' ')

        bad_packages = raw_input('Enter package names to remove: ')
        if not bad_packages:
            raise RuntimeError('No package names given to remove!\n')
        bad_packages = bad_packages.split(' ')
        packages = list(set(packages).difference(set(bad_packages)))
        packages.sort()
        self.app.cparser.set('Packages', parsed_args.name, ' '.join(packages))
        self.app.write_config()
