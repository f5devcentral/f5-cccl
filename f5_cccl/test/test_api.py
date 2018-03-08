#!/usr/bin/env python
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
from f5_cccl.api import F5CloudServiceManager

def test_create_cccl(bigip_proxy):
    """Test CCCL instantiation."""
    bigip = bigip_proxy.mgmt_root()
    partition = 'test'
    user_agent = 'k8s-bigip-ctlr-1.2.1-abcdef'
    prefix = 'myprefix'

    cccl = F5CloudServiceManager(
        bigip,
        partition,
        user_agent=user_agent,
        prefix=prefix)

    assert partition == cccl.get_partition()
    assert user_agent in bigip.icrs.session.headers['User-Agent']
    assert prefix == cccl._bigip_proxy._prefix
