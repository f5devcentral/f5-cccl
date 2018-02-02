"""Provides functions for making jsonpatch positionally independent."""
# coding=utf-8
#
# Copyright 2018 F5 Networks Inc.
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


import hashlib
import json
import logging


LOGGER = logging.getLogger(__name__)


def convert_from_positional_patch(data, patch_obj):
    """Replace array indexes with unique ID (hash).

       Patches that refer to an array index must be modified so
       that they refer to the hash value of the content (whether it's
       a simple value or a complex dictionary).

       Patches are a list of dictionaries values with each value
       specifying a json path, an operation, and possibly a value.
       For example:
           {'path': '/c/0/value', 'value': 1, 'op': 'replace'}
       (other operations are 'add', 'remove', and 'move')

       Note:  This requires the content to be unique among array entries
              (seems to be the case for Big-IP objects)
    """

    LOGGER.debug("convert_from_positional_patch data: %s", data)
    if patch_obj is None:
        return
    patch = patch_obj.patch
    LOGGER.debug("convert_from_positional_patch indexed patch: %s", patch)

    for entry in patch:
        ptr = data
        new_path = ""
        for sub_path in entry['path'].split('/'):
            if not sub_path:
                # ignore the first subpath (before the leading slash)
                continue
            elif ptr is None:
                # continue to add path since we are done with substitutions
                new_path += '/'
                new_path += sub_path
            elif sub_path.isdigit():
                new_path += '/'
                ptr = ptr[int(sub_path)]
                str_content = json.dumps(ptr)
                new_path += \
                    '[{}]'.format(hashlib.sha256(bytes(
                        str_content.encode('utf-8'))).hexdigest())
            else:
                new_path += '/'
                new_path += sub_path
                if sub_path in ptr:
                    ptr = ptr[sub_path]
                else:
                    # done with substitutions, so just finish up remaining path
                    ptr = None
        entry['path'] = new_path
    LOGGER.debug("convert_from_positional_patch hashed patch: %s",
                 patch_obj.patch)


def convert_to_positional_patch(data,  # pylint: disable=too-many-branches
                                patch_obj):
    """Replace arrays indexed by a hash value with a positional index value.

       The index ID is the shasum hash value of the object.  If the ID isn't
       found remove the patch entry.

       Note: A limitation of this function is if the user managed to
             change the content of the hashed object, we would treat
             it as a uniquely different object. Fortunately, this
             doesn't seem possible with Big-IP gui.
    """

    LOGGER.debug("convert_to_positional_patch data: %s", data)
    if patch_obj is None:
        return
    patch = patch_obj.patch
    LOGGER.debug("convert_to_positional_patch hashed patch: %s", patch)

    entry_cnt = len(patch)
    entry_idx = 0
    while entry_idx < entry_cnt:
        entry = patch[entry_idx]
        ptr = data
        new_path = ""
        for sub_path in entry['path'].split('/'):
            if not sub_path:
                # ignore the first subpath (before the leading slash)
                continue
            elif ptr is None:
                # continue to add path since we are done with substitutions
                new_path += '/'
                new_path += sub_path
            elif sub_path[0] == '[' and sub_path[len(sub_path)-1] == ']':
                uuid = sub_path[1:-1]
                new_path += '/'
                for content_idx, content in enumerate(ptr):
                    str_content = json.dumps(content)
                    content_uuid = hashlib.sha256(bytes(
                        str_content.encode('utf-8'))).hexdigest()
                    if content_uuid == uuid:
                        new_path += str(content_idx)
                        ptr = ptr[content_idx]
                        break
                else:
                    # entry no longer exists so we can't remove it
                    new_path = None
                    break
            else:
                new_path += '/'
                new_path += sub_path
                if sub_path in ptr:
                    ptr = ptr[sub_path]
                else:
                    # done with substitutions so just finish up remaining path
                    ptr = None
                    if entry['op'] == 'remove':
                        # entry no longer exists so we must delete this patch
                        new_path = None
                        break
        if new_path:
            entry['path'] = new_path
            entry_idx += 1
        else:
            del patch[entry_idx]
            entry_cnt -= 1
    LOGGER.debug("convert_to_positional_patch indexed patch: %s",
                 patch_obj.patch)
