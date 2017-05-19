#!/usr/bin/env python
"""Hosts an interface for the BIG-IP Monitor Resource.

This module references and holds items relevant to the orchestration of the F5
BIG-IP for purposes of abstracting the F5-SDK library.
"""
#
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

import logging

from collections import namedtuple

from f5_cccl.resource.ltm.monitor import Monitor

logger = logging.getLogger(__name__)
default_schema = dict(interval=5, send='', timeout=16)


class ICMPMonitor(Monitor):
    """Creates a CCCL BIG-IP ICMP Monitor Object of sub-type of Resource

    This object hosts the ability to orchestrate basic CRUD actions against a
    BIG-IP ICMP Monitor via the F5-SDK.

    The major difference is the afforded schema for ICMP specifically.
    """
    monitor_schema_kvps = None

    def _uri_path(self, bigip):
        """Get the URI resource path key for the F5-SDK for ICMP monitor

        This is the URI reference for an ICMP Monitor.
        """
        return bigip.tm.ltm.monitor.icmps.icmp


def _entry():
    schema = default_schema
    ICMPMonitor.monitor_schema_kvps = \
        namedtuple('ICMPMonitor', schema.keys())(**schema)


if __name__ != '__main__':
    # Don't want bad users directly executing this...
    _entry()

# vim: set expandtab tabstop=4
