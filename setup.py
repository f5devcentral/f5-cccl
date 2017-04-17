#!/usr/bin/env python

# Copyright 2014 F5 Networks Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import f5_cccl

from setuptools import find_packages
from setuptools import setup

install_requires = []
print('install_requires', install_requires)
setup(
    name='f5-cccl',
    description='F5 Networks Common Controller Core Library',
    license='Apache License, Version 2.0',
    version=f5_cccl.__version__,
    author='F5 Networks',
    url='https://github.com/f5devcentral/f5-cccl',
    keywords=['F5', 'big-ip'],
    install_requires=install_requires,
    packages=find_packages(
        exclude=["*.test", "*.test.*", "test.*", "test_*", "test", "test*"]
    ),
    data_files=[],
    classifiers=[
    ],
    entry_points={}
)
