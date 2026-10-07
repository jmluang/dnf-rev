"""Exercise the real SDL dummy viewer using only generated original color data."""
import ctypes as C
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
from generate_demo import demo_bytes
import native_viewer as viewer


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / 'shapes.NPK').write_bytes(demo_bytes())
        receipt = root / 'receipt.json'
        calls = {'poll': 0, 'textures_closed': 0, 'packs_closed': 0}
        destroy, close = viewer.DestroyTexture, viewer.Close

        def poll(pointer):
            calls['poll'] += 1
            if calls['poll'] != 3:
                return 0
            raw = bytearray(56)
            struct.pack_into('<I', raw, 0, 0x200)
            raw[12] = 14
            C.memmove(pointer, bytes(raw), len(raw))
            return 1

        def destroy_texture(handle):
            calls['textures_closed'] += 1
            destroy(handle)

        def close_pack(handle):
            calls['packs_closed'] += 1
            close(handle)

        with patch.object(sys, 'argv', ['native_viewer.py', '--samples', str(root), '--receipt', str(receipt)]), \
                patch.object(viewer, 'Poll', side_effect=poll), \
                patch.object(viewer, 'DestroyTexture', side_effect=destroy_texture), \
                patch.object(viewer, 'Close', side_effect=close_pack):
            viewer.main()
        data = json.loads(receipt.read_text())
        if data['frames_drawn'] != 3 or data.get('error') or calls['textures_closed'] != 1 or calls['packs_closed'] != 1:
            raise RuntimeError('synthetic native viewer result differed')
        print(json.dumps({'status': 'PASS', 'frames': data['frames_drawn'],
                          'textures_closed': calls['textures_closed'], 'packs_closed': calls['packs_closed'],
                          'input': 'generated color shapes only', 'video_backend': 'SDL2 dummy'}))


if __name__ == '__main__':
    main()
