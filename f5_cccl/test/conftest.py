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
from f5.bigip import ManagementRoot
import json
from mock import Mock, patch
import pytest


class MockNode():
    """A mock BIG-IP node."""

    def __init__(self, name, **kwargs):
        """Initialize the object."""
        self.name = name
        for key in kwargs:
            setattr(self, key, kwargs[key])
        self.raw = self.__dict__

    def modify(self, **kwargs):
        """Placeholder: This will be mocked."""
        pass

    def update(self, **kwargs):
        """Placeholder: This will be mocked."""
        pass

    def create(self, partition=None, name=None, **kwargs):
        """Create the node object."""
        pass

    def delete(self):
        """Delete the node object."""
        pass

    def load(self, name=None, partition=None):
        """Load the node object."""
        return MockNode(name)


class Pool():
    """A mock BIG-IP Pool."""

    def __init__(self, name, **kwargs):
        """Initialize the object."""
        self.name = name
        for key in kwargs:
            setattr(self, key, kwargs[key])
        self.raw = self.__dict__

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
        """Delete the pool object."""
        pass

    def load(self, name=None, partition=None):
        """Load the pool object."""
        return Pool(name)


class Policy():
    """A mock BIG-IP Policy."""

    def __init__(self, name, **kwargs):
        """Initialize the object."""
        self.name = name
        for key in kwargs:
            setattr(self, key, kwargs[key])
        self.raw = self.__dict__

    def modify(self, **kwargs):
        """Placeholder: This will be mocked."""
        pass

    def update(self, **kwargs):
        """Placeholder: This will be mocked."""
        pass

    def create(self, partition=None, name=None, **kwargs):
        """Create the policy object."""
        pass

    def delete(self):
        """Delete the policy object."""
        pass

    def load(self, name=None, partition=None):
        """Load the policy object."""
        return Policy(name)


class IRule():
    """A mock BIG-IP iRule."""

    def __init__(self, name, **kwargs):
        """Initialize the object."""
        self.name = name
        for key in kwargs:
            setattr(self, key, kwargs[key])
        self.raw = self.__dict__

    def modify(self, **kwargs):
        """Placeholder: This will be mocked."""
        pass

    def update(self, **kwargs):
        """Placeholder: This will be mocked."""
        pass

    def create(self, partition=None, name=None, **kwargs):
        """Create the iRule object."""
        pass

    def delete(self):
        """Delete the iRule object."""
        pass

    def load(self, name=None, partition=None):
        """Load the iRule object."""
        return IRule(name)


class VirtualAddress():
    """A mock BIG-IP VirtualAddress."""

    def __init__(self, name, **kwargs):
        """Initialize the object."""
        self.name = name
        for key in kwargs:
            setattr(self, key, kwargs[key])
        self.raw = self.__dict__

    def modify(self, **kwargs):
        """Placeholder: This will be mocked."""
        pass

    def update(self, **kwargs):
        """Placeholder: This will be mocked."""
        pass

    def create(self, partition=None, name=None, **kwargs):
        """Create the virtual address object."""
        pass

    def delete(self):
        """Delete the virtual address object."""
        pass

    def load(self, name=None, partition=None):
        """Load the virtual address object."""
        return VirtualAddress(name)


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


class Policies():
    """A container of Virtual Server Policies."""

    def __init__(self, **kwargs):
        """Initialize the object."""
        self.policies = kwargs.get('policies', [])

    def exists(self, name, partition):
        """Check for the existance of a policy."""
        for p in self.policies:
            if p['name'] == name and p['partition'] == partition:
                return True

        return False

    def create(self, name, partition):
        """Placeholder: This will be mocked."""
        pass


class PolicySet():
    """A set of Virtual Server Policies."""

    def __init__(self, **kwargs):
        """Initialize the object."""
        self.policies = Policies(**kwargs)


class Virtual():
    """A mock BIG-IP Virtual Server."""

    def __init__(self, name, **kwargs):
        """Initialize the object."""
        self.profiles_s = ProfileSet(**kwargs)
        self.policies_s = PolicySet(**kwargs)
        self.name = name
        for key in kwargs:
            setattr(self, key, kwargs[key])

        self.raw = self.__dict__

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
        return Virtual(name) 


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


class Partition():
    """A mock BIG-IP Partition."""

    def __init__(self, name, **kwargs):
        """Initialize the object."""
        self.name = name
        if kwargs.get('default-route-domain') is not None:
            self.defaultRouteDomain = kwargs.get('default-route-domain')
        else:
            self.defaultRouteDomain = 0
        for key in kwargs:
            setattr(self, key, kwargs[key])
        self.raw = self.__dict__

    def modify(self, **kwargs):
        """Placeholder: This will be mocked."""
        pass

    def create(self, name=None, **kwargs):
        """Create the partition object."""
        pass

    def delete(self):
        """Delete the partition object."""
        pass

    def load(self, name=None):
        """Load the partition object."""
        return Partition(name)


