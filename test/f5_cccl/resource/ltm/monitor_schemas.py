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

import f5_cccl.resource.ltm.monitor as default_monitor
import f5_cccl.resource.ltm.http_monitor as http
import f5_cccl.resource.ltm.https_monitor as https
import f5_cccl.resource.ltm.icmp_monitor as icmp
import f5_cccl.resource.ltm.tcp_monitor as tcp

"""A repository of default schemas importable abstracted for tests.
"""

# Monitor:
default_schema = default_monitor.default_schema

# HTTP:
http_default = http.default_schema

# HTTPS:
https_default = https.default_schema

# ICMP:
icmp_default = icmp.default_schema

# TCP:
tcp_default = tcp.default_schema
