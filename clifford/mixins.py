import os


class KeyMixin(object):
    def get_option(self, section, option, raise_error=True):
        if not self.app.cparser.has_option(section, option):
            if raise_error:
                raise RuntimeError('No %s set!' % option)
            else:
                return None
        value = self.app.cparser.get(section, option)
        if option.endswith('_path'):
            value = os.path.expanduser(value)
            value = os.path.expandvars(value)
        return value

    @property
    def key_path(self):
        return self.get_option('General', 'key_path')

    @property
    def script_path(self):
        return self.get_option('General', 'script_path')


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
