import glob
import logging
import os
import StringIO
import subprocess
import time
from collections import namedtuple
from subprocess import call

import boto
import paramiko


Task = namedtuple('Task', ['build', 'instance_id', 'arg_list'])
LaunchResult = namedtuple('LaunchResult', ['build', 'instance_ids'])


def launcher(tag_name, aws_key_path, script_path, **kwargs):
    out = kwargs.get('out', StringIO.StringIO())

    if 'build' not in kwargs:
        out.write('Error: Build not found in kwargs to launcher')
        return
    build = kwargs['build']

    conn = boto.connect_ec2()
    image = conn.get_image(image_id=build['Image'])

    options = {
        'key_name': build['Key'],
        'instance_type': build['Size'],
        'security_group_ids': build['SecurityGroups'],
    }
    if 'UserData' in build:
        with open(os.path.join(script_path, build['UserData']), 'r') as fh:
            options['user_data'] = fh.read()
    if 'Zone' in build:
        options['placement'] = build['Zone']

    if kwargs.get('num', 1) > 1:
        options['min_count'] = kwargs['num']
        options['max_count'] = kwargs['num']

    out.write('Running instance(s)\n')
    reservation = image.run(**options)
    time.sleep(15)

    instances = reservation.instances
    if 'q' in kwargs:
        l = LaunchResult(build, [inst.id for inst in instances])
        kwargs['q'].put(l)
    count = len(instances)

    out.write('Waiting for instance(s) to come up\n')
    for i in range(8):
        time.sleep(15)
        ready = True
        for inst in instances:
            status = inst.update()
            if status != 'running':
                out.write('%s\n' % status)
                ready = False
                break
        if ready:
            out.write('Instance(s) now running\n')
            break
    else:
        out.write('All instance(s) are not created equal!\n')
        if 'out' in kwargs:
            return
        return out

    out.write('Adding Tags to instance(s)\n')
    for idx, inst in enumerate(instances):
        if 'Suffix' in build:
            full_name = '%s-%s' % (tag_name, build['Suffix'])
        else:
            full_name = tag_name

        if count == 1 and 'counter' not in kwargs:
            inst.add_tag('Name', full_name)
        else:
            inst.add_tag('Name', '%s-%s' % (full_name, idx + 1 + kwargs.get('counter', 0)))

        if 'project_name' in kwargs and kwargs['project_name']:
            inst.add_tag('Project', kwargs['project_name'])

        if 'build_name' in kwargs and kwargs['build_name']:
            inst.add_tag('Build', kwargs['build_name'])

        inst.add_tag('Login', build['Login'])

    time.sleep(20)
    out.write('Instance(s) should now be running\n')
    for inst in instances:
        if aws_key_path:
            out.write('ssh -i %s.pem %s@%s\n' % (os.path.join(aws_key_path, inst.key_name), build['Login'], inst.public_dns_name))
        else:
            out.write('Public DNS: %s\n' % inst.public_dns_name)
    if 'out' in kwargs:
        return
    return out


def add_user(aws_key_path, task):
    output = 'Running adduser on %s\n' % task.instance_id

    output += 'instance, '
    conn = boto.connect_ec2()
    reservations = conn.get_all_instances(instance_ids=[task.instance_id])
    instance = reservations[0].instances[0]
    pub_key_path = task.arg_list[0]
    adduser = task.build['Adduser']

    output += 'logger, '
    logname = 'adduser.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/adduser_%s.log' % instance.id)
    logger.addHandler(fh)

    output += 'connecting'
    ssh = paramiko.SSHClient()
    ssh.set_log_channel(logname)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    while True:
        try:
            ssh.connect(instance.public_dns_name, username=task.build['Login'], key_filename='%s.pem' % os.path.join(aws_key_path, instance.key_name))
            break
        except:
            output += ', sleep'
            time.sleep(60)

    output += '\n'

    output += 'Creating user, make sure to set password.\n'
    cmd = 'sudo adduser --disabled-password'
    #if 'Group' in adduser:
    #    cmd += ' --ingroup %s' % adduser['Group']
    cmd += ' --gecos "%s" %s' % (adduser['FullName'], adduser['User'])
    stdin, stdout, stderr = ssh.exec_command(cmd)
    for line in stderr.readlines():
        output += 'ERROR (adduser): %s\n' % line

    keys = glob.glob('%s/*.pub' % pub_key_path)

    if keys:
        user = adduser['User']
        stdin, stdout, stderr = ssh.exec_command('sudo su -c "mkdir /home/%s/.ssh && chown %s:%s /home/%s/.ssh && chmod 700 /home/%s/.ssh"' % (user, user, user, user, user))
        for line in stderr.readlines():
            output += 'ERROR (mkdir): %s\n' % line

        contents = ''
        for key in keys:
            with open(key, 'r') as f:
                contents += f.read()

        stdin, stdout, stderr = ssh.exec_command('sudo su -c "cat << EOF > /home/%s/.ssh/authorized_keys\n%sEOF"' % (user, contents))
        for line in stderr.readlines():
            output += 'ERROR (cat): %s\n' % line

        stdin, stdout, stderr = ssh.exec_command('sudo su -c "chown %s:%s /home/%s/.ssh/authorized_keys; chmod 600 /home/%s/.ssh/authorized_keys"' % (user, user, user, user))
        for line in stderr.readlines():
            output += 'ERROR (authorized_keys): %s\n' % line

    if 'CopyFiles' in adduser:
        file_names = ' '.join(adduser['CopyFiles'])
        output += subprocess.check_output(
                'scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no %s %s@%s:~' % (file_names, adduser['User'], instance.public_dns_name),
                stderr=subprocess.STDOUT,
                shell=True)
        output += '\n'

    #TODO: still need to be able to run a script as the new user

    ssh.close()
    return output


