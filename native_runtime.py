"""Platform-aware loading for the research harness; no installer or downloads."""
from __future__ import annotations

import ctypes as C
import ctypes.util
import os
from pathlib import Path
import platform
import sys
import threading


class RuntimeDependencyError(RuntimeError):
    pass


def bridge_path(root, system=None):
    system = sys.platform if system is None else system
    if system == 'darwin':
        name = 'libdnf_native.dylib'
    elif system.startswith('linux'):
        name = 'libdnf_native.so'
    else:
        raise RuntimeDependencyError('Only Linux and macOS are supported by this research build.')
    return Path(root).resolve() / 'build' / name


def check_runtime_abi():
    if sys.version_info < (3, 10):
        raise RuntimeDependencyError('Python 3.10 or newer is required by the source annotations.')
    if C.sizeof(C.c_void_p) != 8 or C.sizeof(C.c_int) != 4 or sys.byteorder != 'little':
        raise RuntimeDependencyError('This SDL2 event binding requires a 64-bit little-endian process with 32-bit C int.')


def sdl_candidates(root, system=None, environ=None, finder=None):
    """Explicit override is authoritative; never fall back after its failure."""
    system = sys.platform if system is None else system
    environ = os.environ if environ is None else environ
    finder = ctypes.util.find_library if finder is None else finder
    override = environ.get('DNF_SDL2_LIBRARY')
    if override:
        return [os.path.expanduser(override)]
    root = Path(root).resolve()
    candidates = []
    if system == 'darwin':
        candidates += [
            str(root / 'vendor/SDL2.framework/SDL2'),
            str(root / 'vendor/libSDL2-2.0.0.dylib'),
            str(root / 'vendor/libSDL2.dylib'),
        ]
    elif system.startswith('linux'):
        candidates += [str(root / 'vendor/libSDL2-2.0.so.0')]
    else:
        raise RuntimeDependencyError('Only Linux and macOS are supported by this research build.')
    candidates += [finder('SDL2'), finder('SDL2-2.0')]
    if system == 'darwin':
        candidates += [
            str(Path.home() / 'Library/Frameworks/SDL2.framework/SDL2'),
            '/Library/Frameworks/SDL2.framework/SDL2',
            '/usr/local/lib/libSDL2.dylib',
            '/usr/local/lib/libSDL2-2.0.0.dylib',
            '/opt/homebrew/lib/libSDL2.dylib',
            'libSDL2.dylib', 'libSDL2-2.0.0.dylib',
        ]
    else:
        candidates += ['libSDL2-2.0.so.0', 'libSDL2.so']
    return list(dict.fromkeys(item for item in candidates if item))


class SDLVersion(C.Structure):
    _fields_ = [('major', C.c_uint8), ('minor', C.c_uint8), ('patch', C.c_uint8)]


def sdl_version(library):
    function = library.SDL_GetVersion
    function.argtypes = [C.POINTER(SDLVersion)]
    function.restype = None
    version = SDLVersion()
    function(C.byref(version))
    value = (version.major, version.minor, version.patch)
    if value[0] != 2:
        raise RuntimeDependencyError('SDL2 is required; SDL3 is not ABI-compatible with this binding.')
    return value


def load_sdl2(root, system=None, environ=None, finder=None, loader=None):
    loader = C.CDLL if loader is None else loader
    errors = []
    for candidate in sdl_candidates(root, system, environ, finder):
        try:
            library = loader(candidate)
            sdl_version(library)
            return library
        except (OSError, AttributeError, RuntimeDependencyError) as error:
            errors.append(f'{candidate}: {error}')
    raise RuntimeDependencyError(
        'Cannot load a compatible SDL2 runtime for '
        f'{platform.machine()} ({C.sizeof(C.c_void_p) * 8}-bit Python). '
        'Use an existing matching SDL2 library via DNF_SDL2_LIBRARY, or provision it separately. '
        'No installation was attempted.\n' + '\n'.join(errors)
    )


def load_bridge(root):
    path = bridge_path(root)
    try:
        return C.CDLL(str(path))
    except OSError as error:
        raise RuntimeDependencyError(
            f'Cannot load {path}. Build it on the target OS and architecture with sh build.sh. '
            'A Linux .so cannot be renamed into a macOS .dylib.\n' + str(error)
        ) from error


def initialize_sdl(library, flags, system=None):
    system = sys.platform if system is None else system
    if system == 'darwin' and threading.current_thread() is not threading.main_thread():
        raise RuntimeDependencyError('Initialize and run the macOS SDL event loop on the main thread.')
    ready = library.SDL_SetMainReady
    ready.argtypes = []
    ready.restype = None
    ready()
    initialize = library.SDL_Init
    initialize.argtypes = [C.c_uint32]
    initialize.restype = C.c_int
    return initialize(flags)
