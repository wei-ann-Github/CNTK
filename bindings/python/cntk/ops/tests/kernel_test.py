# Copyright (c) Microsoft. All rights reserved.

# Licensed under the MIT license. See LICENSE.md file in the project root
# for full license information.
# ==============================================================================

"""
Unit tests for kernel operations, tested for the forward and the backward pass
"""

import numpy as np
import pytest
from .ops_test_utils import unittest_helper, AA, I, precision, PRECISION_TO_TYPE, constant
from ...utils import sanitize_dtype_cntk

CONVOLUTION_OPERANDS = [
    ([[[5., 6.], # (1, 2, 2) map
       [3., 4.]]],
     [[[1., 2.], # (1, 2, 2) input operand
       [7., 8.]]]),
    ([[[1., 2.], # (3, 2, 2) map
       [3., 4.]],
      [[1., 2.],
       [3., 4.]],
      [[1., 2.],
       [3., 4.]]],
     [[[1., 2.], # (3, 2, 2) input operand
       [3., 4.]],
      [[5., 6.],
       [7., 8.]],
      [[9., 10.],
       [11., 12.]]])
]

@pytest.mark.parametrize("convolution_map, convolution_input", CONVOLUTION_OPERANDS)
def test_op_convolution_without_padding(convolution_map, convolution_input, device_id, precision):
    dt = PRECISION_TO_TYPE[precision]

    conv_map = AA(convolution_map, dtype=dt)
    conv_input = AA(convolution_input, dtype=dt)

    conv_input.shape = (1,1) + conv_input.shape # adding batch and channel axis
    conv_map.shape = (1,1) + conv_map.shape

    flipped_conv_map = conv_map[...,::-1,::-1]

    from scipy import signal
    expected_forward = AA([[signal.convolve(flipped_conv_map, conv_input, mode='valid')]])

    backward = AA([[conv_map]])

    a = I(shape=conv_input.shape,
        data_type=sanitize_dtype_cntk(precision),
        needs_gradient=True,
        name='a')

    constant_map = constant(value=conv_map)

    from cntk import convolution
    input_op = convolution(constant_map, a, auto_padding=[False])

    conv_input.shape = (1, 1) + conv_input.shape
    forward_input = {a: conv_input}
    expected_backward = {a: backward}

    unittest_helper(input_op,
                    forward_input, expected_forward, expected_backward,
                    device_id=device_id, precision=precision)

# ROI pooling test setup
# --- forward ---
# input convFeatureMap 3x3 map, values [[1,2,3][4,5,6][7,8,9]]
# input rois 4x1, values (x, y, w, h) = (1/3, 1/3, 2/3, 2/3)
# roiOutputShape 3 x 3
# expected output 3x3 map, values [[5,6,6][8,9,9][8,9,9]]
# --- backward ---
# gradient 3x3 map, values [[1,1,1][1,1,1][1,1,1]]
# expected output gradient 3x3 map, values [[0,0,0][0,1,2][0,2,4]]
ROIPOOLING_OPERANDS = [
    ([[[1., 2., 3.],       # (1, 3, 3) input operand (conv feature map)
       [4., 5., 6.],
       [7., 8., 9.]]],
     [.33, .33, .66, .66], # (4) input roi (x, y, w, h) relative to image width and height
     [[[5., 6., 6.],       # (1, 3, 3) expected forward output
       [8., 9., 9.],
       [8., 9., 9.]]],
     [[[0., 0., 0.],       # (1, 3, 3) expected backward output (gradient input is all 1s)
       [0., 1., 2.],
       [0., 2., 4.]]])
]

@pytest.mark.parametrize("input_map, input_rois, expected_fwd, expected_bkwd", ROIPOOLING_OPERANDS)
def test_op_roipooling(input_map, input_rois, expected_fwd, expected_bkwd, device_id, precision):
    dt = PRECISION_TO_TYPE[precision]

    # AA == as numpy array
    conv_input        = AA(input_map, dtype=dt)
    roi_input         = AA(input_rois, dtype=dt)
    exp_fwd_value     = AA(expected_fwd, dtype=dt)
    exp_bkwd_value    = AA(expected_bkwd, dtype=dt)
    
    # adding batch and sequence axis
    conv_input.shape     = (1,1) + conv_input.shape
    roi_input.shape      = (1,1) + roi_input.shape
    
    # adding batch, sequence and roi axis
    exp_fwd_value.shape  = (1,1,1) + exp_fwd_value.shape
    exp_bkwd_value.shape = (1,1,1,1) + exp_bkwd_value.shape

    # I == define cntk input variables
    a = I(shape=conv_input.shape,
        data_type=sanitize_dtype_cntk(precision),
        needs_gradient=True,
        name='a')

    b = I(shape=roi_input.shape,
        data_type=sanitize_dtype_cntk(precision),
        needs_gradient=False,
        name='b')

    from cntk import roipooling
    input_op = roipooling(a, b, (3,3))

    forward_input = {a: conv_input, b: roi_input}
    expected_backward = {a: exp_bkwd_value}

    unittest_helper(input_op,
                    forward_input, exp_fwd_value, expected_backward,
                    device_id=device_id, precision=precision)