def copier(aws_key_path, task):
    output = 'Running Copier on %s\n' % task.instance_id

    output += 'instance, '
    conn = boto.connect_ec2()
    reservations = conn.get_all_instances(instance_ids=[task.instance_id])
    instance = reservations[0].instances[0]

    output += 'logger, '
    logname = 'copier.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/copier_%s.log' % instance.id)
    logger.addHandler(fh)

    output += 'copying\n'

    file_name = task.arg_list[0]

    try:
        retcode = call('scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s.pem %s %s@%s:~' % (os.path.join(aws_key_path, instance.key_name), file_name, task.build['Login'], instance.public_dns_name), shell=True)
        if retcode < 0:
            output += 'Child was terminated by signal %s\n' % -retcode
        else:
            output += 'Child returned %s\n' % retcode
    except OSError as e:
        output += 'Execution failed: %s\n' % e


def group_installer(aws_key_path, task):
    output = 'Running Group Installer on %s\n' % task.instance_id

    output += 'instance, '
    conn = boto.connect_ec2()
    reservations = conn.get_all_instances(instance_ids=[task.instance_id])
    instance = reservations[0].instances[0]

    output += 'logger, '
    logname = 'group_installer.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/group_installer_%s.log' % instance.id)
    logger.addHandler(fh)

    output += 'connecting, '
    ssh = paramiko.SSHClient()
    ssh.set_log_channel(logname)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    while True:
        try:
            ssh.connect(instance.public_dns_name, username=task.build['Login'], key_filename='%s.pem' % os.path.join(aws_key_path, instance.key_name))
            break
        except:
            output += 'sleep, '
            time.sleep(60)

    output += 'installing\n'
    has_error = False
    for bundle in task.arg_list[0]:
        name = bundle[0]
        packages = bundle[1]

        stdin, stdout, stderr = ssh.exec_command('sudo apt-get -y install %s' % packages)
        for line in stdout.readlines():
            if any([item in line for item in ['Note, selecting', 'is already the newest version']]):
                output += line
        for line in stderr.readlines():
            if line.startswith('E: '):
                output += line
                has_error = True
        if has_error:
            output += 'Unable to Continue!\n'
            ssh.close()
            return output
        time.sleep(5)
        if name == 'packages':
            output += 'Installed packages: %s\n' % packages
        else:
            output += 'Installed bundle: %s\n' % name

    ssh.close()
    return output


def pip_installer(aws_key_path, task):
    output = 'Running Pip Installer on %s\n' % task.instance_id

    output += 'instance, '
    conn = boto.connect_ec2()
    reservations = conn.get_all_instances(instance_ids=[task.instance_id])
    instance = reservations[0].instances[0]

    output += 'logger, '
    logname = 'pip_installer.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/pip_installer_%s.log' % instance.id)
    logger.addHandler(fh)

    output += 'connecting'
    ssh = paramiko.SSHClient()
    ssh.set_log_channel(logname)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    while True:
        try:
            ssh.connect(instance.public_dns_name, username=task.build['Login'], key_filename='%s.pem' % os.path.join(aws_key_path, instance.key_name))
            break
        except:
            output += ', sleep'
            time.sleep(60)
    output += '\n'

    packages = task.arg_list[0]
    stdin, stdout, stderr = ssh.exec_command('sudo pip install %s' % packages)
    for line in stdout.readlines():
        if line.startswith('Installed') or line.startswith('Finished') or line.startswith('Successfully'):
            output += line

    ssh.close()
    return output