class MockPartitions():
    """A mock Auth partitions object."""

    def __init__(self):
        """Initialize the object."""
        self.partition = Partition('test')

    def get_collection(self):
        """Get collection of partitions."""
        pass


class MockService():
    """A mock Services service object."""

    def __init__(self):
        """Initialize the object."""
        pass

    def load(self, name, partition):
        """Load a mock iapp."""
        return MockService()

    def create(self, name=None, template=None, partition=None, variables=None,
               tables=None, trafficGroup=None, description=None):
        """Create a mock iapp."""
        pass

    def update(self, **properties):
        """Update a mock iapp."""
        pass

    def delete(self):
        """Delete the iapp object."""
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


class Iapp():
    """A mock BIG-IP iapp object."""

    def __init__(self, name=None, **kwargs):
        """Initialize the object."""
        self.name = name
        for key in kwargs:
            setattr(self, key, kwargs[key])
        self.raw = self.__dict__

    def delete(self):
        """Mock delete method."""
        pass

    def update(self, executeAction=None, name=None, partition=None,
               variables=None, tables=None, **kwargs):
        """Mock update method."""
        pass


class InternalDataGroup():
    """A mock BIG-IP data_group internal."""

    def __init__(self, name, **kwargs):
        """Initialize the object."""
        self.name = name
        #self.partition = partition
        for key in kwargs:
            setattr(self, key, kwargs[key])
        self.raw = self.__dict__

    def modify(self, **kwargs):
        """Placeholder: This will be mocked."""
        pass

    def update(self, **kwargs):
        """Placeholder: This will be mocked."""
        pass

    def create(self, partition=None, name=None, **kwargs):
        """Create the iRule object."""
        pass

    def delete(self):
        """Delete the iRule object."""
        pass

    def load(self, name=None, partition=None):
        """Load the iRule object."""
        return InternalDataGroup(name, partition)


class MockFolder():
    """A mock BIG-IP folder object."""

    def __init__(self, name):
        """Initialize the object."""
        self.name = name


class MockHttp():
    """A mock Http http object."""

    def __init__(self, name=None, **kwargs):
        """Initialize the object."""
        self.name = name
        for key in kwargs:
            setattr(self, key, kwargs[key])
        self.raw = self.__dict__

    def create(self, partition=None, **kwargs):
        """Create a http healthcheck object."""
        pass

    def delete(self):
        """Delete the monitor object."""
        pass

    def load(self, name=None, partition=None):
        """Load an http healthcheck object."""
        return MockHttp(name) 


class MockHttps():
    """A mock Monitor https object."""

    def __init__(self):
        """Initialize the object."""
        self.http = MockHttp()

    def get_collection(self):
        """Get collection of http healthchecks."""
        return []


class MockTcp():
    """A mock Tcps tcp object."""

    def __init__(self):
        """Initialize the object."""
        pass

    def create(self, partition=None, **kwargs):
        """Create a tcp healthcheck object."""
        pass

    def delete(self):
        """Delete the monitor object."""
        pass

    def load(self, name=None, partition=None):
        """Load a tcp healthcheck object."""
        return MockTcp() 


class MockTcps():
    """A mock Monitor tcps object."""

    def __init__(self):
        """Initialize the object."""
        self.tcp = MockTcp()

    def get_collection(self):
        """Get collection of tcp healthchecks."""
        return []


class MockIcmp():
    """A mock Icmps tcp object."""

    def __init__(self):
        """Initialize the object."""
        pass

    def create(self, partition=None, **kwargs):
        """Create a tcp healthcheck object."""
        pass

    def delete(self):
        """Delete the monitor object."""
        pass

    def load(self, name=None, partition=None):
        """Load a tcp healthcheck object."""
        return MockIcmp()


class MockIcmps():
    """A mock Monitor tcps object."""

    def __init__(self):
        """Initialize the object."""
        self.gateway_icmp = MockIcmp()

    def get_collection(self):
        """Get collection of tcp healthchecks."""
        return []


class MockHttpS():
    """A mock Icmps tcp object."""

    def __init__(self):
        """Initialize the object."""
        pass

    def create(self, partition=None, **kwargs):
        """Create a tcp healthcheck object."""
        pass

    def delete(self):
        """Delete the monitor object."""
        pass

    def load(self, name=None, partition=None):
        """Load a tcp healthcheck object."""
        return MockHttpS()


