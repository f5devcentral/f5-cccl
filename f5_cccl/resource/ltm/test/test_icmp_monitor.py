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

import conftest
import f5_cccl.resource.ltm.icmp_monitor as target


class Test_ICMPMonitor(conftest.TestLtmResource):
    pass  # any further deviation should be tested here...


def test_entry():
    assert target.ICMPMonitor.monitor_schema_kvps._asdict() == \
        target.default_schema, "Verified entry vector assignment"
