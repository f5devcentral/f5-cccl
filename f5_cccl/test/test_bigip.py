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
from f5_cccl import bigip
from f5.bigip import BigIP
from f5_cccl.resource.ltm.pool import BigIPPool
from f5_cccl.resource.ltm.virtual import VirtualServer
import json
from mock import Mock, patch
import pytest


class Pool():
    """A mock BIG-IP Pool."""

    def __init__(self, name, **kwargs):
        """Initialize the object."""
        self.name = name
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def modify(self, **kwargs):
        """Placeholder: This will be mocked."""
        pass

    def update(self, **kwargs):
        """Placeholder: This will be mocked."""
        pass

    def create(self, partition=None, name=None, **kwargs):
        """Create the pool object."""
        pass

    def delete(self):
        """Delet the pool object."""
        pass


class Member():
    """A mock BIG-IP Pool Member."""

    def __init__(self, name, **kwargs):
        """Initialize the object."""
        self.name = name
        self.session = kwargs.get('session', None)
        if kwargs.get('state', None) == 'user-up':
            self.state = 'up'
        else:
            self.state = 'user-down'

    def modify(self, **kwargs):
        """Placeholder: This will be mocked."""
        pass


class Profiles():
    """A container of Virtual Server Profiles."""

    def __init__(self, **kwargs):
        """Initialize the object."""
        self.profiles = kwargs.get('profiles', [])

    def exists(self, name, partition):
        """Check for the existance of a profile."""
        for p in self.profiles:
            if p['name'] == name and p['partition'] == partition:
                return True

        return False

    def create(self, name, partition):
        """Placeholder: This will be mocked."""
        pass


class ProfileSet():
    """A set of Virtual Server Profiles."""

    def __init__(self, **kwargs):
        """Initialize the object."""
        self.profiles = Profiles(**kwargs)


class Virtual():
    """A mock BIG-IP Virtual Server."""

    def __init__(self, name, **kwargs):
        """Initialize the object."""
        self.profiles_s = ProfileSet(**kwargs)
        self.name = name
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def modify(self, **kwargs):
        """Placeholder: This will be mocked."""
        pass

    def create(self, name=None, partition=None, **kwargs):
        """Create the virtual object."""
        pass

    def delete(self):
        """Delete the virtual object."""
        pass

    def load(self, name=None, partition=None):
        """Load the virtual object."""
        pass


class HealthCheck():
    """A mock BIG-IP Health Monitor."""

    def __init__(self, name, **kwargs):
        """Initialize the object."""
        self.name = name
        self.interval = kwargs.get('interval', None)
        self.timeout = kwargs.get('timeout', None)
        self.send = kwargs.get('send', None)
        self.partition = kwargs.get('partition', None)

    def modify(self, **kwargs):
        """Placeholder: This will be mocked."""
        pass

    def delete(self):
        """Delete the healthcheck object."""
        pass


class VxLANTunnel():
    """A mock BIG-IP VxLAN tunnel."""

    def __init__(self, partition, name, initial_records):
        """Initialize the object."""
        self.partition = partition
        self.name = name
        self.records = initial_records

    def update(self, **kwargs):
        """Update list of vxlan records."""
        self.records = []
        if 'records' in kwargs:
            self.records = kwargs['records']


class MockService():
    """A mock Services service object."""

    def __init__(self):
        """Initialize the object."""
        pass

    def load(self, name, partition):
        """Load a mock iapp."""
        pass

    def create(self, name=None, template=None, partition=None, variables=None,
               tables=None, trafficGroup=None, description=None):
        """Create a mock iapp."""
        pass


class MockServices():
    """A mock Application services object."""

    def __init__(self):
        """Initialize the object."""
        self.service = MockService()

    def get_collection(self):
        """Get collection of iapps."""
        return []


class MockApplication():
    """A mock Sys application object."""

    def __init__(self):
        """Initialize the object."""
        self.services = MockServices()


class MockFolders():
    """A mock Sys folders object."""

    def __init__(self):
        """Initialize the object."""

    def get_collection():
        """Get collection of partitions."""
        pass


class MockSys():
    """A mock BIG-IP sys object."""

    def __init__(self):
        """Initialize the object."""
        self.application = MockApplication()
        self.folders = MockFolders()


class MockIapp():
    """A mock BIG-IP iapp object."""

    def __init__(self, name=None, template=None, partition=None,
                 variables=None, tables=None, trafficGroup=None,
                 description=None):
        """Initialize the object."""
        self.name = name
        self.partition = partition
        self.template = template
        self.variables = variables
        self.tables = tables
        self.trafficGroup = trafficGroup
        self.description = description

    def delete(self):
        """Mock delete method."""
        pass

    def update(self, executeAction=None, name=None, partition=None,
               variables=None, tables=None, **kwargs):
        """Mock update method."""
        pass


class MockFolder():
    """A mock BIG-IP folder object."""

    def __init__(self, name):
        """Initialize the object."""
        self.name = name


class MockHttp():
    """A mock Https http object."""

    def __init__(self):
        """Initialize the object."""

    def create(self, partition=None, **kwargs):
        """Create a http healthcheck object."""
        pass

    def load(self, name=None, partition=None):
        """Load a http healthcheck object."""
        pass