class MockHttpSs():
    """A mock Monitor tcps object."""

    def __init__(self):
        """Initialize the object."""
        self.https = MockHttpS()

    def get_collection(self):
        """Get collection of tcp healthchecks."""
        pass


class MockMonitor():
    """A mock Ltm monitor object."""

    def __init__(self):
        """Initialize the object."""
        self.https = MockHttps()
        self.tcps = MockTcps()
        self.https_s = MockHttpSs()
        self.gateway_icmps = MockIcmps()

class MockVirtuals():
    """A mock Ltm virtuals object."""

    def __init__(self):
        """Initialize the object."""
        self.virtual = Virtual('test')

    def get_collection(self):
        """Get collection of virtuals."""
        pass


class MockVirtualAddresses():
    """A mock Ltm virtual address object."""

    def __init__(self):
        """Initialize the object."""
        self.virtual_address = VirtualAddress('test')

    def get_collection(self):
        """Get collection of virtual addresses."""
        return []


class MockPools():
    """A mock Ltm pools object."""

    def __init__(self):
        """Initialize the object."""
        self.pool = Pool('test')

    def get_collection(self):
        """Get collection of pools."""
        pass


class MockPolicys():
    """A mock Ltm policy object."""

    def __init__(self):
        """Initialize the object."""
        self.policy = Policy('test')

    def get_collection(self):
        """Get collection of policies."""
        pass


class MockIRules():
    """A mock Ltm iRules object."""

    def __init__(self):
        """Initialize the object."""
        self.rule = IRule('test')

    def get_collection(self):
        """Get collection of iRules."""
        pass


class MockNodes():
    """A mock Ltm nodes object."""

    def __init__(self):
        """Initialize the object."""
        self.node = MockNode('test')

    def get_collection(self):
        """Get collection of nodes."""
        pass


class MockDataGroupInternals():
    """A mock Ltm data-group internals object."""

    def __init__(self):
        """Initialize the object."""
        self.internal = MockDataGroupInternal()
        pass


class MockDataGroupInternal():
    """A mock Ltm data-group internal object."""

    def __init__(self):
        """Initialize the object."""
        pass

    def modify(self, **kwargs):
        """Placeholder: This will be mocked."""
        pass

    def update(self, **kwargs):
        """Placeholder: This will be mocked."""
        pass

    def create(self, partition=None, name=None, **kwargs):
        """Create the object."""
        pass

    def delete(self):
        """Delete the object."""
        pass

    def load(self, name=None, partition=None):
        """Load the object."""
        return InternalDataGroup(name)


class MockDataGroup():
    """A mock Ltm data_group object."""

    def __init__(self):
        """Initialize the object."""
        self.internals = MockDataGroupInternals()

class MockAuth():
    """A mock BIG-IP auth object."""

    def __init__(self):
        """Initialize the object."""
        self.partitions = MockPartitions()

class MockLtm():
    """A mock BIG-IP ltm object."""

    def __init__(self):
        """Initialize the object."""
        self.monitor = MockMonitor()
        self.virtuals = MockVirtuals()
        self.pools = MockPools()
        self.nodes = MockNodes()
        self.policys = MockPolicys()
        self.rules = MockIRules()
        self.virtual_address_s = MockVirtualAddresses()
        self.data_group = MockDataGroup()

class MockTm():
    def __init__(self):
        self.ltm = MockLtm()
        self.auth = MockAuth()
        self.sys = MockSys()


class MockHealthMonitor():
    """A mock BIG-IP healthmonitor object."""

    def __init__(self, name, partition):
        """Initialize the object."""
        self.name = name
        self.partition = partition


