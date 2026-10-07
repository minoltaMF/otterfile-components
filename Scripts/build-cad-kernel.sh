#!/bin/bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
artifact_root="$project_root/.artifacts/cad-kernel-20261006"
vendor_root="$project_root/OtterFile/Vendor/OtterCADKernel"
cmake_cli="$artifact_root/tools/cmake-3.31.10/cmake/data/bin/cmake"
python_cli="${OTTER_CAD_PYTHON:-/usr/bin/python3}"
max_kib=4194304
clean_rebuild=false
if test "${1:-}" = --clean-rebuild; then
    clean_rebuild=true
elif test "$#" -ne 0; then
    printf '%s\n' 'Usage: Scripts/build-cad-kernel.sh [--clean-rebuild]' >&2
    exit 2
fi

check_budget() {
    local total_kib=0
    local current_kib
    local directory
    for directory in "$artifact_root" "$project_root/.artifacts/cad-kernel-host" "$vendor_root"; do
        if test -d "$directory"; then
            current_kib="$(du -sk "$directory" | awk '{print $1}')"
            total_kib=$((total_kib + current_kib))
        fi
    done
    printf 'CAD trial disk: %s KiB / %s KiB\n' "$total_kib" "$max_kib"
    test "$total_kib" -le "$max_kib"
}

# Only terminate the known build process tree when the trial disk limit fails.
stop_build_tree() {
    local parent_pid="$1"
    local child_pid
    for child_pid in $(pgrep -P "$parent_pid" 2>/dev/null || true); do
        stop_build_tree "$child_pid"
    done
    kill -TERM "$parent_pid" 2>/dev/null || true
}

"$python_cli" "$project_root/Scripts/verify-cad-kernel-source.py"
mkdir -p "$artifact_root/downloads" "$artifact_root/tools"
if ! test -x "$cmake_cli"; then
    wheel="$artifact_root/downloads/cmake-3.31.10-py3-none-macosx_10_10_universal2.whl"
    if ! test -f "$wheel"; then
        curl -fL --max-filesize 48001731 --max-time 180 -o "$wheel" \
            https://files.pythonhosted.org/packages/99/3b/6ed408a99709808df4014bead522e075f0e8d1100e6d886eb5bc30fee04e/cmake-3.31.10-py3-none-macosx_10_10_universal2.whl
    fi
    wheel_sha="$(shasum -a 256 "$wheel" | awk '{print $1}')"
    test "$wheel_sha" = ad697643a00d9ba85179590a383c4f7401169b55ebf4b8b2938daf28c6bdeb6d
    test "$(wc -c < "$wheel" | tr -d ' ')" -eq 48001731
    unzip -q "$wheel" -d "$artifact_root/tools/cmake-3.31.10"
fi
test "$(shasum -a 256 "$cmake_cli" | awk '{print $1}')" = \
    93f2fdbb4a671796a4660f51b1838e8a93ee903f8d345355440ce538fe187e0e
"$cmake_cli" --version
check_budget

build_slice() {
    local slice="$1"
    local sdk="$2"
    local build="$artifact_root/build-$slice"
    test ! -L "$build"
    local configure_arguments=(-S "$vendor_root" -B "$build" -G "Unix Makefiles"
        -DCMAKE_BUILD_TYPE=Release -DCMAKE_SYSTEM_NAME=iOS
        "-DCMAKE_C_COMPILER=$(xcrun --find cc)" "-DCMAKE_CXX_COMPILER=$(xcrun --find c++)"
        -DCMAKE_C_FLAGS= -DCMAKE_CXX_FLAGS= -DCMAKE_SHARED_LINKER_FLAGS=
        "-DCMAKE_OSX_SYSROOT=$sdk" -DCMAKE_OSX_ARCHITECTURES=arm64
        -DCMAKE_OSX_DEPLOYMENT_TARGET=17.0)
    if "$clean_rebuild"; then
        configure_arguments=(--fresh "${configure_arguments[@]}")
    fi
    "$cmake_cli" "${configure_arguments[@]}"
    "$cmake_cli" --build "$build" --target OtterCADKernel --parallel 4 \
        > "$artifact_root/build-$slice.log" 2>&1 &
    local build_pid=$!
    while kill -0 "$build_pid" 2>/dev/null; do
        if ! check_budget; then
            stop_build_tree "$build_pid"
            wait "$build_pid" || true
            printf '%s\n' 'CAD build stopped: 4 GiB trial budget exceeded.' >&2
            return 1
        fi
        sleep 15
    done
    wait "$build_pid"
    local framework="$build/OtterCADKernel.framework"
    /usr/bin/otool -L "$framework/OtterCADKernel"
    /usr/bin/xcrun vtool -show-build "$framework/OtterCADKernel"
    shasum -a 256 "$framework/OtterCADKernel"
    check_budget
}

build_slice ios iphoneos
build_slice sim iphonesimulator
output="$artifact_root/OtterCADKernel.xcframework"
if test -d "$output"; then
    mv "$output" "$artifact_root/OtterCADKernel.previous-$(date +%Y%m%d%H%M%S).xcframework"
fi
xcodebuild -create-xcframework \
    -framework "$artifact_root/build-ios/OtterCADKernel.framework" \
    -framework "$artifact_root/build-sim/OtterCADKernel.framework" \
    -output "$output"
"$python_cli" "$project_root/Scripts/verify-cad-kernel-binaries.py" --full-source-build > "$artifact_root/verification.pending.json"
mv "$artifact_root/verification.pending.json" "$artifact_root/verification.json"
check_budget
printf 'CAD kernel ready: %s\n' "$output"
