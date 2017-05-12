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

from f5.sdk_exception import F5SDKError
import f5_cccl.exceptions as cccl_exc
from f5_cccl.resource import Resource

from icontrol.exceptions import iControlUnexpectedHTTPError
from mock import MagicMock
import pytest


def resource_data():
    return {'name': "test_resource", 'partition': "Common"}


@pytest.fixture
def bigip():
    bigip = MagicMock()
    bigip.tm.ltm.subresources.subresource = MagicMock()

    return bigip


@pytest.fixture
def response():
    response = MagicMock()
    response.message = "Mock response"

    return response


class SubResource(Resource):

    def __init__(self, data):
        super(SubResource, self).__init__(data)

    def _uri_path(self, bigip):
        return bigip.tm.ltm.subresources.subresource


def test_create_resource_with_data():
    u"""Test Resource instantiation with data."""
    data = resource_data()
    name = data.get('name', "")
    partition = data.get('partition', "")

    res = Resource(data)

    assert res
    assert res.name == name
    assert res.partition == partition
    assert res.data


def test_create_resource_without_data():
    u"""Test Resource instantiation without data."""
    res = Resource(data={})

    assert res
    assert not res.name
    assert not res.partition
    assert not res.data


def test_get_uri_path(bigip):
    u"""Test _uri_path throws NotImplemented."""
    res = Resource(data={})

    with pytest.raises(NotImplementedError):
        res._uri_path(bigip)


def test_create_resource(bigip):
    u"""Test Resource creation."""
    data = resource_data()

    res = Resource(data)

    with pytest.raises(NotImplementedError):
        res.create(bigip)


def test_delete_resource(bigip):
    u"""Test Resource delete."""
    data = resource_data()

    res = Resource(data)

    with pytest.raises(NotImplementedError):
        res.delete(bigip)


def test_read_resource(bigip):
    u"""Test Resource read."""
    data = resource_data()

    res = Resource(data)

    with pytest.raises(NotImplementedError):
        res.read(bigip)


def test_update_resource(bigip):
    u"""Test Resource update."""
    data = resource_data()

    res = Resource(data)

    with pytest.raises(NotImplementedError):
        res.update(bigip)


def test_set_name():
    u"""Test Resource name update."""
    data = resource_data()

    res = Resource(data)

    with pytest.raises(AttributeError):
        res.name = "test_resource"


def test_set_partition():
    u"""Test Resource partition update."""
    data = resource_data()

    res = Resource(data)

    with pytest.raises(AttributeError):
        res.partition = "Common"


def test_set_data():
    u"""Test Resource data update."""
    data = resource_data()

    res = Resource(data)

    with pytest.raises(AttributeError):
        res.data = {}


def test_create_subresource(bigip):
    u"""Test that a subclass of Resource will execute 'create'."""
    data = resource_data()
    subres = SubResource(data)

    bigip.tm.ltm.subresources.subresource.create.return_value = (
        bigip.tm.ltm.subresources.subresource)

    obj = subres.create(bigip)

    assert obj == bigip.tm.ltm.subresources.subresource

    bigip.tm.ltm.subresources.subresource.create.assert_called()


def test_update_subresource(bigip):
    u"""Test that a subclass of Resource will execute 'update'."""
    data = resource_data()
    subres = SubResource(data)

    bigip.tm.ltm.subresources.subresource.modify.return_value = (None)
    bigip.tm.ltm.subresources.subresource.load.return_value = (
        bigip.tm.ltm.subresources.subresource.obj
    )
    obj = subres.update(bigip)

    assert not obj
    bigip.tm.ltm.subresources.subresource.load.assert_called()
    bigip.tm.ltm.subresources.subresource.obj.modify.assert_called()


def test_delete_subresource(bigip):
    u"""Test that a subclass of Resource will execute 'delete'."""
    data = resource_data()
    subres = SubResource(data)

    bigip.tm.ltm.subresources.subresource.load.return_value = (
        bigip.tm.ltm.subresources.subresource.obj
    )

    subres.delete(bigip)

    bigip.tm.ltm.subresources.subresource.load.assert_called()
    bigip.tm.ltm.subresources.subresource.obj.delete.assert_called()


def test_create_subresource_sdk_exception(bigip):
    u"""Test create can handle SDK exception."""
    data = resource_data()
    subres = SubResource(data)
    bigip.tm.ltm.subresources.subresource.create.side_effect = (
        [F5SDKError, None]
    )

    with pytest.raises(cccl_exc.F5CcclResourceCreateError):
        obj = subres.create(bigip)

        assert not obj


