#!/usr/bin/env python
# Copyright 2017 F5 Networks Inc.
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


from f5_cccl.utils.resource_merge import merge

#
# CCCL merge takes it's required resource properties and
# merges it into the Big-IP existing properties.  If there
# is a conflict, the CCCL properties win.  Also, for lists
# CCCL entries are listed first.
#

def test_resource_merge_scalars():
    """ Test simple scalar merging (replacing) """

    test_data = [
        # desired, existing, merged
        (4, 3, 4),
        ('a', 'b', 'a'),
        (True, False, True)
    ]
    for test in test_data:
        desired = test[0]
        existing = test[1]
        expected = test[2]
        assert merge(existing, desired) == expected


def test_resource_merge_simple_arrays():
    """ Test simple list merging (replacing) """

    test_data = [
        # desired, existing, merged
        ([], [], []),
        ([], [1], [1]),
        ([1], [], [1]),
        ([1], [2], [1, 2]),
        ([2], [1], [2, 1]),
        ([1, 2], [1], [1, 2]),
        ([1], [1, 2], [1, 2]),
        ([1, 3], [1, 2], [1, 3, 2]),
        (['apple', 'orange'], ['apple', 'pear'], ['apple', 'orange', 'pear'])
    ]
    for test in test_data:
        desired = test[0]
        existing = test[1]
        expected = test[2]
        assert merge(existing, desired) == expected


def test_resource_merge_simple_dict():
    """ Test simple dictionary merging """

    test_data = [
        # desired, existing, merged
        ({}, {'a': 1}, {'a': 1}),
        ({'a': 1}, {}, {'a': 1}),
        ({'a': 1}, {'a': 2}, {'a': 1}),
        ({'a': 1}, {'b': 2}, {'a': 1, 'b': 2}),
        ({'a': 1, 'b': 3}, {'b': 2}, {'a': 1, 'b': 3}),
        ({'a': 1, 'b': 2}, {'c': 3, 'd': 4}, {'a': 1, 'b': 2, 'c': 3, 'd': 4})
    ]
    for test in test_data:
        desired = test[0]
        existing = test[1]
        expected = test[2]
        assert merge(existing, desired) == expected


def test_resource_merge_list_of_named_dict():
    """ Test merge lists of named dictionary objects

        This is unique for Big-IP resources that are
        lists of named objects (the resources must have
        a unique property 'name').
    """

    test_data = [
        # desired, existing, merged
        (
            [],
            [],
            []
        ),
        (
            [],
            [{'name': 'resource-a', 'value': 1}],
            [{'name': 'resource-a', 'value': 1}]
        ),
        (
            [{'name': 'resource-a', 'value': 1}],
            [],
            [{'name': 'resource-a', 'value': 1}]),
        (
            [{'name': 'resource-a', 'value': 1}],
            [{'name': 'resource-a', 'value': 3}],
            [{'name': 'resource-a', 'value': 1}]
        ),
        (
            [{'name': 'resource-a', 'value1': 1, 'value2': 2}],
            [{'name': 'resource-a', 'value2': 0, 'value3': 3}],
            [{'name': 'resource-a', 'value1': 1, 'value2': 2}]
        ),
        (
            [
                {'name': 'resource-a', 'value1': 1, 'value2': 2},
                {'name': 'resource-b', 'valueB': 'b'}
            ],
            [
                {'name': 'resource-a', 'value2': 0, 'value3': 3},
                {'name': 'resource-c', 'valueC': 'c'},
                {'name': 'resource-b', 'valueB': 'b'}
            ],
            [
                {'name': 'resource-a', 'value1': 1, 'value2': 2},
                {'name': 'resource-b', 'valueB': 'b'},
                {'name': 'resource-c', 'valueC': 'c'}
            ]
        )
    ]
    for test in test_data:
        desired = test[0]
        existing = test[1]
        expected = test[2]
        assert merge(existing, desired) == expected


def test_resource_merge_sample_resource():
    """ Test actual Big-IP resource """

    desired = {
        'destination': '/test/172.16.3.59%0:80',
        'name': 'ingress_172-16-3-59_80',
        'rules': [],
        'vlansDisabled': True,
        'enabled': True,
        'sourceAddressTranslation': {'type': 'automap'},
        'partition': 'test',
        'source': '0.0.0.0%0/0',
        'profiles': [
            {'partition': 'Common', 'name': 'http', 'context': 'all'},
            {'partition': 'Common', 'name': 'tcp', 'context': 'all'}
        ],
        'connectionLimit': 0,
        'ipProtocol': 'tcp',
        'vlans': [],
        'policies': [
            {'partition': 'test', 'name': 'ingress_172-16-3-59_80'}
        ]
    }

    existing = {
        'destination': '/test/172.16.3.59%0:80',
        'name': 'ingress_172-16-3-59_80',
        'rules': [],
        'vlansDisabled': False,  # should change
        'enabled': True,
        'sourceAddressTranslation': {'type': 'snat'},  # should change
        'partition': 'test',
        'source': '0.0.0.0%0/0',
        'profiles': [
            # html profile should be kept, but added after CCCL entries
            {'partition': 'Common', 'name': 'html', 'context': 'all'},
            {'partition': 'Common', 'name': 'http', 'context': 'all'},
            {'partition': 'Common', 'name': 'tcp', 'context': 'all'}
        ],
        'connectionLimit': 1,  # should change
        'ipProtocol': 'tcp',
        'vlans': [
            {'name': 'vlan', 'a': '1', 'b': '2'}  # should be kept
        ],
        'policies': []  # will be added to
    }

    expected = {
        'destination': '/test/172.16.3.59%0:80',
        'name': 'ingress_172-16-3-59_80',
        'rules': [],
        'vlansDisabled': True,
        'enabled': True,
        'sourceAddressTranslation': {'type': 'automap'},
        'partition': 'test',
        'source': '0.0.0.0%0/0',
        'profiles': [
            {'partition': 'Common', 'name': 'http', 'context': 'all'},
            {'partition': 'Common', 'name': 'tcp', 'context': 'all'},
            {'partition': 'Common', 'name': 'html', 'context': 'all'}
        ],
        'connectionLimit': 0,
        'ipProtocol': 'tcp',
        'vlans': [
            {'name': 'vlan', 'a': '1', 'b': '2'}
        ],
        'policies': [
            {'partition': 'test', 'name': 'ingress_172-16-3-59_80'}
        ]
    }

    assert merge(existing, desired) == expected
