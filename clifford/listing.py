import logging
import os

from cliff.lister import Lister


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
                instance_dict[instance.id] = instance.tags.get('Name')

        return (('Public IP', 'Instance ID', 'Name'),
                ((address.public_ip, address.instance_id, instance_dict.get(address.instance_id, '')) for address in addresses)
                )


class Buckets(Lister):
    "List of Buckets in S3."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        buckets = self.app.s3_conn.get_all_buckets()

        return (('Name', 'Website'),
                ((bucket.name, bucket.get_website_endpoint()) for bucket in buckets)
                )


class Bundles(Lister):
    "List of bundles in config."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        if not self.app.cparser.has_section('Bundles'):
            raise RuntimeError('No bundles found!')

        bundles = self.app.cparser.items('Bundles')
        max_name_len = max(4, max([len(bundle[0]) for bundle in bundles]))
        max_bundles_len = COLUMNS - max_name_len - 7

        bundle_tuples = []
        for bundle in bundles:
            if len(bundle[1]) > max_bundles_len:
                bundle_tuples.append((bundle[0], bundle[1][:max_bundles_len - 3] + '...'))
            else:
                bundle_tuples.append((bundle[0], bundle[1]))


        return (('Name', 'Packages'),
                bundle_tuples
                )


class Groups(Lister):
    "List of groups in config."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        if not self.app.cparser.has_section('Groups'):
            raise RuntimeError('No groups found!')

        groups = self.app.cparser.items('Groups')
        max_name_len = max(4, max([len(group[0]) for group in groups]))
        max_groups_len = COLUMNS - max_name_len - 7

        group_tuples = []
        for group in groups:
            if len(group[1]) > max_groups_len:
                group_tuples.append((group[0], group[1][:max_groups_len - 3] + '...'))
            else:
                group_tuples.append((group[0], group[1]))


        return (('Name', 'Bundles'),
                group_tuples
                )


class Images(Lister):
    "List of images stored in the config."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Images', 'images'):
            raise RuntimeError('No images added!')

        images_str = self.app.cparser.get('Images', 'images')
        image_ids = images_str.split(',')
        if not image_ids:
            raise RuntimeError('No images added!')

        images = [(image.id, image.name) for image in self.app.ec2_conn.get_all_images(image_ids=image_ids)]
        images = sorted(images, key=lambda image: image[1].lower())

        return (('Image ID', 'Name'),
                tuple(images)
                )


class Instances(Lister):
    "List of instances in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        reservations = self.app.ec2_conn.get_all_instances()
        instances = []
        for res in reservations:
            for instance in res.instances:
                instances.append((instance.tags.get('Name'),
                                  instance.id,
                                  instance.state,
                                  instance.instance_type,
                                  instance.root_device_type,
                                  instance.architecture,
                                  instance.placement))
                instances = sorted(instances, key=lambda instance: instance[0].lower())

        return (('Name', 'Id', 'State', 'Type', 'RootDevice', 'Arch', 'Zone'),
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


class PythonBundles(Lister):
    "List of python bundles in config."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        if not self.app.cparser.has_section('Python Bundles'):
            raise RuntimeError('No bundles found!')

        bundles = self.app.cparser.items('Python Bundles')
        max_name_len = max(4, max([len(bundle[0]) for bundle in bundles]))
        max_bundles_len = COLUMNS - max_name_len - 7

        bundle_tuples = []
        for bundle in bundles:
            if len(bundle[1]) > max_bundles_len:
                bundle_tuples.append((bundle[0], bundle[1][:max_bundles_len - 3] + '...'))
            else:
                bundle_tuples.append((bundle[0], bundle[1]))


        return (('Name', 'Packages'),
                bundle_tuples
                )


class Scripts(Lister):
    "List of scripts in script_path."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        return (('Name',),
                ((script,) for script in os.listdir(self.script_path) if not script.startswith('.'))
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
                ((volume.tags.get('name', ''),
                  volume.id,
                  '%s GiB' % volume.size,
                  volume.type,
                  volume.snapshot_id,
                  volume.zone,
                  volume.status,
                  hasattr(volume, 'attach_data') and volume.attach_data.instance_id or '') for volume in volumes)
                )
