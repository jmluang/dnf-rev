import ctypes as C
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import native_runtime as runtime


def fake_sdl(major=2):
    library = mock.Mock()
    def version(pointer):
        pointer._obj.major = major
        pointer._obj.minor = 30
        pointer._obj.patch = 0
    library.SDL_GetVersion.side_effect = version
    library.SDL_Init.return_value = 0
    return library


class NativeRuntimeTests(unittest.TestCase):
    def test_bridge_suffix_is_platform_specific(self):
        self.assertEqual(runtime.bridge_path(ROOT, 'darwin').name, 'libdnf_native.dylib')
        self.assertEqual(runtime.bridge_path(ROOT, 'linux').name, 'libdnf_native.so')

    def test_unsupported_platform_fails(self):
        with self.assertRaises(runtime.RuntimeDependencyError):
            runtime.bridge_path(ROOT, 'win32')

    def test_darwin_candidates_have_no_linux_fallback(self):
        candidates = runtime.sdl_candidates(ROOT, 'darwin', {}, lambda _: None)
        self.assertTrue(any('SDL2.framework/SDL2' in item for item in candidates))
        self.assertTrue(any(item.endswith('.dylib') for item in candidates))
        self.assertFalse(any('.so' in item for item in candidates))

    def test_linux_runtime_name_is_retained(self):
        candidates = runtime.sdl_candidates(ROOT, 'linux', {}, lambda _: None)
        self.assertIn('libSDL2-2.0.so.0', candidates)
        self.assertFalse(any('.dylib' in item for item in candidates))

    def test_find_library_result_is_used_and_deduplicated(self):
        candidates = runtime.sdl_candidates(ROOT, 'darwin', {}, lambda _: '/example/SDL2.dylib')
        self.assertEqual(candidates.count('/example/SDL2.dylib'), 1)

    def test_override_does_not_fall_back(self):
        loader = mock.Mock(side_effect=OSError('wrong architecture'))
        with self.assertRaisesRegex(runtime.RuntimeDependencyError, 'wrong architecture'):
            runtime.load_sdl2(ROOT, 'darwin', {'DNF_SDL2_LIBRARY': '/exact/libSDL2.dylib'}, lambda _: None, loader)
        loader.assert_called_once_with('/exact/libSDL2.dylib')

    def test_missing_candidates_are_skipped_before_valid_library(self):
        library = fake_sdl()
        loader = mock.Mock(side_effect=[OSError('missing'), library])
        result = runtime.load_sdl2(ROOT, 'darwin', {}, lambda _: None, loader)
        self.assertIs(result, library)
        self.assertEqual(loader.call_count, 2)

    def test_sdl3_is_rejected(self):
        with self.assertRaisesRegex(runtime.RuntimeDependencyError, 'SDL3'):
            runtime.sdl_version(fake_sdl(3))

    def test_main_ready_precedes_init(self):
        library = fake_sdl()
        self.assertEqual(runtime.initialize_sdl(library, 0x4020, 'darwin'), 0)
        self.assertEqual(library.mock_calls[-2:], [mock.call.SDL_SetMainReady(), mock.call.SDL_Init(0x4020)])

    def test_background_macos_init_is_rejected_before_native_call(self):
        library = fake_sdl()
        with mock.patch.object(runtime.threading, 'current_thread', return_value=object()):
            with self.assertRaisesRegex(runtime.RuntimeDependencyError, 'main thread'):
                runtime.initialize_sdl(library, 0x4020, 'darwin')
        library.SDL_Init.assert_not_called()
        library.SDL_SetMainReady.assert_not_called()

    def test_missing_bridge_is_actionable(self):
        with mock.patch.object(runtime.C, 'CDLL', side_effect=OSError('missing')):
            with self.assertRaisesRegex(runtime.RuntimeDependencyError, 'sh build.sh'):
                runtime.load_bridge(ROOT)

    def test_old_python_fails(self):
        with mock.patch.object(runtime.sys, 'version_info', (3, 9, 0)):
            with self.assertRaisesRegex(runtime.RuntimeDependencyError, '3.10'):
                runtime.check_runtime_abi()

    def test_incompatible_event_abi_fails(self):
        with mock.patch.object(runtime.C, 'sizeof', return_value=4):
            with self.assertRaisesRegex(runtime.RuntimeDependencyError, '64-bit'):
                runtime.check_runtime_abi()

    def test_current_abi_is_accepted(self):
        runtime.check_runtime_abi()
        self.assertEqual(C.sizeof(runtime.SDLVersion), 3)


if __name__ == '__main__':
    unittest.main()
