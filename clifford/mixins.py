import glob
import re

from main import config


class LaunchOptionsMixin(object):
    def get_instance_type(self, size=''):
        SIZES = ['m1.small', 'm3.medium']
        if size and size in SIZES:
            instance_type = size
        else:
            instance_type = self.question_maker('Available Sizes', 'size',
                                                [{'text': sz} for sz in SIZES])

        return instance_type

    def get_image(self, image_id='', return_key=False):
        keys = config.images.keys()

        image_ids = [config.images[key]['Id'] for key in keys]
        if not image_ids:
            raise RuntimeError('No images found!')

        images = []
        for aws_image in self.app.ec2_conn.get_all_images(image_ids=image_ids):
            for key in keys:
                if config.images[key]['Id'] == aws_image.id:
                    images.append({'text': '%s - %s' % (key, aws_image.id), 'obj': aws_image})
        images = sorted(images, key=lambda image: image['text'].lower())
        image = self.question_maker('Available Images', 'image', images)

        if return_key:
            return [key for key in keys if config.images[key]['Id'] == image.id][0]

        return image

    def get_key(self, key_name=''):
        key = None
        all_keys = self.app.ec2_conn.get_all_key_pairs()
        if not all_keys:
            raise RuntimeError('No keys!\n')
        if key_name and key_name in [item.name for item in all_keys]:
            key = [item for item in all_keys if item.name == key_name][0]

        if not key:
            if len(all_keys) == 1:
                key = all_keys[0]
            else:
                key = self.question_maker('Available Keys', 'key',
                                          [{'text': item.name, 'obj': item} for item in all_keys])

        return key

    def get_zone(self, zone_name=''):
        if zone_name == 'NoPreference':
            return None

        all_zones = self.app.ec2_conn.get_all_zones()
        if zone_name in [item.name for item in all_zones]:
            zone = [item for item in all_zones if item.name == zone_name][0]
        else:
            zones = [{'text': item.name, 'obj': item} for item in all_zones]
            zones.insert(0, {'text': 'No Preference'})
            zone = self.question_maker('Available Zones', 'zone', zones, start_at=0)

        return zone

    def get_security_groups(self, ids='', return_names=False):
        all_security_groups = self.app.ec2_conn.get_all_security_groups()
        if not all_security_groups:
            raise RuntimeError('No security groups!\n')

        security_groups = []

        if ids:
            parsed_groups = ids.split(',')
            for security_group in all_security_groups:
                for parsed_group in parsed_groups:
                    if parsed_group == security_group.name:
                        if return_names:
                            security_groups.append(security_group.name)
                        else:
                            security_groups.append(security_group.id)

        if not security_groups:
            if len(all_security_groups) == 1:
                if return_names:
                    security_groups.append(all_security_groups[0].name)
                else:
                    security_groups.append(all_security_groups[0].id)

            else:
                sorted_groups = sorted(all_security_groups, key=lambda group: group.name.lower())
                sec_grps = self.question_maker('Available Security Groups', 'security group',
                                               [{'text': item.name, 'obj': item} for item in sorted_groups],
                                               multiple_answers=True)
                if return_names:
                    security_groups.extend([sg.name for sg in sec_grps])
                else:
                    security_groups.extend([sg.id for sg in sec_grps])

        return security_groups

    def get_user_data(self, filename='', assume_yes=False, return_name=False):
        script_path = config.script_path
        if filename:
            with open('%s/%s' % (script_path, filename), 'r') as fh:
                user_data = fh.read()
        elif assume_yes:
            user_data = None
        else:
            script_files = glob.glob('%s/*.sh' % script_path)
            scripts = [{'text': 'Skip Step'}]
            scripts.extend([{'text': item[len(script_path) + 1:]} for item in script_files])
            script = self.question_maker('Select user-data script', 'script', scripts, start_at=0)
            if script == 'Skip Step':
                user_data = None
            elif return_name:
                user_data = script
            else:
                with open('%s/%s' % (script_path, script), 'r') as fh:
                    user_data = fh.read()

        return user_data


class PreseedMixin(object):
    def get_preseeds(self, bundle):
        preseeds = []
        packages = bundle.split(' ')
        for package in packages:
            full_name = 'debconf:%s' % package
            if full_name not in config:
                continue
            options = config[full_name]
            for option in options:
                preseeds.append(config[full_name][option])
        return preseeds


class InstanceMixin(object):
    def get_instance(self, name, arg_is_id=False, raise_error=True):
        if arg_is_id:
            reservations = self.app.ec2_conn.get_all_instances(instance_ids=[name])
        else:
            reservations = self.app.ec2_conn.get_all_instances(filters={'tag:Name': name})
            possible_reservations = []
            for res in reservations:
                for instance in res.instances:
                    if instance.state == 'terminated':
                        pass
                    else:
                        possible_reservations.append(res)
            if len(possible_reservations) > 1:
                raise RuntimeError('More than one reservation returned, use --id!')
            reservations = possible_reservations
        if not reservations:
            raise RuntimeError('No instances found!')
        res = reservations[0]
        if not res.instances:
            raise RuntimeError('No instances wth name %s!' % name)
        elif len(res.instances) > 1:
            raise RuntimeError('More than one instance in reservation!' % name)

        instance = res.instances[0]
        return instance

    def get_instances(self, name):
        regex = re.compile('(.*)-([0-9]+)$')
        instances = []
        reservations = self.app.ec2_conn.get_all_instances()
        for reservation in reservations:
            for instance in reservation.instances:
                name_tag = instance.tags.get('Name', '')
                if name == name_tag:
                    instances.append(instance)
                    continue
                m = regex.match(name_tag)
                if m and name == m.group(1):
                    instances.append(instance)
        return instances

    def get_instance_names(self):
        names = set()
        reservations = self.app.ec2_conn.get_all_instances()
        for reservation in reservations:
            for instance in reservation.instances:
                tag = instance.tags.get('Name', '')
                if tag:
                    names.add(tag.split(' [')[0])
        return names

    def get_project_instances(self, name):
        instances = []
        reservations = self.app.ec2_conn.get_all_instances()
        for reservation in reservations:
            for instance in reservation.instances:
                project_tag = instance.tags.get('Project', '')
                if project_tag and project_tag == name:
                    instances.append(instance)

        return instances

    def get_build_instances(self, name):
        instances = []
        reservations = self.app.ec2_conn.get_all_instances()
        for reservation in reservations:
            for instance in reservation.instances:
                build_tag = instance.tags.get('Build', '')
                if build_tag and build_tag == name:
                    instances.append(instance)
        return instances

    def get_reservation(self, name, project_name=None, build_name=None):
        tag_name = name.split(' [')[0]
        reservations = self.app.ec2_conn.get_all_instances()
        for reservation in reservations:
            for instance in reservation.instances:
                inst_tag_name = instance.tags.get('Name', '').split(' [')[0]
                if inst_tag_name != tag_name:
                    continue
                if project_name and instance.tags.get('Project', '') != project_name:
                    continue
                if build_name and instance.tags.get('Build', '') != build_name:
                    continue
                return reservation
        raise RuntimeError('Reservation not found!')

    def get_user(self, instance):
        keys = config.images.keys()
        for key in keys:
            if config.images[key]['Id'] == instance.image_id:
                return config.images[key]['Login']
        raise RuntimeError('Login not found!')
