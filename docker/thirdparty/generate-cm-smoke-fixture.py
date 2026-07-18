#!/usr/bin/env python3
"""Generate a deterministic AviUtl v0.1 logo for the CM runtime smoke test."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path


_FILE_HEADER = struct.Struct('>28sI')
_LOGO_HEADER = struct.Struct('<32s8h')
_LOGO_PIXEL = struct.Struct('<6h')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()

    width = 32
    height = 16
    content = bytearray(_FILE_HEADER.pack(b'<logo data file ver0.1>', 1))
    content.extend(_LOGO_HEADER.pack(
        b'KonomiTV CM smoke'.ljust(32, b'\0'),
        16,
        16,
        height,
        width,
        0,
        0,
        0,
        0,
    ))
    # Match the two drawboxes in verify.sh: a white rectangle with a black core.
    # AviUtl v0.1 stores full-range Y at 4-bit fixed-point scale; logoframe maps
    # it to the clip's limited range before detection.
    for y in range(height):
        for x in range(width):
            inner = 4 <= x < width - 4 and 4 <= y < height - 4
            alpha = 600 if inner else 750
            luma = 0 if inner else 256 << 4
            content.extend(_LOGO_PIXEL.pack(alpha, luma, alpha, 0, alpha, 0))
    args.output.write_bytes(content)


if __name__ == '__main__':
    main()
