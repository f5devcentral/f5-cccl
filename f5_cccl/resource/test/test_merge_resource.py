#!/usr/bin/env python
# Copyright (c) 2017,2018, F5 Networks, Inc.
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


import copy
import logging

from f5_cccl.resource import Resource

# allow logging to show up if test fails
logging.basicConfig(level=logging.INFO)


# Input data to simulate static Big-IP config with CCCL requested additions
# and the resulting Big-IP 'merged' config.
# Note: To reduce redundancy, if the expected merged result is the same as the
#       initial Big-IP config, the mergedBigipProperties field is set to None.
# Note2: If the mergedBigipProperties is what we want feed into the next
#        'update', then the changedBigipProperties does not have to be listed.

LTM_RESOURCE_TEST_DATA = [
    # test top-level properties that are composed of simple dictionary entries
    {
        'name': 'CCCL no change no Bigip dict properties',
        'initialBigipProperties': {},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {},
                'updateRequired': False,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'CCCL Add dict property, no BigIp dict property',
        'initialBigipProperties': {},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {'c': 3},
                'updateRequired': True,
                'mergedBigipProperties': {'c': 3}
            },
            {
                'requestedCcclProperties': {'c': 3},
                'updateRequired': False,
                'mergedBigipProperties': {'c': 3}
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': True,
                'mergedBigipProperties': None
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': False,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'CCCL no change dict property',
        'initialBigipProperties': {'a': 1, 'b': 2},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {},
                'updateRequired': False,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'CCCL Add dict property',
        'initialBigipProperties': {'a': 1, 'b': 2},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {'c': 3},
                'updateRequired': True,
                'mergedBigipProperties': {'a': 1, 'b': 2, 'c': 3}
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': True,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'Modify CCCL Add dict property',
        'initialBigipProperties': {'a': 1, 'b': 2},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {'c': 3},
                'updateRequired': True,
                'mergedBigipProperties': {'a': 1, 'b': 2, 'c': 3}
            },
            {
                'requestedCcclProperties': {'c': 4},
                'updateRequired': True,
                'mergedBigipProperties': {'a': 1, 'b': 2, 'c': 4}
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': True,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'Replace CCCL Add dict property',
        'initialBigipProperties': {'a': 1, 'b': 2},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {'c': 3},
                'updateRequired': True,
                'mergedBigipProperties': {'a': 1, 'b': 2, 'c': 3}
            },
            {
                'requestedCcclProperties': {'d': 4},
                'updateRequired': True,
                'mergedBigipProperties': {'a': 1, 'b': 2, 'd': 4}
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': True,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'Bigip dynamic changes to dict property',
        'initialBigipProperties': {},
        'ltmUpdates': [
            {  # Start with CCCL properties only
                'requestedCcclProperties': {'b': 2, 'c': 3},
                'updateRequired': True,
                'mergedBigipProperties': {'b': 2, 'c': 3}
            },
            {  # Bigip adds a property 'a', we don't care
                'changedBigipProperties': {'a': 1, 'b': 2, 'c': 3},
                'requestedCcclProperties': {'b': 2, 'c': 3},
                'updateRequired': False,
                'mergedBigipProperties': {'b': 2, 'c': 3, 'a': 1}
            },
            { # Bigip tries to remove CCCL properties, we do care!
                'changedBigipProperties': {'a': 1, 'c': 3},
                'requestedCcclProperties': {'b': 2, 'c': 3},
                'updateRequired': True,
                'mergedBigipProperties': {'b': 2, 'c': 3, 'a': 1}
            },
            { # Bigip properties are removed, no matter the order
                'changedBigipProperties': {'c': 3, 'b': 2},
                'requestedCcclProperties': {'b': 2, 'c': 3},
                'updateRequired': False,
                'mergedBigipProperties': {'b': 2, 'c': 3}
            },
            { # Bigip modifies CCCL properties, must fix
                'changedBigipProperties': {'b': 2, 'c': 4},
                'requestedCcclProperties': {'b': 2, 'c': 3},
                'updateRequired': True,
                'mergedBigipProperties': {'b': 2, 'c': 3}
            },
            { # CCCL properties are removed
                'changedBigipProperties': {'b': 2},
                'requestedCcclProperties': {},
                'updateRequired': True,
                'mergedBigipProperties': None
            }
        ]
    },
    # test top-level property that is itself a list
    # (note1: there is no such thing as 'replace' for simply lists)
    # (note2: CCCL additions are always added to the front of the merged list)
    {
        'name': 'CCCL add empty list property, no BigIp property',
        'initialBigipProperties': {},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {'c': []},
                'updateRequired': True,
                'mergedBigipProperties': {'c': []}
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': True,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'CCCL add one list property, no BigIp property',
        'initialBigipProperties': {},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {'c': ['firstProp']},
                'updateRequired': True,
                'mergedBigipProperties': {'c': ['firstProp']}
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': True,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'CCCL add multi-entry list property, no BigIp property',
        'initialBigipProperties': {},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {'c': [1, 2]},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [1, 2]}
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': True,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'CCCL no list property, empty list BigIp property',
        'initialBigipProperties': {'c': []},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {},
                'updateRequired': False,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'CCCL no list property, multi-entry list BigIp property',
        'initialBigipProperties': {'c': [1, 2]},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {},
                'updateRequired': False,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'CCCL add dup list property, multi-entry list BigIp property',
        'initialBigipProperties': {'c': [1, 2]},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {'c': [1]},
                'updateRequired': False,
                'mergedBigipProperties': {'c': [1, 2]}
            },
            {
                'requestedCcclProperties': {'c': [2]},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [2, 1]}
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': True,
                'mergedBigipProperties': None
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': False,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'CCCL add list property, non-existent list BigIp property',
        'initialBigipProperties': {},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {'c': [3]},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [3]}
            },
            {
                'requestedCcclProperties': {'c': [4]},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [4]}
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': True,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'CCCL add list property, empty list BigIp property',
        'initialBigipProperties': {'c': []},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {'c': [3]},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [3]}
            },
            {
                'requestedCcclProperties': {'c': [4]},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [4]}
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': True,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'CCCL add unique list property, multi-entry list BigIp prop',
        'initialBigipProperties': {'c': [1, 2]},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {'c': [3]},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [3, 1, 2]}
            },
            {
                'requestedCcclProperties': {'c': [4]},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [4, 1, 2]}
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': True,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'Bigip dynamic changes to list property',
        'initialBigipProperties': {'c': [1, 2]},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {'c': [3, 4]},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [3, 4, 1, 2]}
            },
            {
                'requestedCcclProperties': {'c': [3, 4]},
                'updateRequired': False,
                'mergedBigipProperties': {'c': [3, 4, 1, 2]}
            },
            {
                'changedBigipProperties': {'c': [3, 4, 2]},
                'requestedCcclProperties': {'c': [3, 4]},
                'updateRequired': False,
                'mergedBigipProperties': {'c': [3, 4, 2]}
            },
            {
                'changedBigipProperties': {'c': [3, 4, 2]},
                'requestedCcclProperties': {'c': [3, 4]},
                'updateRequired': False,
                'mergedBigipProperties': {'c': [3, 4, 2]}
            },
            {
                'changedBigipProperties': {'c': [2, 3, 4]},
                'requestedCcclProperties': {'c': [3, 4]},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [3, 4, 2]}
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [2]}
            }
        ]
    },
    # This following test fails for jsonpatch versions 1.20-1.23.
    # It only works for version 1.16 and that behavior is required
    # for proper merging of Big-IP objects.
    {
        'name': 'Bigip dynamic large changes to list property',
        'initialBigipProperties': {'c': [2, 4, 6, 8]},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {'c': [1, 3, 5, 7]},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [1, 3, 5, 7, 2, 4, 6, 8]}
            },
            {
                'changedBigipProperties': {'c': [3, 7, 4, 8]},
                'requestedCcclProperties': {'c': [1, 3, 5]},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [1, 3, 5, 4, 8]}
            },
            {
                'changedBigipProperties': {'c': [1, 2, 3, 4, 5, 8]},
                'requestedCcclProperties': {'c': []},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [2, 4, 8]}
            }
        ],
    },
    # test top-level list properties that are dictionaries themselves
    # (note1: this takes into account specific Big-IP behavior in that
    #         these dictionaries can be uniquely identified by a 'name'
    #         attribute.  Therefore, we can perform a 'replace' or 'modify'
    #         of the individual list entries.)
    # (note2: CCCL additions are always added to the front of the merged list)
    {
        'name': 'CCCL add dict list property, no BigIp property',
        'initialBigipProperties': {},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {'c': [{'name': 'a', 'value': 1}]},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [{'name': 'a', 'value': 1}]}
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': True,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'CCCL add dict list property, existing BigIp property',
        'initialBigipProperties': {'c': [{'name': 'b', 'value': 0}]},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {'c': [{'name': 'a', 'value': 1}]},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [{'name': 'a', 'value': 1},
                                                {'name': 'b', 'value': 0}]}
            },
            {
                'requestedCcclProperties': {'c': [{'name': 'c', 'value': 2}]},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [{'name': 'c', 'value': 2},
                                                {'name': 'b', 'value': 0}]}
            },
            {
                'requestedCcclProperties': {'c': [{'name': 'c', 'value': 2}]},
                'updateRequired': False,
                'mergedBigipProperties': {'c': [{'name': 'c', 'value': 2},
                                                {'name': 'b', 'value': 0}]}
            },
            {
                'requestedCcclProperties': {'c': [{'name': 'c', 'value': 2},
                                                  {'name': 'd', 'value': 3}]},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [{'name': 'c', 'value': 2},
                                                {'name': 'd', 'value': 3},
                                                {'name': 'b', 'value': 0}]}
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': True,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'CCCL modify dict list property of BigIp property',
        'initialBigipProperties': {'c': [{'name': 'b', 'value': 0}]},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {'c': [{'name': 'b', 'value': 1}]},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [{'name': 'b', 'value': 1}]}
            },
            {
                'requestedCcclProperties': {'c': [{'name': 'b', 'value2': 2}]},
                'updateRequired': True,
                'mergedBigipProperties': {'c': [{'name': 'b', 'value2': 2}]}
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': True,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'CCCL modify complex dict list property of BigIp property',
        'initialBigipProperties': {'c': [{'name': 'b', 'val': 0, 'val2': 1},
                                         {'name': 'd', 'val': 2, 'val3': 3}]},
        'ltmUpdates': [
            {
                'requestedCcclProperties': {
                    'a': [0, 1, 2],
                    'b': "just text",
                    'c': [{'name': 'b', 'val': 0, 'val2': 1},
                          {'name': 'c', 'val': 1, 'val3': 3},
                          {'name': '0', 'val': 9, 'val3': 9}]
                },
                'updateRequired': True,
                'mergedBigipProperties': {
                    'a': [0, 1, 2],
                    'b': "just text",
                    'c': [{'name': 'b', 'val': 0, 'val2': 1},
                          {'name': 'c', 'val': 1, 'val3': 3},
                          {'name': '0', 'val': 9, 'val3': 9},
                          {'name': 'd', 'val': 2, 'val3': 3}]
                },
            },
            {
                'requestedCcclProperties': {
                    'a': [0, 1, 2],
                    'b': "just text",
                    'c': [{'name': 'b', 'val': 0, 'val2': 1},
                          {'name': 'c', 'val': 1, 'val3': 3},
                          {'name': '0', 'val': 9, 'val3': 9}]
                },
                'updateRequired': False,
                'mergedBigipProperties': {
                    'a': [0, 1, 2],
                    'b': "just text",
                    'c': [{'name': 'b', 'val': 0, 'val2': 1},
                          {'name': 'c', 'val': 1, 'val3': 3},
                          {'name': '0', 'val': 9, 'val3': 9},
                          {'name': 'd', 'val': 2, 'val3': 3}]
                },
            },
            {
                'requestedCcclProperties': {
                    'c': [{'name': 'b', 'val1': 0, 'val2': 0}]
                },
                'updateRequired': True,
                'mergedBigipProperties': {
                    'c': [{'name': 'b', 'val1': 0, 'val2': 0},
                          {'name': 'd', 'val': 2, 'val3': 3}]
                },
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': True,
                'mergedBigipProperties': None
            }
        ]
    },
    {
        'name': 'CCCL real Big-IP example',
        'initialBigipProperties': {
            'connectionLimit': 0,
            'ipProtocol': 'tcp',
            'destination': '/test/172.16.3.60%0:443',
            'sourceAddressTranslation': {
                'type': 'none'
            },
            'rules': [
                '/common/custom_irule'
            ],
            'profiles': [
                {
                    'partition': 'Common',
                    'name': 'tcp',
                    'context': 'all'
                },
                {
                    'partition': 'Common',
                    'name': 'http',
                    'context': 'all'
                },
                {
                    'partition': 'Common',
                    'name': 'html',
                    'context': 'all'
                }
            ]
        },
        'ltmUpdates': [
            {
                'requestedCcclProperties': {
                    'connectionLimit': 0,
                    'ipProtocol': 'tcp',
                    'destination': '/test/172.16.3.60%0:443',
                    'sourceAddressTranslation': {
                        'type': 'automap'
                    },
                    'rules': [
                        '/test/openshift_passhtrough_irule'
                    ],
                    'profiles': [
                        {
                            'partition': 'Common',
                            'name': 'tcp',
                            'context': 'all'
                        },
                        {
                            'partition': 'Common',
                            'name': 'http',
                            'context': 'all'
                        }
                    ]
                },
                'updateRequired': True,
                'mergedBigipProperties': {
                    'connectionLimit': 0,
                    'ipProtocol': 'tcp',
                    'destination': '/test/172.16.3.60%0:443',
                    'sourceAddressTranslation': {
                        'type': 'automap'
                    },
                    'rules': [
                        '/test/openshift_passhtrough_irule',
                        '/common/custom_irule'
                    ],
                    'profiles': [
                        {
                            'partition': 'Common',
                            'name': 'tcp',
                            'context': 'all'
                        },
                        {
                            'partition': 'Common',
                            'name': 'http',
                            'context': 'all'
                        },
                        {
                            'partition': 'Common',
                            'name': 'html',
                            'context': 'all'
                        }
                    ]
                }
            },
            {
                'requestedCcclProperties': {},
                'updateRequired': True,
                'mergedBigipProperties': None
            }
        ]
    }
]


