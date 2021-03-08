#!/usr/bin/env python
# Copyright (c) 2017-2021 F5 Networks, Inc.
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

from collections import namedtuple
from glob import glob
from mock import Mock
from mock import MagicMock

import f5.bigip.resource

from f5.bigip import ManagementRoot

import f5_cccl.exceptions as exceptions
import f5_cccl.resource.ltm.monitor.monitor as target
import f5_cccl.resource.ltm.monitor.http_monitor as http
import f5_cccl.resource.ltm.monitor.https_monitor as https
import f5_cccl.resource.ltm.monitor.icmp_monitor as icmp
import f5_cccl.resource.ltm.monitor.tcp_monitor as tcp

from icontrol.exceptions import iControlUnexpectedHTTPError


BigIPConnection = \
    namedtuple('Connection', 'hostname, port, username, password, image')
# to bypass the automation and assign your own BIG-IP, edit the following:
big_ip_connection = None
# example:
# big_ip_connection = \
#    BigIPConnection('10.128.1.145', 443, 'admin', 'funstuff',
#                    'BIGIP-11.6.0.LTM.Tiny')


class MockBigIP(object):
    """This object mocks the BIG-IP object from the f5.bigip module

    For monitors, this object mocks the BIG-IP interactions as needed to allow
    for overall CCCL, standalone functionality tests for monitors.

    THIS CLASS DOES NOT SUPPORT MULTI-THREADED TESTING!!  Two separate
    instances would be fine; however, across the same instance, this CAN BREAK!
    """
    __store_create = dict()

    def __init__(self):
        self.tm = Mock()
        # HTTP and default monitors:
        self.tm.ltm.monitor.https.http.create = self.store_create
        self.tm.ltm.monitor.https.http.load = self.read_from_create
        # HTTPS monitor:
        self.tm.ltm.monitor.https_s.https.create = self.store_create
        self.tm.ltm.monitor.https_s.https.load = self.read_from_create
        # ICMP monitor:
        self.tm.ltm.monitor.gateway_icmps.gateway_icmp.create = (
            self.store_create
        )
        self.tm.ltm.monitor.gateway_icmps.gateway_icmp.load = (
            self.read_from_create
        )
        # TCP monitor:
        self.tm.ltm.monitor.tcps.tcp.create = self.store_create
        self.tm.ltm.monitor.tcps.tcp.load = self.read_from_create

    def store_create(self, **items):
        try:
            key = self.derive_key(items)
            self.__store_create[key] = items
        except Exception:
            response = Mock()
            response.status_code = 409
            error = iControlUnexpectedHTTPError(
                "Key Word 'name' or 'partition' is missing!",
                response=response)
            raise error

    def derive_key(self, items):
        return "{}:{}".format(items['name'], items['partition'])

    def nuke_from_create(self, **items):
        key = self.last_key
        self.__store_create.pop(key)

    def update_create(self, **items):
        key = self.last_key
        self.__store_create[key].update(items)

    def read_from_create(self, *args, **items):
        key = self.derive_key(items)
        retval = MagicMock(spec=f5.bigip.resource.Resource)
        retval.delete = self.nuke_from_create
        retval.modify = self.update_create
        retval.update = self.update_create
        self.last_key = key
        try:
            retval.raw = self.__store_create[key].copy()
        except KeyError:
            response = Mock()
            response.status_code = 404
            raise iControlUnexpectedHTTPError("NOT FOUND HERE!",
                                              response=response)
        return retval


class Provisioned(object):
    """Allows cleanup of provisioned, real objects, such as a BIG-IP

    This object can be used with a 'with' statement to then later clean up
    a monitor object on a provisioned BIG-IP object.  This object can be
    expanded to handle clean up of other, provisioned items during testing
    if needed.
    """

    def __init__(self, monitor, bigip):
        """Provisioned(monitor, bigip)

        with Provisioned(monitor, bigip):
            <tests>

        Will cause an auto-cleanup of the provisioned bigip object by running
        the monitor's `delete` method.  Yes, this assumes that the delete
        operation on the Resource object will work.
        """
        self.monitor = monitor
        self.bigip = bigip

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        if not isinstance(self.bigip, MockBigIP):
            try:
                self.monitor.delete(MockBigIP)
            except exceptions.F5CcclResourceDeleteError:
                # Good test, you cleaned up after yourself...
                pass
            else:
                msg = "We failed to clean BIG-IP of ({})".format(self.monitor)
                raise EnvironmentError(msg)


