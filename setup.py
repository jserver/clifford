#!/usr/bin/env python

PROJECT = 'clifford'

# Change docs/sphinx/conf.py too!
VERSION = '0.1'

from setuptools import setup, find_packages

try:
    long_description = open('README.rst', 'rt').read()
except IOError:
    long_description = ''

setup(
    name=PROJECT,
    version=VERSION,

    description='Clifford, ec2 made easy.',
    long_description=long_description,

    author='Joe Server',
    author_email='joe@jserver.io',

    url='https://github.com/jserver/clifford',
    download_url='https://github.com/jserver/clifford/tarball/master',

    classifiers=['Development Status :: 3 - Alpha',
                 'License :: OSI Approved :: Apache Software License',
                 'Programming Language :: Python',
                 'Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.7',
                 'Intended Audience :: Developers',
                 'Environment :: Console',
                 ],

    platforms=['Any'],

    scripts=[],

    provides=[],
    install_requires=['cliff', 'boto', 'paramiko'],

    namespace_packages=[],
    packages=find_packages(),
    include_package_data=True,

    entry_points={
        'console_scripts': [
            'clifford = clifford.main:main'
            ],
        'clifford': [
            # General
            'domain = clifford.actions:Domain',
            'key_paths = clifford.actions:KeyPaths',
            'script_path = clifford.actions:ScriptPath',

            # Lister tools
            'ls = clifford.listing:Instances',

            'addresses = clifford.listing:Addresses',
            'aws_images = clifford.listing:AwsImages',
            'buckets = clifford.listing:Buckets',
            'builds = clifford.listing:Builds',
            'bundles = clifford.listing:Bundles',
            'groups = clifford.listing:Groups',
            'images = clifford.listing:Images',
            'tags = clifford.listing:InstanceTags',
            'instances = clifford.listing:Instances',
            'keys = clifford.listing:Keys',
            'projects = clifford.listing:Projects',
            'scripts = clifford.listing:Scripts',
            'security groups = clifford.listing:SecurityGroups',
            'snapshots = clifford.listing:Snapshots',
            'volumes = clifford.listing:Volumes',

            # EC2
            'image = clifford.actions:Image',
            'create image = clifford.actions:CreateImage',
            'create snapshot = clifford.actions:CreateSnapshot',
            'del aws_image = clifford.actions:DeleteAwsImage',
            'del snapshot = clifford.actions:DeleteSnapshot',
            'del volume = clifford.actions:DeleteVolume',

            'build = clifford.build:Build',
            'launch = clifford.launch:Launch',
            'project = clifford.project:Project',
            'instance = clifford.show:Instance',
            'terminate = clifford.actions:Terminate',
            'reboot = clifford.actions:Reboot',
            'stop = clifford.actions:Stop',
            'start = clifford.actions:Start',
            'tag = clifford.actions:Tag',

            'adduser = clifford.remote:AddUser',

            'cnct = clifford.actions:Cnct',
            'run script = clifford.remote:Script',
            'copy = clifford.remote:CopyFile',
            'update = clifford.remote:Update',
            'upgrade = clifford.remote:Upgrade',

            'apt install = clifford.remote:AptGetInstall',
            'pip install = clifford.remote:PipInstall',
            'install bundle = clifford.remote:BundleInstall',
            'install group = clifford.remote:GroupInstall',

            #'add-apt = clifford.remote:AddAptInstall',
            #'ppa install = clifford.remote:PPAInstall',

            'bundle = clifford.package:Bundle',
            'group = clifford.package:Group',

            # Elastic IPs
            'associate = clifford.address:Associate',
            'disassociate = clifford.address:Disassociate',
            'allocate = clifford.address:Allocate',
            'release = clifford.address:Release',

            # S3
            'create bucket = clifford.storage:CreateBucket',
            'del bucket = clifford.storage:DeleteBucket',
            'download = clifford.storage:Download',
            'upload = clifford.storage:Upload',
            ],
        },

    zip_safe=False,
)
