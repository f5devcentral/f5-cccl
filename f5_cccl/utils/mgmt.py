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

from f5.bigip import ManagementRoot


def mgmt_root(host, username, password, port, token, ca_certs=None):
    """Create a BIG-IP Management Root object
    
    Args:
        host: BIG-IP management hostname or IP
        username: BIG-IP username for authentication
        password: BIG-IP password for authentication
        port: BIG-IP management port (e.g. 443)
        token: Optional token for authentication (bypasses username/password)
        ca_certs: Optional path to CA certificate file for TLS verification.
                 If provided, TLS verification is enabled using this CA bundle.
                 If None or empty, default system CA verification is used.
    
    Returns:
        ManagementRoot: f5-sdk ManagementRoot instance for API operations
    """
    # Build kwargs for ManagementRoot, only including ca_certs if provided
    kwargs = {
        'port': port,
        'token': token,
    }
    
    # E7: Per-endpoint trusted certs support
    # When ca_certs is provided and non-empty, pass it to ManagementRoot
    # for TLS verification. This supports both file paths and PEM-formatted
    # certificate strings (f5-sdk auto-detects the format).
    if ca_certs:
        kwargs['ca_certs'] = ca_certs
    
    return ManagementRoot(host, username, password, **kwargs)
