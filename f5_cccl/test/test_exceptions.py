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

from f5_cccl import exceptions
import pytest


def test_create_f5ccclerror_nomsg():
    """Test the creation of F5CcclError without message."""
    e = exceptions.F5CcclError()

    assert e
    assert not e.msg
    assert "{}".format(e) == "F5CcclError"


def test_create_f5ccclerror_msg():
    """Test the creation of F5CcclError with message."""
    error_msg = "Test CCCL Error"
    e = exceptions.F5CcclError(error_msg)

    assert e
    assert e.msg == error_msg
    assert "{}".format(e) == "F5CcclError - Test CCCL Error"


def test_raise_f5ccclerror():
    """Test raising a F5CcclError."""
    with pytest.raises(exceptions.F5CcclError):
        def f():
            raise exceptions.F5CcclError()

        f()