class MockBigIP(ManagementRoot):
    """BIG-IP configuration tests.

    Test BIG-IP configuration given various cloud states and existing
    BIG-IP states
    """

    def partition_from_params(self, params): 
        """Extract partition name from the request params"""
        return params.split("partition+eq+")[1].split("&expand")[0]

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
        """Mock: Return a mocked collection of virtuals."""
        partition = self.partition_from_params(requests_params['params'])
        resources = self.bigip_data['virtuals']
        virtuals = [
            Virtual(**r)
            for r in resources if partition == r['partition']
        ]
        return virtuals

    def mock_pools_get_collection(self, requests_params=None):
        """Mock: Return a mocked collection of pools."""
        partition = self.partition_from_params(requests_params['params'])
        resources = self.bigip_data['pools']
        pools = [
            Pool(**r)
            for r in resources if partition == r['partition']
        ]
        return pools

    def mock_policys_get_collection(self, requests_params=None):
        """Mock: Return a mocked collection of policies."""
        partition = self.partition_from_params(requests_params['params'])
        policies = [
            Policy(**r)
            for r in self.bigip_data['policies'] if partition == r['partition']
        ]
        return policies

    def mock_irules_get_collection(self, requests_params=None):
        """Mock: Return a mocked collection of iRules."""
        partition = self.partition_from_params(requests_params['params'])
        resources = self.bigip_data['rules']
        irules = [
            IRule(**r)
            for r in resources if partition == r['partition']
        ]
        return irules

    def mock_iapps_get_collection(self, requests_params=None):
        """Mock: Return a mocked collection of app svcs."""
        partition = self.partition_from_params(requests_params['params'])
        resources = self.bigip_data['iapps']
        iapps = [
            Iapp(**r)
            for r in resources if partition == r['partition']
        ]
        return iapps

    def mock_monitors_get_collection(self, requests_params=None):
        partition = self.partition_from_params(requests_params['params'])
        resources = self.bigip_data['monitors']
        monitors = [
            MockHttp(**r)
            for r in resources if partition == r['partition']
        ]
        return monitors

    def mock_nodes_get_collection(self, requests_params=None):
        """Mock: Return a mocked collection of nodes."""
        partition = self.partition_from_params(requests_params['params'])
        resources = self.bigip_data['nodes']
        nodes = [
            MockNode(**r)
            for r in resources if partition == r['partition']
        ]
        return nodes

    def mock_vas_get_collection(self, requests_params=None):
        """Mock: Return a mocked collection of virtual addresses."""
        partition = self.partition_from_params(requests_params['params'])
        resources = self.bigip_data['virtual_addresses']
        vas = [
            MockVirtualAddress(**r)
            for r in resources if partition == r['partition']
        ]
        return vas

    def mock_data_group_internals_get_collection(self, requests_params=None):
        """Mock: Return a mocked collection of data_group internal."""
        partition = self.partition_from_params(requests_params['params'])
        resources = self.bigip_data['internaldatagroups']
        int_dgs = [
            InternalDataGroup(**r)
            for r in resources if partition == r['partition']
        ]
        return int_dgs

    def read_test_data(self, bigip_state):
        """Read test data for the Big-IP state."""
        # Read the BIG-IP state
        with open(bigip_state) as json_data:
            self.bigip_data = json.load(json_data)


@pytest.fixture
def bigip_proxy():

    with patch.object(ManagementRoot, '_get_tmos_version'):
        mgmt_root = MockBigIP('1.2.3.4', 'admin', 'admin')

    mgmt_root.tm = MockTm()

    mgmt_root.tm.ltm.pools.get_collection = \
        Mock(side_effect=mgmt_root.mock_pools_get_collection)
    mgmt_root.tm.ltm.policys.get_collection = \
        Mock(side_effect=mgmt_root.mock_policys_get_collection)
    mgmt_root.tm.ltm.rules.get_collection = \
        Mock(side_effect=mgmt_root.mock_irules_get_collection)
    mgmt_root.tm.ltm.virtuals.get_collection = \
        Mock(side_effect=mgmt_root.mock_virtuals_get_collection)
    mgmt_root.tm.ltm.monitor.https.get_collection = \
        Mock(side_effect=mgmt_root.mock_monitors_get_collection)
    mgmt_root.tm.ltm.monitor.https_s.get_collection = \
        Mock(side_effect=mgmt_root.mock_monitors_get_collection)
    mgmt_root.tm.ltm.monitor.tcps.get_collection = \
        Mock(side_effect=mgmt_root.mock_monitors_get_collection)
    mgmt_root.tm.ltm.monitor.gateway_icmps.get_collection = \
        Mock(side_effect=mgmt_root.mock_monitors_get_collection)
    mgmt_root.tm.sys.application.services.get_collection = \
        Mock(side_effect=mgmt_root.mock_iapps_get_collection)
    mgmt_root.tm.ltm.nodes.get_collection = \
        Mock(side_effect=mgmt_root.mock_nodes_get_collection)
    mgmt_root.tm.ltm.virtual_address_s.get_collection = \
        Mock(side_effect=mgmt_root.mock_vas_get_collection)
    mgmt_root.tm.ltm.data_group.internals.get_collection = \
        Mock(side_effect=mgmt_root.mock_data_group_internals_get_collection)

    bigip_state='f5_cccl/test/bigip_data.json'
    mgmt_root.read_test_data(bigip_state)

    bigip_proxy = bigip.BigIPProxy(mgmt_root, 'test')

    return bigip_proxy
