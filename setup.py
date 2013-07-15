#!/usr/bin/env python

PROJECT = 'clifford'

# Change docs/sphinx/conf.py too!
VERSION = '0.1'

# Bootstrap installation of Distribute
import distribute_setup
distribute_setup.use_setuptools()

from setuptools import setup, find_packages

from distutils.util import convert_path
from fnmatch import fnmatchcase
import os
import sys

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
    author_email='servernyc@gmail.com',

    url='https://github.com/jserver/clifford',
    download_url='https://github.com/jserver/clifford/tarball/master',

    classifiers=['Development Status :: 3 - Alpha',
                 'License :: OSI Approved :: Apache Software License',
                 'Programming Language :: Python',
                 'Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.2',
                 'Intended Audience :: Developers',
                 'Environment :: Console',
                 ],

    platforms=['Any'],

    scripts=[],

    provides=[],
    install_requires=['distribute', 'cliff', 'boto', 'paramiko'],

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
            'salt = clifford.actions:Salt',
            'script_path = clifford.actions:ScriptPath',

            # Lister tools
            'ls = clifford.listing:Instances',

            'addresses = clifford.listing:Addresses',
            'buckets = clifford.listing:Buckets',
            'bundles = clifford.listing:Bundles',
            'groups = clifford.listing:Groups',
            'images = clifford.listing:Images',
            'tags = clifford.listing:InstanceTags',
            'instances = clifford.listing:Instances',
            'keys = clifford.listing:Keys',
            'python bundles = clifford.listing:PythonBundles',
            'scripts = clifford.listing:Scripts',
            'security groups = clifford.listing:SecurityGroups',
            'snapshots = clifford.listing:Snapshots',
            'volumes = clifford.listing:Volumes',

            # EC2
            'add image = clifford.actions:AddImage',
            'create image = clifford.actions:CreateImage',
            'create snapshot = clifford.actions:CreateSnapshot',
            'del image = clifford.actions:DeleteImage',
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

            'remote add-apt install = clifford.remote:AddAptInstall',
            'remote apt-get install = clifford.remote:AptGetInstall',
            'remote bundle install = clifford.remote:BundleInstall',
            'remote create user = clifford.remote:CreateUser',
            'remote pip install = clifford.remote:PipInstall',
            'remote group install = clifford.remote:GroupInstall',
            'remote ppa install = clifford.remote:PPAInstall',
            'remote script = clifford.remote:Script',
            'remote upgrade = clifford.remote:Upgrade',

            'create bundle = clifford.package:CreateBundle',
            'bundle add = clifford.package:BundleAdd',
            'bundle rm = clifford.package:BundleRemove',
            'del bundle = clifford.package:DeleteBundle',
            'show bundle = clifford.show:Bundle',

            'create group = clifford.package:CreateGroup',
            'group add = clifford.package:GroupAdd',
            'group rm = clifford.package:GroupRemove',
            'del group = clifford.package:DeleteGroup',
            'show group = clifford.show:Group',

            # Elastic IPs
            'associate = clifford.address:Associate',
            'disassociate = clifford.address:Disassociate',
            'allocate = clifford.address:Allocate',
            'release = clifford.address:Release',

            # S3
            's3 create bucket = clifford.storage:CreateBucket',
            's3 del bucket = clifford.storage:DeleteBucket',
            's3 download = clifford.storage:Download',
            's3 upload = clifford.storage:Upload',
            ],
        },

    zip_safe=False,
    )
