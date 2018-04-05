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


import jsonpatch

import f5_cccl.utils.json_pos_patch as pospatch

from f5_cccl.utils.resource_merge import merge

#
# These tests verify that JSON patches can be converted to a positionally
# independent patch and then reverted back again, assuming the original
# data has not changed (if so, the patches should be trimmed)
#
def test_json_simple_property():
    """ Test simple dict """

    dataIn = {
        'a': 1,
        'b': 2,
        'c': 3
    }
    dataOut1 = {
        'a': 1,
        'b': 2,
        'c': 3
    }
    dataOut2 = {
        'c': 3,
        'b': 2,
        'a': 1
    }
    dataOut3 = {
        'a': 1,
        'b': 2
    }
    dataOut4 = {
        'b': 2
    }
    dataOut5 = {
    }

    patch_strIn = '[{"path": "/a", "op": "remove"}]'
    patch_strOutPropExists = '[{"path": "/a", "op": "remove"}]'
    patch_strOutPropNotExists = '[]'

    patch = jsonpatch.JsonPatch.from_string(patch_strIn)
    expected_patch = jsonpatch.JsonPatch.from_string(patch_strOutPropExists)
    pospatch.convert_from_positional_patch(dataIn, patch)
    pospatch.convert_to_positional_patch(dataOut1, patch)
    assert patch == expected_patch

    patch = jsonpatch.JsonPatch.from_string(patch_strIn)
    expected_patch = jsonpatch.JsonPatch.from_string(patch_strOutPropExists)
    pospatch.convert_from_positional_patch(dataIn, patch)
    pospatch.convert_to_positional_patch(dataOut2, patch)
    assert patch == expected_patch

    patch = jsonpatch.JsonPatch.from_string(patch_strIn)
    expected_patch = jsonpatch.JsonPatch.from_string(patch_strOutPropExists)
    pospatch.convert_from_positional_patch(dataIn, patch)
    pospatch.convert_to_positional_patch(dataOut3, patch)
    assert patch == expected_patch

    patch = jsonpatch.JsonPatch.from_string(patch_strIn)
    expected_patch = jsonpatch.JsonPatch.from_string(patch_strOutPropNotExists)
    pospatch.convert_from_positional_patch(dataIn, patch)
    pospatch.convert_to_positional_patch(dataOut4, patch)
    assert patch == expected_patch

    patch = jsonpatch.JsonPatch.from_string(patch_strIn)
    expected_patch = jsonpatch.JsonPatch.from_string(patch_strOutPropNotExists)
    pospatch.convert_from_positional_patch(dataIn, patch)
    pospatch.convert_to_positional_patch(dataOut5, patch)
    assert patch == expected_patch


def test_json_simple_array():
    """ Test simple arrays """

    dataIn = {
        'rules': [
            'A',
            'B',
        ],
    }
    dataOut1 = {
        'rules': [
            'A',
            'B',
        ],
    }
    dataOut2 = {
        'rules': [
            'B',
            'A',
        ],
    }
    dataOut3 = {
        'rules': [
            'A',
        ],
    }
    dataOut4 = {
        'rules': [
            'B',
        ],
    }

    patch_strIn = '[{"path": "/rules/1", "op": "remove"}]'
    patch_strOut1 = '[{"path": "/rules/1", "op": "remove"}]'
    patch_strOut2 = '[{"path": "/rules/0", "op": "remove"}]'
    patch_strOut3 = '[]'
    patch_strOut4 = '[{"path": "/rules/0", "op": "remove"}]'

    patch = jsonpatch.JsonPatch.from_string(patch_strIn)
    expected_patch = jsonpatch.JsonPatch.from_string(patch_strOut1)
    pospatch.convert_from_positional_patch(dataIn, patch)
    pospatch.convert_to_positional_patch(dataOut1, patch)
    assert patch == expected_patch

    # Test that if the order is switched (user rearranges the
    # order on the Big-IP), the patching still works correctly
    patch = jsonpatch.JsonPatch.from_string(patch_strIn)
    expected_patch = jsonpatch.JsonPatch.from_string(patch_strOut2)
    pospatch.convert_from_positional_patch(dataIn, patch)
    pospatch.convert_to_positional_patch(dataOut2, patch)
    assert patch == expected_patch

    # Test if the patched entry is deleted (e.g. user deleted a
    # rule/policy on the Big-IP)
    patch = jsonpatch.JsonPatch.from_string(patch_strIn)
    expected_patch = jsonpatch.JsonPatch.from_string(patch_strOut3)
    pospatch.convert_from_positional_patch(dataIn, patch)
    pospatch.convert_to_positional_patch(dataOut3, patch)
    assert patch == expected_patch

    # Test if another entry is deleted (e.g. user deleted a
    # rule/policy on the Big-IP)
    patch = jsonpatch.JsonPatch.from_string(patch_strIn)
    expected_patch = jsonpatch.JsonPatch.from_string(patch_strOut4)
    pospatch.convert_from_positional_patch(dataIn, patch)
    pospatch.convert_to_positional_patch(dataOut4, patch)
    assert patch == expected_patch


