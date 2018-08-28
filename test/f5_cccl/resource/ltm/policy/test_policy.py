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

from copy import deepcopy
from pprint import pprint as pp
import pytest
import requests
import pdb

from mock import Mock
from mock import MagicMock

from f5.bigip import ManagementRoot

from f5.sdk_exception import F5SDKError
from icontrol.exceptions import iControlUnexpectedHTTPError

import f5_cccl.exceptions as exceptions
from f5_cccl.resource.ltm.policy import Policy, IcrPolicy
from f5_cccl.resource.ltm.policy import Rule
from f5_cccl.resource.ltm.policy import Action
from f5_cccl.resource.ltm.policy import Condition


requests.packages.urllib3.disable_warnings()

actions = {
    'redirect': {
	"request": True,
	"redirect": True,
	"location": "http://boulder-dev.f5.com",
	"httpReply": True
    },
    'redirect_http_https': {
	"request": True,
	"redirect": True,
	"location": "tcl:https://[getfield [HTTP::host] : 1][HTTP::uri]",
	"httpReply": True
    },
    'pool_forward': {
	"request": True,
	"forward": True,
	"pool": "/Test1/pool1"
    },
    'reset': {
	"request": True,
	"forward": True,
	"reset": True
    },
    'invalid_action': {
        "request": False,
        "forward": False,
        "pool": None,
        "location": None,
        "reset": False,
        "redirect": False
    }
}

conditions = {
    'http_host': {
        'httpHost': True,
        'host': True,
        'equals': True,
        'values': ["www.my-site.com", "www.your-site.com"],
    },
    'http_uri_path': {
        'httpUri': True,
        'path': True,
        'not': True,
        'equals': True,
        'values': ["/", "/home.htm"]
    },
    'http_uri_path_segment': {
        'httpUri': True,
        'pathSegment': True,
        'startsWith': True,
        'index': 1,
        'values': ["articles"],
    },
    'http_uri_extension': {
        'httpUri': True,
        'extension': True,
        'startsWith': True,
        'values': ["htm"]
    },
    'http_uri_unsupported': {
        'httpUri': True,
        'queryString': True,
        'equals': True,
        'values': ["expandSubcollections=true"]
    },
    'http_unsupported_operand_type': {
        'httpMethod': True,
        'equals': True,
        'values': ["GET"]
    },
    'http_cookie': {
        'httpCookie': True,
        'tmName': "Cookie",
        'contains': True,
        'values': ["sessionToken=abc123"]
    },
    'http_header': {
        'httpHeader': True,
        'tmName': "Host",
        'contains': True,
        'values': ["www.acme.com"]
    },
    'tcp_address': {
        'tcp': True,
        'address': True,
        'matches': True,
        'values': ['1.1.1.1/32', '2.2.2.0/24']
    }
}


