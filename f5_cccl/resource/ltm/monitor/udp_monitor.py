"""Hosts an interface for the BIG-IP Monitor Resource.

This module references and holds items relevant to the orchestration of the F5
BIG-IP for purposes of abstracting the F5-SDK library.
"""
# coding=utf-8
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

from f5_cccl.resource.ltm.monitor import Monitor


LOGGER = logging.getLogger(__name__)


class UDPMonitor(Monitor):
    """Creates a CCCL BIG-IP UDP Monitor Object of sub-type of Resource

    This object hosts the ability to orchestrate basic CRUD actions against a
    BIG-IP UDP Monitor via the F5-SDK.

    The major difference is the afforded schema for UDP specifically.
    """
    properties = dict(interval=5, recv="", send="", timeout=16)

    def __init__(self, name, partition, **kwargs):
        super(UDPMonitor, self).__init__(name, partition, **kwargs)
        for key in ['send', 'recv']:
            self._data[key] = kwargs.get(key, self.properties.get(key))

    def _uri_path(self, bigip):
        """Get the URI resource path key for the F5-SDK for UDP monitor

        This is the URI reference for an UDP Monitor.
        """
        return bigip.tm.ltm.monitor.udps.udp


class ApiUDPMonitor(UDPMonitor):
    """Create the canonical UDP monitor from API input."""
    pass


class IcrUDPMonitor(UDPMonitor):
    """Create the canonical UDP monitor from API input."""
    def __init__(self, name, partition, **kwargs):
        try:
            super(IcrUDPMonitor, self).__init__(name, partition, **kwargs)
        except ValueError:
            # Need to allow for misconfigured legacy monitors from BIG-IP,
            # so let this through
            pass
