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
import requests

from mock import MagicMock

from f5_cccl.api import F5CloudServiceManager

from f5.bigip import ManagementRoot

from icontrol.exceptions import iControlUnexpectedHTTPError

requests.packages.urllib3.disable_warnings()


def _wrap_instrument(f, counters, name):
    def instrumented(*args, **kwargs):
        counters[name] += 1
        return f(*args, **kwargs)
    return instrumented


def instrument_bigip(mgmt_root):
    icr = mgmt_root.__dict__['_meta_data']['icr_session']
    counters = {}
    mgmt_root.test_rest_calls = counters

    for method in ['get', 'put', 'delete', 'patch', 'post']:
        counters[method] = 0
        orig = getattr(icr.session, method)
        instrumented = _wrap_instrument(orig, counters, method)
        setattr(icr.session, method, instrumented)
    return mgmt_root


@pytest.fixture(scope="module")
def bigip():
    if pytest.symbols:
        hostname = pytest.symbols.bigip_mgmt_ip
        username = pytest.symbols.bigip_username
        password = pytest.symbols.bigip_password
        port = pytest.symbols.bigip_port

        bigip_fix = ManagementRoot(hostname, username, password, port=port)
        bigip_fix = instrument_bigip(bigip_fix)
    else:
        bigip_fix = MagicMock()

    yield bigip_fix


@pytest.fixture(scope="function")
def bigip_rest_counters(bigip):
    counters = bigip.test_rest_calls
    for k in list(counters.keys()):
        counters[k] = 0

    yield counters

    for k in list(counters.keys()):
        counters[k] = 0


@pytest.fixture(scope="function")
def partition(bigip):
    name = "Test1"
    partition = None

    # Cleanup partition, in case previous runs were interrupted
    try:
        bigip.tm.ltm.virtuals.virtual.load(
            name="test_virtual", partition=name).delete()
    except iControlUnexpectedHTTPError as icr_error:
        pass
    try:
        bigip.tm.auth.partitions.partition.load(name=name).delete()
    except iControlUnexpectedHTTPError as icr_error:
        pass

    try:
        partition = bigip.tm.auth.partitions.partition.create(subPath="/", name=name)
    except iControlUnexpectedHTTPError as icr_error:
        code = icr_error.response.status_code
        if code == 400:
            print(("Can't create partition {}".format(name)))
        elif code == 409:
            print(("Partition {} already exists".format(name)))
            partition = bigip.tm.auth.partitions.partition.load(subPath="/", name=name)
        else:
            print("Unknown error creating partition.")
        print(icr_error)

    yield name

    for pool in bigip.tm.ltm.pools.get_collection():
        if pool.partition == name:
            pool.delete()
    for virtual in bigip.tm.ltm.virtuals.get_collection():
        if virtual.partition == name:
            virtual.delete()
    partition.delete()


@pytest.fixture(scope="function")
def cccl(bigip, partition):
    cccl = F5CloudServiceManager(bigip, partition)
    yield cccl
    cccl.apply_ltm_config({})


@pytest.fixture()
def pool(bigip, partition):
    name = "pool1"
    partition = partition
    model = {'name': name, 'partition': partition}

    try:
        pool = bigip.tm.ltm.pools.pool.create(**model)
    except iControlUnexpectedHTTPError as icr_error:
        code = icr_error.response.status_code
        if code == 400:
            print(("Can't create pool {}".format(name)))
        elif code == 409:
            print(("Pool {} already exists".format(name)))
            partition = bigip.tm.ltm.pools.pool.load(partition=partition,
                                                     name=name)
        else:
            print("Unknown error creating pool.")
        print(icr_error)

    yield name

    pool.delete()
