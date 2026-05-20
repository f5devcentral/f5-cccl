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
import os
import tempfile

from f5.bigip import ManagementRoot

LOGGER = logging.getLogger(__name__)


def mgmt_root(host, username, password, port, token, trusted_certs=''):
    """Create a BIG-IP Management Root object.

    Args:
        host: BIG-IP hostname or IP address
        username: BIG-IP admin username
        password: BIG-IP admin password
        port: BIG-IP management port (default: 443)
        token: Token type for authentication (e.g., "tmos")
        trusted_certs: Optional PEM-encoded CA certificate bundle for TLS
                       verification. If provided, SSL verification is enabled
                       using these certificates. If empty, SSL verification is
                       disabled (insecure, for backward compatibility).

    Returns:
        ManagementRoot: A connected BIG-IP management object
    """
    if trusted_certs:
        # Write trusted certs to a temporary file for use with ManagementRoot.
        # The temp file must persist for the lifetime of the ManagementRoot
        # session so delete=False is used.
        cert_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.pem', delete=False)
        try:
            cert_file.write(trusted_certs)
            cert_file.flush()
            cert_file.close()
            LOGGER.info(
                "SSL verification enabled with trusted certificate(s) "
                "from Secret")
            return ManagementRoot(
                host, username, password, port=port, token=token,
                verify=cert_file.name)
        except Exception as e:
            LOGGER.error(
                "Failed to configure SSL verification with trusted "
                "certs: %s", e)
            # Clean up temp file on error
            try:
                os.unlink(cert_file.name)
            except OSError:
                pass
            raise
    else:
        # Backward compatibility: SSL verification disabled (insecure)
        return ManagementRoot(
            host, username, password, port=port, token=token)