class MockHttps():
    """A mock Monitor https object."""

    def __init__(self):
        """Initialize the object."""
        self.http = MockHttp

    def get_collection(self):
        """Get collection of http healthchecks."""
        pass


class MockTcp():
    """A mock Tcps tcp object."""

    def __init__(self):
        """Initialize the object."""
        pass

    def create(self, partition=None, **kwargs):
        """Create a tcp healthcheck object."""
        pass

    def load(self, name=None, partition=None):
        """Load a tcp healthcheck object."""
        pass


class MockTcps():
    """A mock Monitor tcps object."""

    def __init__(self):
        """Initialize the object."""
        self.tcp = MockTcp()

    def get_collection(self):
        """Get collection of tcp healthchecks."""
        pass


class MockMonitor():
    """A mock Ltm monitor object."""

    def __init__(self):
        """Initialize the object."""
        self.https = MockHttps()
        self.tcps = MockTcps()


class MockVirtuals():
    """A mock Ltm virtuals object."""

    def __init__(self):
        """Initialize the object."""
        self.virtual = Virtual('test')

    def get_collection(self):
        """Get collection of virtuals."""
        pass


class MockPools():
    """A mock Ltm pools object."""

    def __init__(self):
        """Initialize the object."""
        self.pool = Pool('test')

    def get_collection(self):
        """Get collection of pools."""
        pass


class MockLtm():
    """A mock BIG-IP ltm object."""

    def __init__(self):
        """Initialize the object."""
        self.monitor = MockMonitor()
        self.virtuals = MockVirtuals()
        self.pools = MockPools()


class MockHealthMonitor():
    """A mock BIG-IP healthmonitor object."""

    def __init__(self, name, partition):
        """Initialize the object."""
        self.name = name
        self.partition = partition


class BigIPTest(bigip.CommonBigIP):
    """BIG-IP configuration tests.

    Test BIG-IP configuration given various cloud states and existing
    BIG-IP states
    """

    def create_mock_pool(self, name, **kwargs):
        """Create a mock pool server object."""
        pool = Pool(name, **kwargs)
        self.pools[name] = pool
        pool.modify = Mock()
        return pool

    def create_mock_pool_member(self, name, **kwargs):
        """Create a mock pool member object."""
        member = Member(name, **kwargs)
        self.members[name] = member
        member.modify = Mock()
        return member

    def mock_virtuals_get_collection(self, requests_params=None):
        """Mock: Return a mocked collection of pools."""
        virtuals = []
        for v in self.bigip_data['virtuals']:
            virtual = Virtual(**v)
            virtuals.append(virtual)

        return virtuals

    def mock_pools_get_collection(self, requests_params=None):
        """Mock: Return a mocked collection of pools."""
        pools = []
        for p in self.bigip_data['pools']:
            pool = Pool(**p)
            pools.append(pool)

        return pools

    def read_test_data(self, bigip_state):
        """Read test data for the Big-IP state."""
        # Read the BIG-IP state
        with open(bigip_state) as json_data:
            self.bigip_data = json.load(json_data)


@pytest.fixture()
def big_ip():
    """Fixture to supply a moked BIG-IP."""
    # Mock the call to _get_tmos_version(), which tries to make a
    # connection
    with patch.object(BigIP, '_get_tmos_version'):
        big_ip = BigIPTest('1.2.3.4', '443', 'admin', 'admin', ['test1'])
    #big_ip = BigIPTest('10.190.24.182', '443', 'admin', 'admin', ['test1'])

    big_ip.sys = MockSys()
    big_ip.ltm = MockLtm()

    big_ip.ltm.pools.get_collection = \
        Mock(side_effect=big_ip.mock_pools_get_collection)
    big_ip.ltm.virtuals.get_collection = \
        Mock(side_effect=big_ip.mock_virtuals_get_collection)

    return big_ip


def test_bigip_refresh(big_ip, bigip_state='f5_cccl/test/bigip_data.json'):
    """Test BIG-IP refresh function."""
    big_ip.read_test_data(bigip_state)

    test_pools = []
    for p in big_ip.bigip_data['pools']:
        pool = BigIPPool(**p)
        test_pools.append(pool)
    test_virtuals = []
    for v in big_ip.bigip_data['virtuals']:
        test_virtuals.append(VirtualServer(**v))


    # refresh the BIG-IP state
    big_ip.refresh()

    # verify pools and pool members
    assert big_ip.ltm.pools.get_collection.called
    assert len(big_ip._pools) == 2

    assert len(big_ip._pools) == len(test_pools)
    for a, b in zip(big_ip._pools, test_pools):
        assert a == b

    # Make a change, pools will not be equal
    for p in test_pools:
        p._data['loadBalancingMode'] = 'Not a valid LB mode'

    for a, b in zip(big_ip._pools, test_pools):
        assert a != b

    # verify virtual servers 
    assert big_ip.ltm.virtuals.get_collection.called
    assert len(big_ip._virtuals) == 2

    assert len(big_ip._virtuals) == len(test_virtuals)
    for a, b in zip(big_ip._virtuals, test_virtuals):
        assert a == b
