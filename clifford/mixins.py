class SingleInstanceMixin(object):
    def get_instance(self, name, arg_is_id):
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
        res = reservations[0]
        if not res.instances:
            raise RuntimeError('No instances wth name %s' % name)
        elif len(res.instances) > 1:
            raise RuntimeError('More than one instance in reservation!' % name)
        else:
            return res.instances[0]
        return None


class QuestionableMixin(object):
    def question_maker(self, question, item_type, dict_list):
        self.app.stdout.write(question + '\n')
        self.app.stdout.write('-' * len(question) + '\n')
        for index, item in enumerate(dict_list):
            answer_text = item['id']
            if 'name' in item:
                answer_text += ' - %s' % item['name']
            self.app.stdout.write('%s) %s\n' % (index, answer_text))
        item_choice = raw_input('Enter number of %s: ' % item_type)
        if not item_choice.isdigit() or int(item_choice) >= len(dict_list):
            self.app.stdout.write('Not a valid %s!\n' % item_type)
            return {}
        return dict_list[int(item_choice)]


class SureCheckMixin(object):
    def sure_check(self):
        you_sure = raw_input('Are you sure? ')
        if you_sure.lower() not in ['y', 'yes']:
            return False
        return True
