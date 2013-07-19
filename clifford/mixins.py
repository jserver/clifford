import glob

from main import config


class LaunchOptionsMixin(object):
    def get_instance_type(self, size=''):
        SIZES = ['t1.micro', 'm1.small', 'm1.medium', 'm1.large']
        if size and size in SIZES:
            instance_type = size
        else:
            instance_type = self.question_maker('Available Sizes', 'size',
                    [{'text': sz} for sz in SIZES])

        return instance_type

    def get_image(self, image_id='', return_item=False):
        image = None
        if image_id:
            try:
                image = self.app.ec2_conn.get_image(image_id=image_id)
            except:
                pass

        if not image:
            if 'Images' not in config:
                raise RuntimeError('No Images found!\n')

            items = config['Images'].keys()

            image_ids = [config['Images'][item]['Id'] for item in items]
            if not image_ids:
                raise RuntimeError('No images found!')

            images = []
            for aws_image in self.app.ec2_conn.get_all_images(image_ids=image_ids):
                for item in items:
                    if config['Images'][item]['Id'] == aws_image.id:
                        images.append({'text': '%s - %s' % (item, aws_image.id), 'obj': aws_image})
            images = sorted(images, key=lambda image: image['text'].lower())
            image = self.question_maker('Available Images', 'image', images)

            if return_item:
                return [config['Images'][item] for item in items if config['Images'][item]['Id'] == image.id][0]

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
        script_path = self.app.script_path
        if filename:
            user_data = open('%s/%s' % (script_path, filename), 'r').read()
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
                user_data = open('%s/%s' % (script_path, script), 'r').read()

        return user_data


class PreseedMixin(object):
    def get_preseeds(self, bundle):
        preseeds = []
        packages = bundle.split(' ')
        for package in packages:
            if not self.app.cparser.has_section('debconf:%s' % package):
                continue
            options = self.app.cparser.options('debconf:%s' % package)
            if options:
                for option in options:
                    preseeds.append(self.app.cparser.get('debconf:%s' % package, option))
        return preseeds


class SingleInstanceMixin(object):
    def get_instance(self, name, arg_is_id=False):
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
                raise RuntimeError('More than one reservation returned, use --id')
            reservations = possible_reservations
        if not reservations:
            raise RuntimeError('No instances found')
        res = reservations[0]
        if not res.instances:
            raise RuntimeError('No instances wth name %s' % name)
        elif len(res.instances) > 1:
            raise RuntimeError('More than one instance in reservation!' % name)

        instance = res.instances[0]
        return instance

    def get_reservation(self, name):
        reservations = self.app.ec2_conn.get_all_instances(filters={'tag:Name': name})
        if not reservations:
            raise RuntimeError('No instances found')

        if len(reservations) > 1:
            raise RuntimeError('More than one reservation found!')

        return reservations[0]
