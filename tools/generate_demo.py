#!/usr/bin/env python3
"""Generate an original colored-shape fixture; contains no game artwork."""
import argparse
from pathlib import Path
import struct
import zlib


def demo_bytes():
    records, payloads = [], []
    for frame in range(3):
        pixels = bytearray()
        for y in range(32):
            for x in range(32):
                inside = 4 + frame * 3 <= x < 22 + frame * 3 and 4 <= y < 28
                red, green, blue, alpha = ((80 + frame * 65, 210 - frame * 35, 160, 255)
                                            if inside else (0, 0, 0, 0))
                pixels += bytes((blue, green, red, alpha))
        payload = zlib.compress(pixels)
        records.append(struct.pack('<9I', 16, 6, 32, 32, len(payload), 16, 16, 64, 64))
        payloads.append(payload)
    index = b''.join(records)
    image = b'Neople Img File\0' + struct.pack('<4I', len(index), 0, 2, 3) + index + b''.join(payloads)
    return b'NeoplePack_Bill\0' + struct.pack('<I', 1) + struct.pack('<II', 284, len(image)) + bytes(256) + image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='A new file, for example artifacts/demo/shapes.NPK')
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as stream:
        stream.write(demo_bytes())
    print(str(args.output))


if __name__ == '__main__':
    main()