def test_create_subresource_icontrol_409_exception(bigip, response):
    u"""Test create can handle HTTP 409 exception."""
    data = resource_data()
    subres = SubResource(data)

    response.status_code = 409
    bigip.tm.ltm.subresources.subresource.create.side_effect = (
        [iControlUnexpectedHTTPError(response=response), None]
    )

    with pytest.raises(cccl_exc.F5CcclResourceConflictError):
        obj = subres.create(bigip)

        assert not obj


def test_create_subresource_icontrol_4XX_exception(bigip, response):
    u"""Test create can handle HTTP client exception."""
    data = resource_data()
    subres = SubResource(data)

    response.status_code = 400
    bigip.tm.ltm.subresources.subresource.create.side_effect = (
        [iControlUnexpectedHTTPError(response=response), None]
    )

    with pytest.raises(cccl_exc.F5CcclError):
        obj = subres.create(bigip)

        assert not obj


def test_create_subresource_icontrol_500_exception(bigip, response):
    u"""Test create can handle HTTP server exception."""
    data = resource_data()
    subres = SubResource(data)

    response.status_code = 500
    bigip.tm.ltm.subresources.subresource.create.side_effect = (
        [iControlUnexpectedHTTPError(response=response), None]
    )

    with pytest.raises(cccl_exc.F5CcclError):
        obj = subres.create(bigip)

        assert not obj


def test_update_subresource_sdk_exception(bigip):
    u"""Test update can handle SDK exception."""
    data = resource_data()
    subres = SubResource(data)

    bigip.tm.ltm.subresources.subresource.load.return_value = (
        bigip.tm.ltm.subresources.subresource
    )
    bigip.tm.ltm.subresources.subresource.modify.side_effect = (
        [F5SDKError, None]
    )

    with pytest.raises(cccl_exc.F5CcclResourceUpdateError):
        subres.update(bigip)


def test_update_subresource_icontrol_404_exception(bigip, response):
    u"""Test update can handle HTTP 404 not found exception.

    A NotFound error should occur when the resource load is performed.
    """
    data = resource_data()
    subres = SubResource(data)

    response.status_code = 404

    bigip.tm.ltm.subresources.subresource.load.side_effect = (
        [iControlUnexpectedHTTPError(response=response), None]
    )

    with pytest.raises(cccl_exc.F5CcclResourceNotFoundError):
        subres.update(bigip)

    bigip.tm.ltm.subresources.subresource.modify.assert_not_called()


def test_update_subresource_icontrol_4XX_exception(bigip, response):
    u"""Test update can handle gener HTTP client request exception."""
    data = resource_data()
    subres = SubResource(data)

    response.status_code = 400
    bigip.tm.ltm.subresources.subresource.load.return_value = (
        bigip.tm.ltm.subresources.subresource.obj
    )
    bigip.tm.ltm.subresources.subresource.obj.modify.side_effect = (
        [iControlUnexpectedHTTPError(response=response), None]
    )

    with pytest.raises(cccl_exc.F5CcclResourceRequestError):
        obj = subres.update(bigip)

        assert not obj


def test_delete_subresource_sdk_exception(bigip):
    u"""Test update can handle SDK exception."""
    data = resource_data()
    subres = SubResource(data)

    bigip.tm.ltm.subresources.subresource.load.return_value = (
        bigip.tm.ltm.subresources.subresource
    )
    bigip.tm.ltm.subresources.subresource.delete.side_effect = (
        [F5SDKError, None]
    )

    with pytest.raises(cccl_exc.F5CcclResourceDeleteError):
        subres.delete(bigip)


def test_delete_subresource_icontrol_404_exception(bigip, response):
    u"""Test delete can handle HTTP 404 not found exception.

    A NotFound error should occur when the resource load is performed.
    """
    data = resource_data()
    subres = SubResource(data)

    response.status_code = 404

    bigip.tm.ltm.subresources.subresource.load.side_effect = (
        [iControlUnexpectedHTTPError(response=response), None]
    )

    with pytest.raises(cccl_exc.F5CcclResourceNotFoundError):
        subres.delete(bigip)

    bigip.tm.ltm.subresources.subresource.delete.assert_not_called()


def test_delete_subresource_icontrol_4XX_exception(bigip, response):
    u"""Test delete can handle gener HTTP client request exception."""
    data = resource_data()
    subres = SubResource(data)

    response.status_code = 400
    bigip.tm.ltm.subresources.subresource.load.return_value = (
        bigip.tm.ltm.subresources.subresource
    )
    bigip.tm.ltm.subresources.subresource.delete.side_effect = (
        [iControlUnexpectedHTTPError(response=response), None]
    )

    with pytest.raises(cccl_exc.F5CcclResourceRequestError):
        obj = subres.delete(bigip)

        assert not obj
