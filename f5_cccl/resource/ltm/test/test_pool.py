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
import pytest

from mock import Mock
from mock import patch

import conftest
import f5_cccl.exceptions as exceptions
import f5_cccl.resource.ltm.pool as target


class Test_Pool(conftest.TestLtmResource):
    store_logger = target.logger

    # Fixtures and environment setups
    def create_child(self):
        """Creates a child by mocking the parent's __init__() method

        This utilizes the conftest.TestLtmResource class's create_ltm_resource
        method in the assistance of creating a child without the parent
        running its __init__.
        """
        mock_name = Mock()
        mock_partition = Mock()
        args = \
            dict(description='description',
                 loadBalancingMode='loadBalancingMode', members='members',
                 monitor='monitor', name=mock_name, partition=mock_partition)
        self.pool = target.Pool(**args)
        self.pool._name = mock_name
        self.pool._partition = mock_partition
        self.args = args

    # .conftest.TestLtmResource.create_ltm_resource
    @pytest.fixture(autouse=True)
    def create_pool(self, create_ltm_resource):
        """Creates a child via mocking the parent and customization

        This test fixture will create a child via conftest.TestLtmResource and
        self.create_child().  Then customization can be performed to better
        handle the using tests.
        """
        self.create_ltm_resource()

    @pytest.fixture(autouse=True)
    def mock_logger(self, request):
        """Creates a Mock() instance for test target's logger object"""
        request.addfinalizer(self.restore_logger)
        self.logger = Mock()
        target.logger = self.logger

    def negative_init_case(self, **kwargs):
        args = self.args
        args.update(kwargs)
        mock_parent = Mock()
        with patch('f5_cccl.resource.Resource.__init__', mock_parent,
                   create=True):
            with pytest.raises(exceptions.F5CcclResourceCreateError):
                print(args)
                target.Pool(**args)

    def restore_logger(self):
        """Restores logger as per mock_logger() method"""
        target.logger = self.store_logger

    def not_implemented(self, method, *args):
        with pytest.raises(NotImplementedError):
            if args:
                method(*args)
            else:
                method()

    def test__eq__(self, mock_logger):
        myself = 'myself'
        comparison = 'comparison'
        call_with = [myself, comparison]
        mock_extract_comparison = Mock(
            side_effect=[comparison, comparison, comparison, comparison,
                         comparison, NotImplementedError])
        self.pool._Pool__shallow_compare = Mock(side_effect=[
                                                None, None, AssertionError,
                                                None, NotImplementedError])
        self.pool._Pool__member_compare = Mock(side_effect=[
                                               None, None, AssertionError,
                                               NotImplementedError])
        self.pool.__dict__ = Mock(return_value=myself)
        with patch('f5_cccl.resource.ltm.pool.extract_comparison',
                   mock_extract_comparison, create=True):
            assert self.pool == self.pool, "Positive Pool test"
            self.pool._Pool__shallow_compare.assert_called_once_with(
                *call_with)
            self.pool._Pool__member_compare.assert_called_once_with(*call_with)
            assert self.pool == dict(), 'Positive dict test'
            assert not self.pool == dict(), 'Negative member compare'
            assert not self.pool == dict(), 'Negative shallow compare'
            for cnt in range(2):
                with pytest.raises(NotImplementedError):
                    self.pool == dict()

    def test__dict__(self):
        result = self.pool.__dict__()
        args = self.args

        # parent should handle...
        args.pop('name')
        args.pop('partition')

        # perform our tests...
        assert result == self.args, "positive test"

    def test__init__(self):
        """Tests the target's __init__ method"""
        for arg in self.args:
            if arg == 'name' or arg == 'partition':
                # parent should test this...
                continue
            assert getattr(self.pool, arg, None) == arg
        # negative case, missing either name or partition
        self.negative_init_case(name='present', partition=None)
        self.negative_init_case(partition='present', name=None)

    def test_add_member(self):
        self.not_implemented(self.pool.add_member, 'member')

    def test_create(self):
        """tests the appropriate creation of a f5_cccl.resource.ltm.pool.Pool

        This test is heavily dependent on fixtures in this repo and in conftest
        and only tests the positive case.
        """
        expected = 'expected'
        assert expected == self.with_mocking_super_methods(
            self.pool.create, 'f5_cccl.resource.Resource.create',
            expected=expected, arg='bigip'), "Positive Return Case"

    def test_delete(self, mock_logger):
        """Tests the target's delete method"""
        assert not self.with_mocking_super_methods(
            self.pool.delete,
            'f5_cccl.resource.Resource.delete'), 'Positive Return Case'

    def test_equals(self):
        """Test target's equals method

        This validates the case of a list of members and a string of monitors
        along with the rest of the schema.
        """
        comparison = 'comaprison'
        self.pool.__eq__ = Mock(side_effect=[True, False])
        assert self.pool.equals(comparison), "Positive case test"
        assert not self.pool.equals(comparison), "Negative case test"

    def test_find_member(self):
        self.not_implemented(self.pool.find_member, 'member')

    def test_member_list(self):
        """Tests target's member_list method

        This is a fairly unique method to Pool.  This test method will test the
        retrieval method of a list of members.
        """
        expected = self.pool._data['members']
        assert expected == self.pool.member_list(), \
            "There should be no difference here..."

    def test__member_compare(self):
        self.not_implemented(self.pool._Pool__member_compare,
                             'myself', 'compare')

    def test_properties(self):
        for arg in self.args:
            assert getattr(self.pool, arg, None) == self.args[arg], \
                "{} property test".format(arg)

    def test_read(self, mock_logger):
        """Tests the target's read method"""
        expected = 'expected'
        bigip = 'bigip'
        assert self.with_mocking_super_methods(
            self.pool.read, 'f5_cccl.resource.Resource.read', expected,
            bigip) == expected, "Positive return case"

    def test_read_member(self):
        self.not_implemented(self.pool.read_member, 'member')

    def test__shallow_compare(self):
        # positive case:
        # dict().copy avoided for a reason...
        baseline = self.pool._data.copy()
        negative_missing_key = baseline.copy()
        negative_changed_attr = baseline.copy()
        positive_match = baseline.copy()
        negative_missing_key.pop('description')
        negative_changed_attr['description'] = 'will never be me'
        self.pool._Pool__shallow_compare(baseline, positive_match)
        with pytest.raises(KeyError):
            self.pool._Pool__shallow_compare(baseline, negative_missing_key)
        with pytest.raises(AssertionError):
            self.pool._Pool__shallow_compare(baseline, negative_changed_attr)

    def test_update(self):
        """Tests 2 cases: when there's a difference and where is not"""
        bigip = 'bigip'
        assert not self.with_mocking_super_methods(
            self.pool.update, 'f5_cccl.resource.Resource.update',
            arg=bigip), "Positive return case"

    def update_difference_case(self, data=None, p_id=Mock(), poolp=Mock(),
                               partition=Mock()):
        """Tests the need for an update

        This is not a test, but it does suppliment test_update
        """
        pass

    def update_no_difference_case(self, data=None, p_id=Mock(), poolp=Mock(),
                                  partition=Mock()):
        """Tests the case for no need to update

        This is not a test, but it does assist test_update.
        """
        pass

    def with_mocking_super_methods(
                self, method, mock_case, expected=None, arg=None):
        """Performs the testing steps for create() and delete()"""
        positive_return_value = 'positive_return_value'
        mock_parent = Mock(
            side_effect=[expected, exceptions.F5CcclResourceNotFoundError])
        with patch(mock_case, mock_parent,
                   create=True):

            # Positive case:
            if arg:
                positive_return_value = method(arg)
            else:
                positive_return_value = method()
            if arg:
                mock_parent.assert_called_once_with(arg)
            else:
                mock_parent.assert_called_once_with()

            # Negative case:
            with pytest.raises(exceptions.F5CcclResourceNotFoundError):
                if arg:
                    method(arg)
                else:
                    method()
        return positive_return_value


def test_extract_comparison():
    compare_pool = target.Pool(name='name', partition='partition')
    # Test pool case:
    assert target.extract_comparison(compare_pool) == \
        compare_pool.__dict__()
    # dict cases:
    cases = [dict(name='List of members=dict',
                  comparison=dict(members=[dict(name='foo')], name='foo'),
                  expected=dict(members=dict(foo=dict(name='foo')),
                                name='foo')),
             dict(name='dict of members',
                  comparison=dict(members=dict(), name='foo'),
                  expected='self'),
             dict(name='NotImplemented members type',
                  comparison=dict(members=str(), name='foo'),
                  expected=NotImplementedError),
             dict(name='NotImplemented member type',
                  comparison=dict(members=[str()], name='foo'),
                  expected=NotImplementedError)]
    for case in cases:
        name = case['name']
        comparison = case['comparison']
        expected = case['comparison'] if case['expected'] == 'self' else \
            case['expected']
        if isinstance(expected, type):
            with pytest.raises(expected):
                target.extract_comparison(comparison)
        else:
            result = target.extract_comparison(comparison)
            assert result == expected, name
