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

import pytest

from mock import Mock
from mock import patch


class TestLtmResource(object):
    """Creates a TestLtmResource Object
This object is useful in inheriting it within other, branching
Resource's sub-objects' testing.  This object uses built-in features that can
be used by any number of Resource objects for their testing.
    """
    @pytest.fixture
    def create_ltm_resource(self):
        """Useful for mocking f5_cccl.resource.Resource.__init__()
This test-class method is useful for mocking out the Resource parent object.
        """
        Resource = Mock()
        # future proofing:
        with patch('f5_cccl.resource.Resource.__init__', Resource,
                   create=True):
            self.create_child()
