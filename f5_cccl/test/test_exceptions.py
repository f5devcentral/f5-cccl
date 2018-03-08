#!/usr/bin/env python
# Copyright (c) 2017,2018, F5 Networks, Inc.
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


def test_raise_f5cccl_resource_create_error():
    """Test raising a F5CcclResourceCreateError."""
    with pytest.raises(exceptions.F5CcclResourceCreateError):
        def f():
            raise exceptions.F5CcclResourceCreateError()

        f()


def test_raise_f5cccl_resource_conflict_error():
    """Test raising a F5CcclConflictError."""
    with pytest.raises(exceptions.F5CcclResourceConflictError):
        def f():
            raise exceptions.F5CcclResourceConflictError()

        f()


def test_raise_f5cccl_resource_notfound_error():
    """Test raising a F5CcclResourceNotFoundError."""
    with pytest.raises(exceptions.F5CcclResourceNotFoundError):
        def f():
            raise exceptions.F5CcclResourceNotFoundError()

        f()


def test_raise_f5cccl_resource_request_error():
    """Test raising a F5CcclResourceRequestError."""
    with pytest.raises(exceptions.F5CcclResourceRequestError):
        def f():
            raise exceptions.F5CcclResourceRequestError()

        f()


def test_raise_f5cccl_resource_update_error():
    """Test raising a F5CcclResourceUpdateError."""
    with pytest.raises(exceptions.F5CcclResourceUpdateError):
        def f():
            raise exceptions.F5CcclResourceUpdateError()

        f()


def test_raise_f5cccl_resource_delete_error():
    """Test raising a F5CcclResourceDeleteError."""
    with pytest.raises(exceptions.F5CcclResourceDeleteError):
        def f():
            raise exceptions.F5CcclResourceDeleteError()

        f()


def test_raise_f5cccl_configuration_read_error():
    """Test raising a F5CcclConfigurationReadError."""
    with pytest.raises(exceptions.F5CcclConfigurationReadError):
        def f():
            raise exceptions.F5CcclConfigurationReadError()

        f()
