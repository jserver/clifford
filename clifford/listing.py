import logging
import os

from cliff.lister import Lister

from mixins import SingleInstanceMixin


ROWS, COLUMNS = [int(item) for item in os.popen('stty size', 'r').read().split()]


class Addresses(Lister):
    "List of IP addresses in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        addresses = self.app.ec2_conn.get_all_addresses()
        if not addresses:
            raise RuntimeError('No IP Addresses attached to account')

        reservations = self.app.ec2_conn.get_all_instances(instance_ids=[address.instance_id for address in addresses if address.instance_id])
        instance_dict = {}
        for res in reservations:
            for instance in res.instances:
                instance_dict[instance.id] = instance.tags.get('Name', '')

        return (('Public IP', 'Instance ID', 'Name'),
                ((address.public_ip, address.instance_id, instance_dict.get(address.instance_id, '')) for address in addresses)
                )


class AwsImages(Lister):
    "List of AWS images associated with owner."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        images = self.app.ec2_conn.get_all_images(owners=['self'])

        return (('Image ID', 'Name'),
                ((image.id, image.name) for image in images)
                )


class Buckets(Lister):
    "List of Buckets in S3."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        buckets = self.app.s3_conn.get_all_buckets()

        return (('Name', 'Website'),
                ((bucket.name, bucket.get_website_endpoint()) for bucket in buckets)
                )


class Builds(Lister):
    "List of builds in config."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        if 'Builds' not in self.app.config:
            raise RuntimeError('No Builds found!')
        builds = self.app.config['Builds']

        build_tuples = []
        for build in builds.keys():
            build_tuples.append((build,
                                 builds[build].get('size', ''),
                                 builds[build].get('image', ''),
                                 builds[build].get('key', ''),
                                 builds[build].get('zone', ''),
                                 builds[build].get('group', '')))

        return (('Name', 'Size', 'Image', 'Key', 'Zone', 'Group'),
                build_tuples
                )



class Bundles(Lister):
    "List of bundles in config."

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(Bundles, self).get_parser(prog_name)
        parser.add_argument('--py', dest='is_py_bundle', action='store_true')
        return parser


    def take_action(self, parsed_args):
        section = 'Bundles' if not parsed_args.is_py_bundle else 'PythonBundles'
        if section not in self.app.config:
            raise RuntimeError('No %s found!' % section)

        bundles = self.app.config[section]
        if not bundles:
            raise RuntimeError('No %s found!!' % section)

        max_name_len = max(4, max([len(bundle) for bundle in bundles.keys()]))
        max_bundles_len = COLUMNS - max_name_len - 7

        bundle_tuples = []
        for bundle in bundles.keys():
            if len(bundles[bundle]) > max_bundles_len:
                bundle_tuples.append((bundle, bundles[bundle][:max_bundles_len - 3] + '...'))
            else:
                bundle_tuples.append((bundle, bundles[bundle]))

        return (('Name', 'Packages'),
                bundle_tuples
                )


class Groups(Lister):
    "List of groups in config."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        section = 'Groups'
        if section not in self.app.config:
            raise RuntimeError('No %s found!' % section)

        groups = self.app.config[section]
        if not groups:
            raise RuntimeError('No %s found!!' % section)

        max_name_len = max(4, max([len(group) for group in groups.keys()]))
        max_groups_len = COLUMNS - max_name_len - 7

        group_tuples = []
        import pdb; pdb.set_trace()
        for group in groups.keys():
            items = ''
            for item in groups[group]:
                if item['Type'] == 'bundle':
                    items += item['Value'] + ' '
                elif item['Type'] == 'group':
                    items += '&' + item['Value'] + ' '
                elif item['Type'] == 'packages':
                    items += '$' + item['Value'] + ' '
            if items:
                items = items[:-1]

            if len(items) > max_groups_len:
                group_tuples.append((group, items[:max_groups_len - 3] + '...'))
            else:
                group_tuples.append((group, items))


        return (('Name', 'Items'),
                group_tuples
                )