class GenericResource(Resource):
    """Mock resource"""

    def __init__(self, properties):
        super(GenericResource, self).__init__("testResource",
                                              "testPartition",
                                              **properties)

        for key, value in properties.items():
            self._data[key] = value

    def scrub_data(self, include_metadata = False):
        """Remove programmatically added properties"""
        data = copy.deepcopy(self._data)
        if include_metadata:
            del data['metadata']
        del data['name']
        del data['partition']
        return data

    def replace_data(self, data):
        """Remove programmatically added properties"""
        metadata = self._data['metadata']
        name = self._data['name']
        partition = self._data['partition']
        self._data = copy.deepcopy(data)
        self._data['metadata'] = metadata
        self._data['name'] = name
        self._data['partition'] = partition


def _add_whitelist_metadata(orig_data):
    """Turn this resource into a whitelisted resource"""

    data = copy.deepcopy(orig_data)
    data['metadata'] = [
        {
            'name': 'cccl-whitelist',
            'app-service': 'none',
            'persist': True,
            'value': 1
        }
    ]
    return data


def test_merge_cccl_resource_properties():
    """Test merge and revert when CCCL resource is added, modified, removed"""
    for test in LTM_RESOURCE_TEST_DATA:
        initial_properties = \
            _add_whitelist_metadata(test['initialBigipProperties'])
        current_bigip_resource = GenericResource(initial_properties)

        # cycle through each update request and verify proper merge
        # (the Big-IP current state is the final state of the previous update)
        for ltm_update in test['ltmUpdates']:
            print("Running test '{}'".format(test['name']))
            if 'changedBigipProperties' in ltm_update:
                # Simulates BigIP changing on the fly
                current_bigip_resource.replace_data(
                    ltm_update['changedBigipProperties'])
            update_required = current_bigip_resource.merge(
                ltm_update['requestedCcclProperties'])
            assert ltm_update['updateRequired'] == update_required, \
                    "Failed test: {}".format(test['name'])
            # assume the initial BigIP properties if we don't specify them
            expected_bigip_resource = ltm_update['mergedBigipProperties'] \
                if ltm_update['mergedBigipProperties'] \
                else test['initialBigipProperties']
            assert expected_bigip_resource == \
                   current_bigip_resource.scrub_data(include_metadata=True), \
                   "Failed test: {}".format(test['name'])

            # Prepare next pass to simulate retrieval from Big-IP
            current_data = copy.deepcopy(current_bigip_resource.scrub_data())
            current_bigip_resource = GenericResource(current_data)
