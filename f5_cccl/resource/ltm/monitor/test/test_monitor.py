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

from mock import MagicMock
from mock import Mock
from mock import patch

import conftest
import f5
import f5_cccl.exceptions as exceptions
import f5_cccl.resource.ltm.monitor.monitor as target


class Test_Monitor(conftest.TestLtmResource):
    store_logger = target.logger
    partition = 'partition'
    name = 'name'
    args = dict(interval=2, recv='receive', send="GET /\\r\\n", timeout=3)

    @pytest.fixture(autouse=True)
    def store_target(self, request):
        request.addfinalizer(self.restore_target)
        self.target_entry = target._entry
        self.target_get_dynamic_schema = target.get_dynamic_schema

    # Fixtures and environment setups
    def create_child(self):
        """Creates a child by mocking the parent's __init__() method

        This utilizes the conftest.TestLtmResource class's create_ltm_resource
        method in the assistance of creating a child without the parent
        running its __init__.
        """
        mock_name = Mock()
        mock_partition = Mock()
        self.monitor = target.Monitor(self.name, self.partition, **self.args)

    def crud_run(self, test, expected=None):
        bigip = Mock()
        self.logger.reset_mock()
        mock_parent = Mock() if not expected else Mock(return_value=expected)
        print(expected, mock_parent.return_value)
        self.monitor._data['name'] = test
        call = getattr(self.monitor, test, None)
        with patch('f5_cccl.resource.Resource.{}'.format(test), mock_parent,
                   create=True):
            result = call(bigip)
            print(result)
        mock_parent.assert_called_once()
        assert bigip in mock_parent.call_args[0]
        self.logger.debug.assert_called_once()
        assert test in self.logger.debug.call_args[0][0], \
            "logger.debug({})".format(test)
        return result

    # .conftest.TestLtmResource.create_ltm_resource
    @pytest.fixture(autouse=True)
    def create_monitor(self, create_ltm_resource, mock_logger):
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

    def restore_logger(self):
        """Restores logger as per mock_logger() method"""
        target.logger = self.store_logger

    def restore_target(self):
        target._entry = self.target_entry
        target.get_dynamic_schema = self.target_get_dynamic_schema
        target._entry()

    def test_entry(self):
        assert target.Monitor.monitor_schema_kvps._asdict() == \
            target.default_schema, "Verified entry vector assignment"

    def test__cmp__(self):
        # all the same behavior
        self.monitor.__eq__ = Mock(return_value=True)
        assert self.monitor.__cmp__(self.name)
        self.monitor.__eq__.assert_called_once_with(self.name)

    def test__eq__(self):
        args = self.args
        compare = MagicMock(spec=f5.bigip.resource.Resource)
        compare.raw = args.copy()
        assert self.monitor == self.monitor, "self-against self test"
        args['interval'] = 1
        assert not self.monitor == args, "Negative test"
        with pytest.raises(TypeError):
            self.monitor == "foo"
        print(compare.raw, self.monitor._data)
        assert self.monitor == compare, "big-ip object test"

    def test__hash__(self):
        self.monitor._data['name'], self.monitor._data['partition'] = \
            (self.name, self.partition)
        expected = hash("{}{}{}".format(self.partition, self.name,
                                        self.monitor.__class__))
        assert expected == self.monitor.__hash__(), "hash test"

    def test__init__(self):
        pos_args = self.args.copy()
        # positive tests...
        assert self.logger.debug.called, "Logged that type=None"
        equals_test = True
        for item in pos_args.keys():
            value = pos_args[item]
            if self.monitor._data[item] != value:
                equals_test = False
                break
        assert equals_test, "creation positive test"
        # negative tests... starting with no args
        with pytest.raises(exceptions.F5CcclResourceCreateError):
            target.Monitor(None, None)
        # With a bad type:
        neg_args = pos_args.copy()
        neg_args['type'] = 'foodog'
        with pytest.raises(exceptions.F5CcclResourceCreateError):
            target.Monitor(self.name, self.partition, **neg_args)
        # finishing with bad entry...
        target.Monitor.monitor_schema_kvps = None
        with pytest.raises(EnvironmentError):
            target.Monitor(None, None)

    def test__ne__(self):
        # negative case...
        self.monitor.__eq__ = Mock(return_value=False)
        assert self.monitor.__ne__(self.name), 'neg test'
        self.monitor.__eq__.assert_called_once_with(self.name)
        # positive case...
        self.monitor.__eq__.return_value = True
        assert not self.monitor.__ne__(self.name), 'pos test'

    def test__str__(self):
        self.monitor._data['name'], self.monitor._data['partition'] = \
            (self.name, self.partition)
        result = str(self.monitor)
        mon_type = str(type(self.monitor))
        name, partition = ('name', 'partition')
        self.monitor._data['name'] = name
        self.monitor._data['partition'] = partition
        assert name in result and partition in result and mon_type in result, \
            "str() test"

    def test_uri_path(self):
        with pytest.raises(NotImplementedError):
            self.monitor._uri_path(Mock())

    def test_create(self):
        self.crud_run('create')

    def test_delete(self):
        self.crud_run('delete')

    def test_update(self):
        self.crud_run('update')

    def test_read(self):
        expected = 'ret_case'
        result = self.crud_run('read', expected=expected)
        assert result == expected, "read got case back!"
