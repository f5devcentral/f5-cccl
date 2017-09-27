"""Provides a class for managing BIG-IP L7 Policy resources."""
# coding=utf-8
#
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

import logging
from operator import itemgetter

from f5_cccl.resource import Resource
from f5_cccl.resource.ltm.policy.action import Action
from f5_cccl.resource.ltm.policy.condition import Condition
from f5_cccl.resource.ltm.policy.rule import Rule


LOGGER = logging.getLogger(__name__)


class Policy(Resource):
    """L7 Policy class."""
    # The property names class attribute defines the names of the
    # properties that we wish to compare.
    properties = dict(
        name=None,
        partition=None,
        strategy="/Common/first-match",
        rules=list()
    )

    def __init__(self, name, partition, **data):
        """Create the policy and nested class objects"""
        super(Policy, self).__init__(name, partition)

        # Get the rules.
        rules = data.get('rules', list())
        self._data['rules'] = self._create_rules(rules)

        self._data['strategy'] = data.get(
            'strategy',
            self.properties.get('strategy')
        )

        # Fix these values.
        self._data['legacy'] = True
        self._data['controls'] = ["forwarding"]
        self._data['requires'] = ["http"]

    def __eq__(self, other):
        """Check the equality of the two objects.

        Only compare the properties as defined in the
        properties class dictionany.
        """
        if not isinstance(other, Policy):
            return False

        for key in self.properties:
            if key == 'rules':
                if len(self._data['rules']) != len(other.data['rules']):
                    return False
                for index, rule in enumerate(self._data['rules']):
                    if rule != other.data['rules'][index]:
                        return False
                continue
            if self._data[key] != other.data.get(key, None):
                return False
        return True

    def __str__(self):
        return str(self._data)

    def _create_rules(self, rules):
        """Create a list of the policy Rules from rules data.

        The order of the rules in the list is taken as the order
        in which the should be evaluated.
        """
        new_rules = list()
        for index, rule in enumerate(rules):
            rule['ordinal'] = index
            new_rules.append(Rule(**rule).data)

        return new_rules

    def _uri_path(self, bigip):
        return bigip.tm.ltm.policys.policy


class IcrPolicy(Policy):
    """Policy object created from the iControl REST object"""
    def __init__(self, name, partition, **data):
        policy_data = self._flatten_policy(data)
        super(IcrPolicy, self).__init__(name, partition, **policy_data)

    def _flatten_policy(self, data):
        """Flatten the unnecessary levels of nesting for the policy object.

        The structure of a policy are returned by the SDK looks like:

        'policy': {
            ...,
            'rulesReference': {
                ...,
                'items': [
                    ...,
                    'actionsReference': [
                        ...,
                        'items': [
                            {action0}, {action1},...,{actionN}
                        ]
                    ],
                    'rulesReference': [
                        ...,
                        'items': [
                            {rule0}, {rule1},...,{ruleN}
                        ]
                    ]
                ]
            }
        }

        Flattens to a simpler representation:
        'policy': {
            ...,
            'rules': {
                ...,
                'actions': [
                     {action0}, {action1},...,{actionN}
                 ]
                 'rules': [
                     {rule0}, {rule1},...,{ruleN}
                 ]
            }
        }

        This function does filter some of the Rule, Action, and Condition
        properties.
        """
        policy = dict()
        for key in Policy.properties:
            if key == 'rules':
                rulesReference = data['rulesReference']
                if 'items' in rulesReference:
                    policy['rules'] = self._flatten_rules(
                        rulesReference['items'])
            elif key == 'name' or key == 'partition':
                pass
            else:
                policy[key] = data.get(key)
        return policy

    def _flatten_rules(self, rules_list):
        rules = list()

        for rule in sorted(rules_list, key=itemgetter('ordinal')):
            flat_rule = dict()
            for key in Rule.properties:
                if key == 'actions':
                    flat_rule['actions'] = self._flatten_actions(rule)
                elif key == 'conditions':
                    flat_rule['conditions'] = self._flatten_condition(rule)
                else:
                    flat_rule[key] = rule.get(key)
            rules.append(flat_rule)
        return rules

    def _flatten_actions(self, rule):
        actions = list()
        actions_reference = rule.get('actionsReference', dict())

        for action in actions_reference.get('items', list()):
            flat_action = dict()
            for key in Action.properties:
                flat_action[key] = action.get(key)
            actions.append(flat_action)
        return actions

    def _flatten_condition(self, rule):
        conditions = list()
        conditions_reference = rule.get('conditionsReference', dict())

        for condition in conditions_reference.get('items', list()):
            flat_condition = dict()
            for key in Condition.properties:
                flat_condition[key] = condition.get(key)
            conditions.append(flat_condition)
        return conditions


class ApiPolicy(Policy):
    """Policy object created from the API configuration object"""
    pass
