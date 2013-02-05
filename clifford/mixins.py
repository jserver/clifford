#Utilities go here
class SingleInstanceMixin(object):
    def get_instance(self, name):
        reservations = self.app.ec2_conn.get_all_instances(filters={'tag:Name': name})
        for res in reservations:
            if not res.instances:
                raise RuntimeError('No instances wth name %s' % name)
            elif len(res.instances) > 1:
                raise RuntimeError('More than one instance has name %s' % name)
            else:
                return res.instances[0]
            return None


class SureCheckMixin(object):
    def sure_check(self):
        you_sure = raw_input('Are you sure? ')
        if you_sure.lower() not in ['y', 'yes']:
            return False
        return True