def test_json_compound_array():
    """ Test arrays of dictionaries """

    dataIn = {
        'profiles': [
            {
                'partition': 'Common',
                'name': 'http',
                'context': 'all'
            },
            {
                'partition': 'Common',
                'name': 'tcp',
                'context': 'all'
            }
        ],
    }
    dataOut1 = {
        'profiles': [
            {
                'partition': 'Common',
                'name': 'http',
                'context': 'all'
            },
            {
                'partition': 'Common',
                'name': 'tcp',
                'context': 'all'
            }
        ]
    }
    dataOut2 = {
        'profiles': [
            {
                'partition': 'Common',
                'name': 'tcp',
                'context': 'all'
            }
        ]
    }
    dataOut3 = {
        'profiles': [
            {
                'partition': 'Common',
                'name': 'http',
                'context': 'all'
            },
            {
                'partition': 'Common',
                'name': 'tcp',
            }
        ]
    }
    dataOut4 = {
        'profiles': [
            {
                'partition': 'Common',
                'name': 'http',
                'context': 'all'
            }
        ]
    }

    patch_strIn = \
        '[{"path": "/profiles/1/context", "value": "none", "op": "replace"}]'
    patch_strOut1 = \
        '[{"path": "/profiles/1/context", "value": "none", "op": "replace"}]'
    patch_strOut2 = \
        '[{"path": "/profiles/0/context", "value": "none", "op": "replace"}]'
    patch_strOut3 = \
        '[]'
    patch_strOut4 = '[]'

    patch = jsonpatch.JsonPatch.from_string(patch_strIn)
    expected_patch = jsonpatch.JsonPatch.from_string(patch_strOut1)
    pospatch.convert_from_positional_patch(dataIn, patch)
    pospatch.convert_to_positional_patch(dataOut1, patch)
    assert patch == expected_patch

    patch = jsonpatch.JsonPatch.from_string(patch_strIn)
    expected_patch = jsonpatch.JsonPatch.from_string(patch_strOut2)
    pospatch.convert_from_positional_patch(dataIn, patch)
    pospatch.convert_to_positional_patch(dataOut2, patch)
    assert patch == expected_patch

    # if an array entry is modified by user, we must treat it as a new
    # entry and will not attempt to patch it (fortunately, this does not
    # seem possible on the Big-IP).
    patch = jsonpatch.JsonPatch.from_string(patch_strIn)
    expected_patch = jsonpatch.JsonPatch.from_string(patch_strOut3)
    pospatch.convert_from_positional_patch(dataIn, patch)
    pospatch.convert_to_positional_patch(dataOut3, patch)
    assert patch == expected_patch

    patch = jsonpatch.JsonPatch.from_string(patch_strIn)
    expected_patch = jsonpatch.JsonPatch.from_string(patch_strOut4)
    pospatch.convert_from_positional_patch(dataIn, patch)
    pospatch.convert_to_positional_patch(dataOut4, patch)
    assert patch == expected_patch