class TestPolicy(object):

    name = "test_policy"

    def _get_policy_from_bigip(self, bigip, partition):
        try:
            icr_policy = bigip.tm.ltm.policys.policy.load(
                name=self.name, partition=partition,
                requests_params={'params': "expandSubcollections=true"})
            code = 200
        except iControlUnexpectedHTTPError as err:
            icr_policy = None
            code = err.response.status_code

        return (icr_policy, code)

    def test_create_policy_no_rules(self, bigip, partition):
        """Create a simple policy with no rules."""
        if isinstance(bigip, MagicMock):
            return

        test_policy = {
            'name': self.name,
            'strategy': "/Common/first-match",
            'rules': []
        }

        policy = Policy(partition=partition, **test_policy)

        try:
            policy.create(bigip)
        except exceptions.F5CcclError as e:
            print(e)

        (icr_policy, code) = self._get_policy_from_bigip(bigip, partition)

        assert icr_policy
        assert icr_policy.raw['name'] == self.name
        assert icr_policy.raw['strategy'] == "/Common/first-match"
        assert 'items' not in icr_policy.raw['rulesReference']
        # assert icr_policy.raw['status'] == "legacy"

        try:
            policy.delete(bigip)
        except exceptions.F5CcclError as e:
            print(e)

    def test_create_policy_one_rule(self, bigip, partition):
        """Create a simple policy with one rule."""
        if isinstance(bigip, MagicMock):
            return

        test_rule = {
            'name': "rule_0",
            'actions': [],
            'conditions': []
        }
        test_policy = {
            'name': self.name,
            'strategy': "/Common/first-match",
            'rules': []
        }
        test_policy['rules'].append(test_rule)

        # Create the policy resource.
        policy = Policy(partition=partition, **test_policy)

        try:
            # Create on bigip.
            policy.create(bigip)
        except exceptions.F5CcclError as e:
            print(e)

        # Get the policy from the bigip.
        (icr_policy, code) = self._get_policy_from_bigip(bigip, partition)

        # Assert object exists and test attributes.
        assert icr_policy
        assert icr_policy.raw['name'] == self.name
        assert icr_policy.raw['strategy'] == "/Common/first-match"

        assert 'items' in icr_policy.raw['rulesReference']
        rules = icr_policy.raw['rulesReference']['items']
        assert len(rules) == 1

        rule = rules[0]
        assert rule['name'] == "rule_0"
        assert rule['ordinal'] == 0

        assert policy == IcrPolicy(**icr_policy.raw)

        # Cleanup
        try:
            policy.delete(bigip)
        except exceptions.F5CcclError as e:
            print(e)

    def test_update_policy_one_rule(self, bigip, partition):
        if isinstance(bigip, MagicMock):
            return

        # Create a new policy
        policy_data = {
            'name': self.name,
            'strategy': "/Common/first-match",
            'rules': []
        }
        policy = Policy(partition=partition, **policy_data)

        try:
            policy.create(bigip)
        except exceptions.F5CcclError as e:
            print(e)

        # Retrieve it from the BIG-IP
        (icr_policy, code) = self._get_policy_from_bigip(bigip, partition)
        assert code == 200

        # Assert the attributes of the retrieved policy
        assert icr_policy
        assert icr_policy.raw['name'] == self.name
        assert icr_policy.raw['strategy'] == "/Common/first-match"
        assert 'items' not in icr_policy.raw['rulesReference']

        # Update the policy strategy
        new_policy_data = {
            'name': self.name,
            'strategy': "/Common/best-match",
            'rules': []
        }
        policy = Policy(partition=partition, **new_policy_data)
        try:
            policy.update(bigip)
        except exceptions.F5CcclError as e:
            print(e)

        # Retrieve it from the BIG-IP
        (icr_policy, code) = self._get_policy_from_bigip(bigip, partition)
        assert code == 200

        # Assert strategy changed
        assert icr_policy
        assert icr_policy.raw['strategy'] == "/Common/best-match"

        # Add a rule to the policy, and update
        test_rule = {
            'name': "rule_0",
            'actions': [],
            'conditions': []
        }
        new_policy_data['rules'].append(test_rule)
        policy = Policy(partition=partition, **new_policy_data)
        try:
            policy.update(bigip)
        except exceptions.F5CcclError as e:
            print(e)

        # Retrieve it from the BIG-IP
        (icr_policy, code) = self._get_policy_from_bigip(bigip, partition)
        assert code == 200

        # Assert rule added
        assert icr_policy
        assert 'items' in icr_policy.raw['rulesReference']
        rules = icr_policy.raw['rulesReference']['items']

        assert len(rules) == 1
        rule = rules[0]
        assert rule['name'] == "rule_0"

        # Remove the rule.
        new_policy_data['rules'].pop()
        policy = Policy(partition=partition, **new_policy_data)
        try:
            policy.update(bigip)
        except exceptions.F5CcclError as e:
            print(e)

        # Retrieve it from the BIG-IP
        (icr_policy, code) = self._get_policy_from_bigip(bigip, partition)
        assert code == 200

        # Assert rule removed
        assert icr_policy
        assert 'items' not in icr_policy.raw['rulesReference']

        # cleanup
        try:
            policy.delete(bigip)
        except exceptions.F5CcclError as e:
            print(e)

    def test_create_policy_rules(self, bigip, partition):
        if isinstance(bigip, MagicMock):
            return

        # Create a new policy
        policy_data = {
            'name': self.name,
            'strategy': "/Common/first-match",
            'rules': []
        }
        policy = Policy(partition=partition, **policy_data)

        try:
            policy.create(bigip)
        except exceptions.F5CcclError as e:
            print(e)

        (icr_policy, code) = self._get_policy_from_bigip(bigip, partition)
        assert icr_policy

        for i in range(5):
            test_rule = {
                'actions': [],
                'conditions': []
            }
            test_rule['name'] = "rule_{}".format(i)

            policy_data['rules'].append(test_rule)

            policy = Policy(partition=partition, **policy_data)

            try:
                policy.update(bigip)
            except exceptions.F5CcclError as e:
                print(e)

            (icr_policy, code) = self._get_policy_from_bigip(bigip, partition)
            assert icr_policy

            assert 'items' in icr_policy.raw['rulesReference']
            rules = icr_policy.raw['rulesReference']['items']
            assert len(rules) == i+1

        # Assert that the policy is equal to the one on the bigip.
        assert policy == IcrPolicy(**icr_policy.raw)

        # Reverse the list of rules and assert that the ordinals change.
        policy_data['rules'].reverse()
        policy = Policy(partition=partition, **policy_data)
        try:
            policy.update(bigip)
        except exceptions.F5CcclError as e:
            print(e)

        (icr_policy, code) = self._get_policy_from_bigip(bigip, partition)
        assert icr_policy

        assert 'items' in icr_policy.raw['rulesReference']
        rules = icr_policy.raw['rulesReference']['items']
        for rule in rules:
            ordinal = rule['ordinal']
            assert rule['name'] == "rule_{}".format(4-ordinal)

        # Assert that the policy is equal to the one on the bigip.
        assert policy == IcrPolicy(**icr_policy.raw)

        policy_data = {
            'name': self.name,
            'strategy': "/Common/first-match",
            'rules': []
        }
        policy = Policy(partition=partition, **policy_data)

        try:
            policy.update(bigip)
        except exceptions.F5CcclError as e:
            print(e)

        (icr_policy, code) = self._get_policy_from_bigip(bigip, partition)
        assert icr_policy
        assert 'items' not in icr_policy.raw['rulesReference']

        try:
            policy.delete(bigip)
        except exceptions.F5CcclError as e:
            print(e)

    def test_create_policy_rule_conditions(self, bigip, partition):
        """Create a policy with a rule and conditions."""
        if isinstance(bigip, MagicMock):
            return

        policy_data = {
            'name': self.name,
            'strategy': "/Common/first-match",
            'rules': [
                {
                    'name': "test_rule0",
                    'actions': [],
                    'conditions': []
                }
            ]
        }
        rule_0 = policy_data['rules'][0]
        rule_0['conditions'].append(conditions['http_host'])

        policy = Policy(partition=partition, **policy_data)

        try:
            policy.create(bigip)
        except exceptions.F5CcclError as e:
            print(e)

        (icr_policy, code) = self._get_policy_from_bigip(bigip, partition)
        assert icr_policy
        assert policy == IcrPolicy(**icr_policy.raw)

        # Add a condition
        condition = conditions['http_host']
        rule_0['conditions'].append(conditions['http_host'])
        policy = Policy(partition=partition, **policy_data)

        try:
            policy.update(bigip)
        except exceptions.F5CcclError as e:
            print(e)

        (icr_policy, code) = self._get_policy_from_bigip(bigip, partition)
        assert icr_policy
        assert policy == IcrPolicy(**icr_policy.raw)

        # Remove both conditions
        rule_0['conditions'] = list()
        policy = Policy(partition=partition, **policy_data)

        try:
            policy.update(bigip)
        except exceptions.F5CcclError as e:
            print(e)

        (icr_policy, code) = self._get_policy_from_bigip(bigip, partition)
        assert icr_policy
        assert policy == IcrPolicy(**icr_policy.raw)

        # Modify the condition and check that they are different
        new_condition = deepcopy(conditions['http_host'])

        # Change the matcher.
        new_condition.pop('equals')
        new_condition['contains'] = True
        rule_0['conditions'] = [new_condition]

        policy = Policy(partition=partition, **policy_data)

        # Test that the conditions are not equal.
        assert policy != IcrPolicy(**icr_policy.raw)

        # Update and check that they are equal
        try:
            policy.update(bigip)
        except exceptions.F5CcclError as e:
            print(e)

        (icr_policy, code) = self._get_policy_from_bigip(bigip, partition)
        assert icr_policy
        assert policy == IcrPolicy(**icr_policy.raw)

        # Delete the policy
        try:
            policy.delete(bigip)
        except exceptions.F5CcclError as e:
            print(e)

    def test_create_policy_supported_conditions(self, bigip, partition):
        """Create a policy with supported conditions"""
        if isinstance(bigip, MagicMock):
            return

        policy_data = {
            'name': self.name,
            'strategy': "/Common/first-match",
            'rules': [
                {
                    'name': "test_rule0",
                    'actions': [],
                    'conditions': []
                }
            ]
        }
        rule = policy_data['rules'][0]

        skip_conditions = ["http_uri_unsupported", "http_unsupported_operand_type"]
        # For each supported condition create, test, and delete.
        for condition in conditions:
            if condition in skip_conditions:
                continue

            rule['conditions'] = [conditions[condition]]

            # Create the CCCL policy object.
            policy = Policy(partition=partition, **policy_data)

            # Create on the BIG-IP
            try:
                policy.create(bigip)
            except exceptions.F5CcclError as e:
                print(e)

            # Retrieve it from the BIG-IP
            (icr_policy, code) = self._get_policy_from_bigip(bigip, partition)

            # Compare.
            assert icr_policy
            assert policy == IcrPolicy(**icr_policy.raw)

            # Delete the policy
            try:
                policy.delete(bigip)
            except exceptions.F5CcclError as e:
                print(e)

    def test_create_policy_supported_actions(self, bigip, partition, pool):
        """Create a policy with supported actions"""
        if isinstance(bigip, MagicMock):
            return

        policy_data = {
            'name': self.name,
            'strategy': "/Common/first-match",
            'rules': [
                {
                    'name': "test_rule0",
                    'actions': [],
                    'conditions': []
                }
            ]
        }
        rule = policy_data['rules'][0]

        skip_actions = ["invalid_action"]
        for action in actions:
            if action in skip_actions:
                continue

            rule['actions'] = [actions[action]]

            # Create the CCCL policy object.
            policy = Policy(partition=partition, **policy_data)

            # Create on the BIG-IP
            try:
                policy.create(bigip)
            except exceptions.F5CcclError as e:
                print(e)

            # Retrieve it from the BIG-IP
            (icr_policy, code) = self._get_policy_from_bigip(bigip, partition)

            # Compare.
            assert icr_policy
            assert policy == IcrPolicy(**icr_policy.raw)

            # Delete the policy
            try:
                policy.delete(bigip)
            except exceptions.F5CcclError as e:
                print(e)
