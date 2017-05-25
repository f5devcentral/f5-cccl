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

import copy

import f5
import f5_cccl
from f5_cccl._f5 import Policy

import pytest
from mock import MagicMock


def test_version():
    assert isinstance(f5_cccl.__version__, str)


@pytest.fixture
def cp():
    return copy.deepcopy(controller_policy)


@pytest.fixture
def mock_bigip_policy():
    mbp = MagicMock(spec=f5.bigip.tm.ltm.policy.Policy)
    mbp.__dict__.update(bigip_policy)
    return mbp


def test_policy_class_equal(mock_bigip_policy):
    bp = Policy(mock_bigip_policy)
    up = Policy(controller_policy)
    assert bp == up


def test_policy_class_policy_unequal(mock_bigip_policy, cp):
    cp['name'] = 'notequal'
    bp = Policy(mock_bigip_policy)
    up = Policy(cp)
    assert bp != up


def test_policy_class_rule_unequal(mock_bigip_policy, cp):
    cp['rules'][0]['ordinal'] = 1
    bp = Policy(mock_bigip_policy)
    up = Policy(cp)
    assert bp != up


def test_policy_class_action_unequal(mock_bigip_policy, cp):
    cp['rules'][0]['actions'][0]['pool'] = 'wrong_pool'
    bp = Policy(mock_bigip_policy)
    up = Policy(cp)
    assert bp != up


def test_policy_class_condition_unequal(mock_bigip_policy, cp):
    cp['rules'][0]['conditions'][1]['values'].append('another')
    bp = Policy(mock_bigip_policy)
    up = Policy(cp)
    assert bp != up


bigip_policy = {
    '_meta_data': {
        'allowed_commands': [],
        'allowed_lazy_attributes': [
            "< class 'f5.bigip.tm.ltm.policy.Rules_s' >",
            "< class 'f5.bigip.resource.Stats' >"],
        'attribute_registry': {
            'tm:ltm:policy:rules:rulescollectionstate':
                "< class 'f5.bigip.tm.ltm.policy.Rules_s' >"
        },
        'bigip': '<f5.bigip.ManagementRoot object at 0x10ecd5410>',
        'container': '<f5.bigip.tm.ltm.policy.Policys object at 0x10eed48d0>',
        'creation_uri_frag': '',
        'creation_uri_qargs': {
            'expandSubcollections': ['true'],
            'ver': ['12.1.0']
        },
        'exclusive_attributes': [],
        'icontrol_version': '',
        'icr_session':
            "< icontrol.session.iControlRESTSession object at 0x10ed92410 >",
        'minimum_version': '11.5.0',
        'object_has_stats': True,
        'read_only_attributes': [],
        'reduction_forcing_pairs': [('enabled', 'disabled'),
                                    ('online', 'offline'),
                                    ('vlansEnabled', 'vlansDisabled')],
        'required_command_parameters': set([]),
        'required_creation_parameters': set(['name', 'strategy']),
        'required_json_kind': 'tm:ltm:policy:policystate',
        'required_load_parameters': set(['name']),
        'uri': 'https://10.190.25.16:443/mgmt/tm/ltm/policy/~k8s~mock/'
    },
    'controls': ['forwarding'],
    'fullPath': '/k8s/mock',
    'generation': 117177,
    'kind': 'tm:ltm:policy:policystate',
    'lastModified': '2017-05-24T21:04:14Z',
    'name': 'mock',
    'partition': 'k8s',
    'references': {},
    'requires': ['http'],
    'rulesReference': {
        'isSubcollection': True,
        'items': [{
            'actionsReference': {
                'isSubcollection': True,
                'items': [{
                    'code': 0,
                  'expirySecs': 0,
                  'forward': True,
                  'fullPath': '0',
                  'generation': 117175,
                  'kind': 'tm:ltm:policy:rules:actions:actionsstate',
                  'length': 0,
                  'name': '0',
                  'offset': 0,
                  'pool': '/k8s/nginx-05c03468ced66d2c',
                  'poolReference': {
                      'link': 'https://localhost/mgmt/tm/ltm/pool/'
                  },
                  'port': 0,
                  'request': True,
                  'select': True,
                  'selfLink': 'https://localhost/mgmt/tm/ltm/policy/',
                  'status': 0,
                  'timeout': 0,
                  'vlanId': 0
                  }],
                'link': 'https://localhost/mgmt/tm/ltm/policy/'
            },
            'conditionsReference': {
                'isSubcollection': True,
                'items': [{
                    'caseInsensitive': True,
                    'equals': True,
                    'external': True,
                    'fullPath': '0',
                    'generation': 117175,
                    'host': True,
                    'httpHost': True,
                    'index': 0,
                    'kind': 'tm:ltm:policy:rules:conditions:conditionsstate',
                    'name': '0',
                    'present': True,
                    'remote': True,
                    'request': True,
                    'selfLink': 'https://localhost/mgmt/tm/ltm/policy/',
                    'values': ['nginx.local.pcfdev.io']
                }, {
                    'caseInsensitive': True,
                    'equals': True,
                    'external': True,
                    'fullPath': '1',
                    'generation': 117175,
                    'httpUri': True,
                    'index': 1,
                    'kind': 'tm:ltm:policy:rules:conditions:conditionsstate',
                    'name': '1',
                    'pathSegment': True,
                    'present': True,
                    'remote': True,
                    'request': True,
                    'selfLink': 'https://localhost/mgmt/tm/ltm/policy/',
                    'values': ['foo']
                }],
                'link': 'https://localhost/mgmt/tm/ltm/policy/'
            },
            'fullPath': 'nginx-foo',
            'generation': 117176,
            'kind': 'tm:ltm:policy:rules:rulesstate',
            'name': 'nginx-foo',
            'ordinal': 0,
            'selfLink': 'https://localhost/mgmt/tm/ltm/policy/'
        }],
        'link': 'https://localhost/mgmt/tm/ltm/policy/'
    },
    'selfLink': 'https://localhost/mgmt/tm/ltm/policy/',
    'status': 'published',
    'strategy': '/Common/first-match',
    'strategyReference': {
        'link': 'https://localhost/mgmt/tm/ltm/policy-strategy/'
    }
}

controller_policy = {
    'name': 'mock',
    'partition': 'k8s',
    'controls': ['forwarding'],
    'strategy': '/Common/first-match',
    'legacy': True,
    'requires': ['http'],
    'rules': [{
        'ordinal': 0,
        'conditions': [{
            'index': 0,
            'name': '0',
            'request': True,
            'equals': True,
            'host': True,
            'values': ['nginx.local.pcfdev.io'],
            'httpHost': True
        }, {
            'index': 1,
            'name': '1',
            'httpUri': True,
            'request': True,
            'equals': True,
            'pathSegment': True,
            'values': ['foo']
        }],
        'name': 'nginx-foo',
        'actions': [{
            'forward': True,
            'request': True,
            'name': '0',
            'pool': '/k8s/nginx-05c03468ced66d2c'
        }]
    }]
}
