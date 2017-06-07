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

from f5_cccl.resource.ltm.profile import Profile
from mock import Mock
import pytest


cfg_test = {
    'name': 'tcp',
    'partition': 'Common',
    'context': 'all'
}


@pytest.fixture
def bigip():
    bigip = Mock()
    return bigip


def test_create_profile():
    """Test Profile creation."""
    profile = Profile(
        **cfg_test
    )
    assert profile

    # verify all cfg items
    for k,v in cfg_test.items():
        assert profile.data[k] == v


def test_eq():
    """Test Profile equality."""
    partition = 'Common'
    name = 'tcp'

    profile1 = Profile(
        **cfg_test
    )
    profile2 = Profile(
        **cfg_test
    )
    assert profile1
    assert profile2
    assert id(profile1) != id(profile2)
    assert profile1 == profile2

    # not equal
    profile2.data['context'] = 'serverside'
    assert profile1 != profile2

    # different objects
    assert profile1 != "profile1"


def test_uri_path(bigip):
    """Test Profile URI."""
    profile = Profile(
        **cfg_test
    )
    assert profile

    with pytest.raises(NotImplementedError):
        profile._uri_path(bigip)

def test_repr():
    """Test get repr."""
    profile = Profile(
        **cfg_test
    )
    assert profile

    assert (
        repr(profile) == "Profile('tcp', 'Common', context='all')")
