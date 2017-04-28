# Copyright 2017 F5 Networks
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Controller Unit Tests.

Units tests for testing command-line args, Marathon state parsing, and
BIG-IP resource management.

"""
import unittest
import json
import requests
from mock import Mock
import f5
import icontrol


class Pool():
    """A mock BIG-IP Pool."""

    def __init__(self, name, **kwargs):
        """Initialize the object."""
        self.name = name
        self.monitor = kwargs.get('monitor', None)
        self.loadBalancingMode = kwargs.get('balance', None)

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
        self.enabled = kwargs.get('enabled', None)
        self.disabled = kwargs.get('disabled', None)
        self.ipProtocol = kwargs.get('ipProtocol', None)
        self.destination = kwargs.get('destination', None)
        self.pool = kwargs.get('pool', None)
        self.sourceAddressTranslation = kwargs.get('sourceAddressTranslation',
                                                   None)
        self.profiles = kwargs.get('profiles', [])
        self.partition = kwargs.get('partition', None)

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


class BigIPTest(unittest.TestCase):
    """BIG-IP configuration tests.

    Test BIG-IP configuration given various cloud states and existing
    BIG-IP states
    """

    virtuals = {}
    profiles = {}
    pools = {}
    virtuals = {}
    members = {}
    healthchecks = {}

    def mock_get_pool_member_list(self, partition, pool):
        """Mock: Get a mocked list of pool members."""
        try:
            return self.bigip_data[pool]
        except KeyError:
            return []

    def mock_get_node_list(self, partition):
        """Mock: Get a mocked list of nodes."""
        return ['10.141.141.10']

    def mock_get_http_healthcheck_collection(self):
        """Mock: Get a mocked list of http health monitors."""
        monitors = []
        for key in self.hm_data:
            if 'http' in self.hm_data[key]['type']:
                monitors.append(MockHealthMonitor(key, self.test_partition))
        return monitors

    def mock_get_tcp_healthcheck_collection(self):
        """Mock: Get a mocked list of http health monitors."""
        monitors = []
        for key in self.hm_data:
            if self.hm_data[key]['type'] == 'tcp':
                monitors.append(MockHealthMonitor(key, self.test_partition))
        return monitors

    def mock_iapp_service_create(self, name, template, partition, variables,
                                 tables, trafficGroup, description):
        """Mock: Create a mocked iapp."""
        self.test_iapp = MockIapp(name=name, template=template,
                                  partition=partition, variables=variables,
                                  tables=tables, trafficGroup=trafficGroup,
                                  description=description)
        return self.test_iapp

    def mock_iapp_service_load(self, name, partition):
        """Mock: Get a mocked iapp."""
        self.test_iapp = MockIapp(name=name, partition=partition)
        return self.test_iapp

    def mock_iapp_services_get_collection(self):
        """Mock: Get a mocked collection of iapps."""
        self.test_iapp_list = \
            [MockIapp(name='server-app2_iapp_10000_vs',
                      partition=self.test_partition)]
        return self.test_iapp_list

    def mock_iapp_update_services_get_collection(self):
        """Mock: Get a mocked collection of iapps for iapp update."""
        self.test_iapp_list = \
            [MockIapp(name='default_configmap',
                      partition=self.test_partition)]
        return self.test_iapp_list

    def mock_partition_folders_get_collection(self):
        """Mock: Get a mocked collection of partitions."""
        folder = MockFolder('mesos')
        folder2 = MockFolder('mesos2')
        return [folder, folder2]

    def create_mock_pool(self, name, **kwargs):
        """Create a mock pool server object."""
        pool = Pool(name, **kwargs)
        self.pools[name] = pool
        pool.modify = Mock()
        return pool

    def create_mock_virtual(self, name, **kwargs):
        """Create a mock virtual server object."""
        virtual = Virtual(name, **kwargs)
        self.virtuals[name] = virtual
        virtual.modify = Mock()
        virtual.profiles_s.profiles.create = Mock()
        self.profiles = kwargs.get('profiles', [])
        return virtual

    def create_mock_pool_member(self, name, **kwargs):
        """Create a mock pool member object."""
        member = Member(name, **kwargs)
        self.members[name] = member
        member.modify = Mock()
        return member

    def create_mock_healthcheck(self, name, **kwargs):
        """Create a mock healthcheck object."""
        healthcheck = HealthCheck(name, **kwargs)
        self.healthchecks[name] = healthcheck
        healthcheck.modify = Mock()
        return healthcheck

    def mock_get_pool(self, partition, name):
        """Lookup a mock pool object by name."""
        return self.pools.get(name, None)

    def mock_get_virtual(self, partition, name):
        """Lookup a mock virtual server object by name."""
        return self.virtuals.get(name, None)

    def mock_get_virtual_address(self, partition, name):
        """Lookup a mock virtual Address object by name."""
        return name

    def mock_get_member(self, partition, pool, name):
        """Lookup a mock pool member object by name."""
        return self.members.get(name, None)

    def mock_get_healthcheck(self, partition, hc, hc_type):
        """Lookup a mock healthcheck object by name."""
        return self.healthchecks.get(hc, None)

    def mock_get_virtual_profiles(self, virtual):
        """Return a list of Virtual Server profiles."""
        return self.profiles

    def mock_virtual_create(self, name=None, partition=None, **kwargs):
        """Mock: Creates a mocked virtual server."""
        self.test_virtual.append({'name': name, 'partition': partition})

    def mock_pool_create(self, partition=None, name=None, **kwargs):
        """Mock: Create a mocked pool."""
        self.test_pool.append({'name': name, 'partition': partition})

    def mock_healthmonitor_create(self, partition=None, **kwargs):
        """Mock: Create a mocked tcp or http healthmonitor."""
        self.test_monitor.append({'partition': partition,
                                  'name': kwargs['name']})

    def mock_virtual_load(self, name=None, partition=None):
        """Mock: Return a mocked virtual."""
        v = Virtual(name, kwargs={'partition': partition})
        self.test_virtual.append(v)
        return v

    def mock_healtcheck_load(self, name=None, partition=None):
        """Mock: Return a mocked healthcheck."""
        hc = HealthCheck(name, kwargs={'partition': partition})
        self.test_monitor.append(hc)
        return hc

    def mock_pools_get_collection(self):
        """Mock: Return a mocked collection of pools."""
        p_collection = []
        for key in self.bigip_data:
            p = Pool(key)
            p.partition = 'mesos'
            p_collection.append(p)
        self.test_pool = p_collection
        return p_collection

    def mock_pool_load(self, name=None, partition=None, cow=3):
        """Mock: Return a mocked pool."""
        pool = Pool(name)
        self.test_pool.append(pool)
        return pool

    def mock_get_pool_list(self, partition):
        """Mock: Return previouly created pools."""
        pool_list = []
        if self.test_pool is not None:
            for pool in self.test_pool:
                if pool['partition'] == partition:
                    pool_list.append(pool['name'])
        return pool_list

    def mock_get_virtual_list(self, partition):
        """Mock: Return previously created virtuals."""
        virtual_list = []
        if self.test_virtual is not None:
            for virtual in self.test_virtual:
                if virtual['partition'] == partition:
                    virtual_list.append(virtual['name'])
        return virtual_list

    def mock_get_healthcheck_list(self, partition):
        """Mock: Return previously created healthchecks."""
        monitor_list = {}
        if self.test_monitor is not None:
            for monitor in self.test_monitor:
                if monitor['partition'] == partition:
                    monitor_list.update({monitor['name']: 'mocked'})
        return monitor_list

    def mock_virtual_delete(self, partition, virtual):
        """Mock: deletion of a virtual server."""
        if self.test_virtual is not None:
            for i in range(0, len(self.test_virtual)):
                if (self.test_virtual[i]['name'] == virtual and
                        self.test_virtual[i]['partition'] == partition):
                    self.test_virtual.pop(i)

    def read_test_vectors(self, cloud_state, bigip_state=None,
                          hm_state=None, network_state=None):
        """Read test vectors for the various states."""
        # Read the Marathon state
        if cloud_state:
            with open(cloud_state) as json_data:
                self.cloud_data = json.load(json_data)

        # Read the BIG-IP state
        if bigip_state:
            with open(bigip_state) as json_data:
                self.bigip_data = json.load(json_data)
            self.bigip.get_pool_list = Mock(
                    return_value=self.bigip_data.keys())
            self.bigip.get_virtual_list = Mock(
                    return_value=self.bigip_data.keys())
        else:
            self.bigip_data = {}
            self.bigip.get_pool_list = Mock(
                    return_value=[])
            self.bigip.get_virtual_list = Mock(
                    return_value=[])

        if hm_state:
            with open(hm_state) as json_data:
                self.hm_data = json.load(json_data)
        else:
            self.hm_data = {}

        if network_state:
            with open(network_state) as json_data:
                self.network_data = json.load(json_data)

    def raiseTypeError(self, cfg):
        """Raise a TypeError exception."""
        raise TypeError

    def raiseSDKError(self, cfg):
        """Raise an F5SDKError exception."""
        raise f5.sdk_exception.F5SDKError

    def raiseConnectionError(self, cfg):
        """Raise a ConnectionError exception."""
        raise requests.exceptions.ConnectionError

    def raiseBigIPInvalidURL(self, cfg):
        """Raise a BigIPInvalidURL exception."""
        raise icontrol.exceptions.BigIPInvalidURL

    def raiseBigiControlUnexpectedHTTPError(self, cfg):
        """Raise an iControlUnexpectedHTTPError exception."""
        raise icontrol.exceptions.iControlUnexpectedHTTPError

    def setUp(self, partition, bigip):
        """Test suite set up."""
        self.bigip = bigip
        self.test_partition = partition
        self.test_virtual = []
        self.test_pool = []
        self.test_monitor = []

        self.bigip.sys = MockSys()

        self.bigip.get_pool_member_list = \
            Mock(side_effect=self.mock_get_pool_member_list)

        self.bigip.ltm = MockLtm()

        self.bigip.ltm.virtuals.virtual.create = \
            Mock(side_effect=self.mock_virtual_create)
        self.bigip.ltm.virtuals.virtual.load = \
            Mock(side_effect=self.mock_virtual_load)

        self.bigip.ltm.pools.pool.create = \
            Mock(side_effect=self.mock_pool_create)
        self.bigip.ltm.pools.get_collection = \
            Mock(side_effect=self.mock_pools_get_collection)

        self.bigip.ltm.monitor.https.get_collection = \
            Mock(side_effect=self.mock_get_http_healthcheck_collection)
        self.bigip.ltm.monitor.tcps.get_collection = \
            Mock(side_effect=self.mock_get_tcp_healthcheck_collection)

        self.bigip.ltm.monitor.https.http.create = \
            Mock(side_effect=self.mock_healthmonitor_create)
        self.bigip.ltm.monitor.tcps.tcp.create = \
            Mock(side_effect=self.mock_healthmonitor_create)

        self.bigip.ltm.monitor.https.http.load = \
            Mock(side_effect=self.mock_healtcheck_load)
        self.bigip.ltm.monitor.tcps.tcp.load = \
            Mock(side_effect=self.mock_healtcheck_load)

        # Save the original update functions (to be restored when needed)
        self.bigip.pool_update_orig = self.bigip.pool_update
        self.bigip.virtual_update_orig = self.bigip.virtual_update
        self.bigip.member_update_orig = self.bigip.member_update
        self.bigip.healthcheck_update_orig = self.bigip.healthcheck_update
        self.bigip.healthcheck_exists_orig = self.bigip.healthcheck_exists
        self.bigip.iapp_delete_orig = self.bigip.iapp_delete
        self.bigip.iapp_create_orig = self.bigip.iapp_create
        self.bigip.pool_delete_orig = self.bigip.pool_delete
        self.bigip.iapp_update_orig = self.bigip.iapp_update

        self.bigip.get_node = Mock()
        self.bigip.pool_update = Mock()

        self.bigip.healthcheck_update = Mock()
        self.bigip.healthcheck_exists = Mock()
        self.bigip.healthcheck_exists.return_value = {'http': True,
                                                      'tcp': True}

        self.bigip.virtual_update = Mock()

        self.bigip.virtual_address_create = Mock()
        self.bigip.virtual_address_update = Mock()

        self.bigip.member_create = Mock()
        self.bigip.member_delete = Mock()
        self.bigip.member_update = Mock()

        self.bigip.iapp_create = Mock()
        self.bigip.iapp_delete = Mock()
        self.bigip.iapp_update = Mock()

        self.bigip.node_delete = Mock()

        self.bigip.sys.folders.get_collection = \
            Mock(side_effect=self.mock_partition_folders_get_collection)
        self.bigip.get_node_list = Mock(side_effect=self.mock_get_node_list)

    def tearDown(self):
        """Test suite tear down."""
        self.test_partition = None
        self.test_iapp = None
        self.test_iapp_list = None
        self.test_virtual = None
        self.test_pool = None
        self.test_monitor = None
