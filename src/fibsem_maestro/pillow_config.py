# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""
Application-wide Pillow configuration.
"""

from PIL import Image

# Disable DecompressionBomb warnings and errors globally.
# FIB-SEM TIFFs are instrument-generated,
# not an untrusted-input threat model, so the protection
# this guards against is not a relevant risk here.
Image.MAX_IMAGE_PIXELS = None
