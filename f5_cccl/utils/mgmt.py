# coding=utf-8
#
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
"""Wrapper functions for the f5-sdk"""

import logging

from f5.bigip import ManagementRoot

log = logging.getLogger(__name__)


def mgmt_root(host, username, password, port, token, ca_certs=None):
    """Create a BIG-IP Management Root object.

    Args:
        host: BIG-IP hostname or IP.
        username: BIG-IP admin username.
        password: BIG-IP admin password.
        port: BIG-IP management port.
        token: Authentication token type (e.g. "tmos").
        ca_certs: Optional path to a PEM CA bundle file for TLS
                  verification of the BIG-IP management endpoint.
                  When *None* the default SDK behaviour (no custom
                  CA verification) is used.
    """
    bigip = ManagementRoot(host, username, password, port=port, token=token)

    # Apply custom CA certificate for TLS verification if provided.
    # The f5-sdk's ManagementRoot has an 'icrs' attribute which is an
    # iControlRESTSession — a subclass of requests.Session.
    # Setting .verify on it to a PEM file path enables TLS verification
    # against the supplied CA bundle for all subsequent REST calls.
    if ca_certs:
        try:
            bigip.icrs.verify = ca_certs
            log.info("TLS verification enabled with CA bundle: %s", ca_certs)
        except AttributeError:
            # Fallback: some f5-sdk versions may nest the session differently
            try:
                bigip.icrs.session.verify = ca_certs
                log.info("TLS verification enabled (via session.verify) with CA bundle: %s", ca_certs)
            except AttributeError:
                log.warning(
                    "Could not set verify on iControlRESTSession; "
                    "TLS verification with custom CA may not be active."
                )

    return bigip
