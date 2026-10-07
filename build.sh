#!/bin/sh
# Source build only. Does not download, install, or execute the Windows client.
set -eu
cd "$(dirname "$0")"
system=$(uname -s)
case "$system" in
 Darwin)
  # xcrun locates the selected Apple compiler and SDK. Full Xcode is optional.
  if ! command -v xcrun >/dev/null 2>&1; then
   printf '%s\n' 'Apple developer tools are unavailable; no build was attempted.' >&2
   exit 2
  fi
  sdk=$(xcrun --sdk macosx --show-sdk-path)
  compiler=${CXX:-$(xcrun --sdk macosx --find clang++)}
  [ -d "$sdk" ] || { printf '%s\n' 'The selected macOS SDK is missing.' >&2; exit 2; }
  arch=${DNF_MACOS_ARCH:-x86_64}
  case "$arch" in x86_64|arm64) ;; *) printf '%s\n' 'DNF_MACOS_ARCH must be x86_64 or arm64.' >&2; exit 2;; esac
  target=${MACOSX_DEPLOYMENT_TARGET:-15.0}
  compile() { "$compiler" -std=c++17 -O2 -Wall -Wextra -Wpedantic -Werror -stdlib=libc++ -isysroot "$sdk" -arch "$arch" "-mmacosx-version-min=$target" "$@"; }
  ;;
 Linux)
  compiler=${CXX:-c++}
  compile() { "$compiler" -std=c++17 -O2 -Wall -Wextra -Wpedantic -Werror "$@"; }
  ;;
 *) printf '%s\n' 'This research build supports Linux and macOS only.' >&2; exit 2;;
esac
mkdir -p build
compile src/npk_preview.cpp -lz -o build/npk_preview
case "$system" in
 Darwin) compile -fPIC -dynamiclib src/native_bridge.cpp -lz -Wl,-install_name,@rpath/libdnf_native.dylib -o build/libdnf_native.dylib;;
 Linux) compile -fPIC -shared src/native_bridge.cpp -lz -o build/libdnf_native.so;;
esac
compile -I src tests/test_input_state.cpp -o build/test_input_state
compile -I src tests/presentation_quad_test.cpp -o build/presentation_quad_test
# Cross-architecture builds are allowed, but must never execute through emulation.
if [ "$system" != Darwin ] || [ "$arch" = "$(uname -m)" ]; then
 ./build/test_input_state
 ./build/presentation_quad_test
else
 printf '%s\n' 'Cross-architecture output built; native C++ tests must run on the target architecture.'
fi