def script_runner(aws_key_path, task):
    output = 'Running Script on %s\n' % task.instance_id

    user = task.arg_list[0]

    output += 'instance, '
    conn = boto.connect_ec2()
    reservations = conn.get_all_instances(instance_ids=[task.instance_id])
    instance = reservations[0].instances[0]
    name_tag = instance.tags.get('Name')

    output += 'logger, '
    logname = 'script_runner.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/script_runner_%s.log' % instance.id)
    logger.addHandler(fh)

    output += 'connecting'
    ssh = paramiko.SSHClient()
    ssh.set_log_channel(logname)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    while True:
        try:
            if user in ['admin', 'ec2-user', 'ubuntu']:
                ssh.connect(instance.public_dns_name, username=user, key_filename='%s.pem' % os.path.join(aws_key_path, instance.key_name))
            else:
                ssh.connect(instance.public_dns_name, username=user)
            break
        except:
            output += ', sleep'
            time.sleep(60)
    output += '\n'

    script = task.arg_list[1]
    copy_only = task.arg_list[2]
    script_name = os.path.basename(script)

    with open(script, 'r') as f:
        contents = f.read()
        if user in ['admin', 'ec2-user', 'ubuntu'] and 'ScriptFormatArgs' in task.build:
            format_args = task.build['ScriptFormatArgs'].split(',')
            format_args = [name_tag for arg in format_args if arg == '@name']
            contents = contents % tuple(format_args)
        ssh.exec_command('cat << EOF > %s\n%s\nEOF' % (script_name, contents))
        time.sleep(5)
        ssh.exec_command('chmod 744 %s' % script_name)

    if not copy_only:
        channel = ssh.get_transport().open_session()
        channel.settimeout(0.1)
        channel.input_enabled = True
        forward = paramiko.agent.AgentRequestHandler(channel)

        channel.exec_command('/home/%s/%s' % (user, script_name))

        while True:
            time.sleep(5)
            if channel.exit_status_ready():
                break
        status = channel.recv_exit_status()
        output += 'Script status: %s\n' % status

        channel.close()
        forward.close()

    ssh.close()
    return output


def upgrade(aws_key_path, task):
    output = 'Running %s on %s\n' % (task.build['Upgrade'], task.instance_id)

    output += 'instance, '
    conn = boto.connect_ec2()
    reservations = conn.get_all_instances(instance_ids=[task.instance_id])
    instance = reservations[0].instances[0]

    output += 'logger, '
    logname = 'upgrade.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/upgrade_%s.log' % instance.id)
    logger.addHandler(fh)

    output += 'connecting, '
    ssh = paramiko.SSHClient()
    ssh.set_log_channel(logname)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    while True:
        try:
            ssh.connect(instance.public_dns_name, username=task.build['Login'], key_filename='%s.pem' % os.path.join(aws_key_path, instance.key_name))
            break
        except:
            output += 'sleep, '
            time.sleep(60)

    output += 'hosts\n'
    stdin, stdout, stderr = ssh.exec_command('sudo su -c "echo \'\n### CLIFFORD\n127.0.1.1\t%s\' >> /etc/hosts"' % instance.tags.get('Name'))

    has_error = False
    stdin, stdout, stderr = ssh.exec_command('sudo apt-get -y update')
    for line in stderr.readlines():
        if line.startswith('E: '):
            output += line
            has_error = True
    if has_error:
        output += 'Unable to Continue!\n'
        ssh.close()
        return output
    time.sleep(5)
    output += 'UPDATED\n'

    stdin, stdout, stderr = ssh.exec_command('sudo apt-get -s upgrade')
    string_list = ['The following packages have been kept back:', 'The following packages will be upgraded:']
    for line in stdout.readlines():
        if line.rstrip() in string_list or line.startswith('  '):
            output += line
    time.sleep(5)

    if task.build['Upgrade'] in ['upgrade', 'dist-upgrade']:
        stdin, stdout, stderr = ssh.exec_command('sudo su -c "env DEBIAN_FRONTEND=noninteractive apt-get -y -o DPkg::Options::=--force-confnew %s"' % task.build['Upgrade'])
        for line in stderr.readlines():
            if line.startswith('E: '):
                output += line
                has_error = True
        if has_error:
            output += 'Unable to Continue!\n'
            ssh.close()
            return output
        time.sleep(5)
        output += '%sD\n' % task.build['Upgrade'].upper()

    ssh.close()

    if task.build['Upgrade'] == 'dist-upgrade':
        time.sleep(5)
        output += 'Rebooting...\n'
        instance.reboot()
        time.sleep(60)

    return output