class Images(Lister):
    "List of images stored in the config."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        if 'Images' not in self.app.config:
            raise RuntimeError('No images found!')

        images = self.app.config['Images']

        image_tuples = []

        image_ids = [images[image]['Id'] for image in images.keys()]
        for aws_image in self.app.ec2_conn.get_all_images(image_ids=image_ids):
            for image in images.keys():
                if images[image]['Id'] == aws_image.id:
                    images[image]['Name'] = aws_image.name
                    break

        for image in images.keys():
            image_tuples.append((image, images[image].get('Login', ''), images[image].get('Id', ''), images[image].get('Name', '')))

        return (('Nickname', 'Login', 'AMI ID', 'Name'),
                image_tuples
                )


class InstanceTags(Lister, SingleInstanceMixin):
    "List of tags on an ec2 instance."

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(InstanceTags, self).get_parser(prog_name)
        parser.add_argument('-y', dest='assume_yes', action='store_true')
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)

        return (('Tag', 'Value'),
                (instance.tags.iteritems())
                )


class Instances(Lister):
    "List of instances in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        reservations = self.app.ec2_conn.get_all_instances()
        instances = []
        for res in reservations:
            for instance in res.instances:
                instances.append((instance.tags.get('Name', ''),
                                  instance.id,
                                  instance.state,
                                  instance.instance_type[3:],
                                  'Y' if instance.root_device_type == 'ebs' else 'N',
                                  'Y' if instance.architecture == 'x86_64' else 'N',
                                  instance.placement,
                                  instance.public_dns_name))
                instances = sorted(instances, key=lambda instance: instance[0].lower())

        return (('Name', 'Id', 'State', 'Type', 'ebs', '64', 'Zone', 'Public DNS'),
                (instance for instance in instances)
                )


class Keys(Lister):
    "List of keys in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        keys = self.app.ec2_conn.get_all_key_pairs()

        return (('Name',),
                ((key.name,) for key in keys)
                )


class Projects(Lister):
    "List of projects in config."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        if 'Projects' not in self.app.config:
            raise RuntimeError('No Projects found!')
        projects = self.app.config['Projects']

        project_tuples = []
        for project in projects.keys():
            project_tuples.append((project,
                                 projects[project].get('Build', ''),
                                 projects[project].get('Count', '')))

        return (('Name', 'Build', 'Count'),
                project_tuples
                )


class Scripts(Lister):
    "List of scripts in script_path."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        return (('Name',),
                ((script,) for script in os.listdir(self.app.script_path) if not script.startswith('.'))
                )




class SecurityGroups(Lister):
    "List of security groups in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        security_groups = self.app.ec2_conn.get_all_security_groups()

        return (('Name', 'Description'),
                ((group.name, group.description) for group in security_groups)
                )


class Snapshots(Lister):
    "List of snapshots in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        snapshots = self.app.ec2_conn.get_all_snapshots(owner='self')

        return (('Name', 'ID', 'Size', 'Status', 'Progress' ),
                ((snapshot.tags.get('Name', ''),
                  snapshot.id,
                  '%s GiB' % snapshot.volume_size,
                  snapshot.status,
                  snapshot.progress) for snapshot in snapshots)
                )


class Volumes(Lister):
    "List of Volumes in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        volumes = self.app.ec2_conn.get_all_volumes()

        return (('Name', 'ID', 'Size', 'Type', 'Snapshot ID', 'Zone', 'Status', 'Instance ID'),
                ((volume.tags.get('Name', ''),
                  volume.id,
                  '%s GiB' % volume.size,
                  volume.type,
                  volume.snapshot_id,
                  volume.zone,
                  volume.status,
                  hasattr(volume, 'attach_data') and volume.attach_data.instance_id or '') for volume in volumes)
                )