class TestMonitor(object):
    """This is a functional test for the Monitor class

    This test class will dynamically determine whether or not the test should
    be ran against an existing, available BIG-IP or not.

    To run this against a BIG-IP make sure that the object-level attribute
    'BIG-IP connection' (big_ip_connect) has a valid address within it.  This
    can be set at a higher-level object or parent.

    If the big_ip_connect does not evaluate as True, then a mock interface is
    built in its stead and the responses are trialed against pre-mocked data.

    NOTE: A test WILL fail if a big_ip_connect is present and evaluates as
    true, but importing f5-SDK and other dependencies did not succeed!
    """
    _big_ip_connect = None
    _load_yml_file = "/tmp/.*fntest_cccl_bigip.yml"

    def install_bigip(self, request):
        """Installs an actual BIG-IP as the object's bigip attribute

        This method uses the F5-SDK to construct a BIG-IP object.
        """
        request.addfinalizer(self.nuke_bigip_config)
        cx = self._big_ip_connect
        args = [cx.hostname, cx.username, cx.password]
        self.bigip = ManagementRoot(*args, port=cx.port)

    def nuke_bigip_config(self):
        """This is a place holder for a means to nuke the BIG-IP of all configs
        """
        pass  # implement some script or option by which to nuke the config

    def get_bigip(self):
        """Constructs a Mocked BIG-IP object

        This stores a mocked instance of the object's BIG-IP interactions from
        the SDK by using the affore-created MockBigIP object.
        """
        self.bigip = MockBigIP()

    @pytest.fixture()
    def check_load_yml(self):
        """A place holder method to load a BIG-IP's connection data from a file

        This meathod will load a BIG-IP's connection data from a yaml file.
        This will then be set within this object in such a way that the
        BIG-IP will be utilized rather than mocked objects.
        """
        potential = glob(self._load_yml_file)
        if potential:
            pass  # implement reading the yml

    @pytest.fixture(autouse=True)
    def bigip_or_premodeled(self, request, check_load_yml):
        """This will determine whether or not we're using a real BIG-IP or fake

        Please keep in mind that any "fake" data here to mimic the BIG-IP
        should always be verified responses to the BIG-IP for the mock-data.
        This type of test has the source data be mock-data and the responses
        perfectly mimic how a healthy BIG-IP of a particular version might
        respond.
        """
        if self._big_ip_connect:
            self.install_bigip(request)
            # set the self call to this method to install_bigip
            self.bigip_or_premodeled = self.install_bigip
        else:
            self.get_bigip()
            # set the self call to this method to get_bigip
            self.bigip_or_premodeled = self.get_bigip

    def crud_test(self, monitor):
        """Performs basic CRUD activities on a CCCL Resource object
        """
        with Provisioned(monitor, self.bigip):
            monitor.create(self.bigip)
            read = monitor.read(self.bigip)
            assert monitor == read.raw, "Read result test"
            monitor._data['interval'] = 1
            monitor.update(self.bigip)
            updated = monitor.read(self.bigip)
            assert monitor != read.raw, "Self vs previous read updated result test"
            assert updated.raw != read.raw, "Previously read vs updated test"
            monitor.delete(self.bigip)
            with pytest.raises(exceptions.F5CcclResourceNotFoundError):
                monitor.read(self.bigip)

    def test_crud_http_monitor(self):
        """Tests the http monitor arch-type"""
        assert getattr(self, 'bigip', None), \
            'We should always have a bigip at this point...'
        partition = 'Common'
        name = 'test_http'
        schema = http.HTTPMonitor.properties
        schema['partition'] = partition
        schema['name'] = name
        monitor = http.HTTPMonitor(**schema)
        self.crud_test(monitor)

    def test_crud_https_monitor(self):
        """Tests the https monitor arch-type"""
        assert getattr(self, 'bigip', None), \
            'We should always have a bigip at this point...'
        partition = "Common"
        name = "test_https"
        schema = https.HTTPSMonitor.properties
        schema['partition'] = partition
        schema['name'] = name
        monitor = https.HTTPSMonitor(**schema)
        self.crud_test(monitor)

    def test_crud_icmp_monitor(self):
        """Tests the icmp monitor arch-type"""
        assert getattr(self, 'bigip', None), \
            'We should always have a bigip at this point...'
        partition = "Common"
        name = "test_icmp"
        schema = icmp.ICMPMonitor.properties
        schema['partition'] = partition
        schema['name'] = name
        monitor = icmp.ICMPMonitor(**schema)
        self.crud_test(monitor)

    def test_crud_tcp_monitor(self):
        """Tests the tcp monitor arch-type"""
        assert getattr(self, 'bigip', None), \
            'We should always have a bigip at this point...'
        partition = "Common"
        name = "test_tcp"
        schema = tcp.TCPMonitor.properties
        schema['partition'] = partition
        schema['name'] = name
        monitor = tcp.TCPMonitor(**schema)
        self.crud_test(monitor)


if __name__ != '__main__':
    if big_ip_connection:
        TestMonitor._big_ip_connect = big_ip_connection
