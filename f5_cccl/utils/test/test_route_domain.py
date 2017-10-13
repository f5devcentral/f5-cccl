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


from requests.utils import quote as urlquote

from f5_cccl.utils.route_domain \
    import combine_ip_and_route_domain
from f5_cccl.utils.route_domain \
    import encoded_normalize_address_with_route_domain
from f5_cccl.utils.route_domain \
        import normalize_address_with_route_domain
from f5_cccl.utils.route_domain \
        import split_ip_with_route_domain


def test_combine_ip_and_route_domain():
    """Test proper behavior of combine_ip_and_route_domain."""

    tests = [
        ["1.2.3.4", 12, "1.2.3.4%12"],
        ["64:ff9b::", 13, "64:ff9b::%13"]
    ]
    for test in tests:
        result = combine_ip_and_route_domain(test[0], test[1])
        assert result == test[2]

    # def combine_ip_and_route_domain(ip, route_domain):
    # u"""Return address that includes IP and route domain

    # Input ip format must be of the form:
    #     <ipv4_or_ipv6>
    # """
    # address = "{}%{}".format(ip, route_domain)
    # return address


def test_split_ip_with_route_domain():
    """Test proper behavior of split_ip_with_route_domain."""

    tests = [
        ["1.2.3.4%1", "1.2.3.4", 1],
        ["1.2.3.4", "1.2.3.4", None],
        ["64:ff9b::%2", "64:ff9b::", 2],
        ["64:ff9b::", "64:ff9b::", None]
    ]
    for test in tests:
        results = split_ip_with_route_domain(test[0])
        assert results[0] == test[1]
        assert results[1] == test[2]

def test_normalize_address_with_route_domain():
    """Test proper behavior of normalize_address_with_route_domain."""

    # If route domain is not specified, add the default
    tests = [
        ["1.2.3.4%1", 2, "1.2.3.4%1", "1.2.3.4", 1],
        ["1.2.3.4", 2, "1.2.3.4%2", "1.2.3.4", 2],
        ["64:ff9b::%1", 2, "64:ff9b::%1", "64:ff9b::", 1],
        ["64:ff9b::", 2, "64:ff9b::%2", "64:ff9b::", 2]
    ]
    for test in tests:
        results = normalize_address_with_route_domain(test[0], test[1])
        assert results[0] == test[2]
        assert results[1] == test[3]
        assert results[2] == test[4]

def test_encoded_normalize_address_with_route_domain():
    """Test proper behavior of encoded_normalize_address_with_route_domain."""

    # test wrapper for test_normalize_address_with_route_domain but with
    # address input/output being either url encoded or url unencoded
    tests = [
        ["1.2.3.4%1", 2, False, False, "1.2.3.4%1"],
        ["1.2.3.4%1", 2, False, True, urlquote("1.2.3.4%1")],
        [urlquote("1.2.3.4%1"), 2, True, False, "1.2.3.4%1"],
        [urlquote("1.2.3.4%1"), 2, True, True, urlquote("1.2.3.4%1")],

        ["64:ff9b::", 2, False, False, "64:ff9b::%2"],
        ["64:ff9b::", 2, False, True, urlquote("64:ff9b::%2")],
        [urlquote("64:ff9b::"), 2, True, False, "64:ff9b::%2"],
        [urlquote("64:ff9b::"), 2, True, True, urlquote("64:ff9b::%2")]
    ]

    for test in tests:
        result = encoded_normalize_address_with_route_domain(
            test[0], test[1], test[2], test[3])
        assert result == test[4]
