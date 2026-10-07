#!/usr/bin/env python3
"""Recompile only the CAD bridge against identity-pinned, previously built OCCT archives.

This deliberately uses generated Unix Makefiles' /fast targets, never the normal
dependency traversal (the OCCT object cache may have been reclaimed). A missing
or changed archive/recipe/toolchain fails closed; use a separately scheduled full
source build instead. Generated receipts and binaries remain in ignored artifacts.
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / ".artifacts/cad-kernel-20261006"
HOST = ROOT / ".artifacts/cad-kernel-host"
VENDOR = ROOT / "OtterFile/Vendor/OtterCADKernel"
CMAKE = ARTIFACT / "tools/cmake-3.31.10/cmake/data/bin/cmake"
BASELINE = ARTIFACT / "archive-reuse-baseline.json"
RELINK = ARTIFACT / "bridge-relink-receipt.json"
MAX_BYTES = 4 * 1024 * 1024 * 1024
TOOLKITS = ("TKDESTEP", "TKDEIGES", "TKMesh", "TKXSBase", "TKBool", "TKBO",
            "TKPrim", "TKShHealing", "TKTopAlgo", "TKGeomAlgo", "TKBRep",
            "TKGeomBase", "TKG3d", "TKG2d", "TKMath", "TKernel")
MUTABLE = {
    "OtterFile/Vendor/OtterCADKernel/Bridge/OtterCADKernel.cxx",
    "OtterFile/Vendor/OtterCADKernel/Bridge/include/OtterCADKernel.h",
    "Scripts/build-cad-kernel.sh", "Scripts/verify-cad-kernel-binaries.py",
    "Scripts/ensure-cad-kernel-xcframework.sh", "Scripts/relink-cad-kernel-bridge.py",
}


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def sha(path):
    require(path.is_file() and not path.is_symlink(), "Missing/nonregular pinned artifact: " + str(path))
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.STDOUT)


def budget():
    total = 0
    for directory in (ARTIFACT, HOST, VENDOR):
        if directory.is_dir():
            total += int(command("/usr/bin/du", "-sk", str(directory)).split()[0]) * 1024
    require(total <= MAX_BYTES, "CAD owned artifact/source/host budget exceeds 4 GiB")
    with (ARTIFACT / "bridge-relink-budget.log").open("a") as log:
        log.write(f"{datetime.datetime.now(datetime.timezone.utc).isoformat()} {total}/{MAX_BYTES}\n")
    return total


def pinned_files():
    files = {}
    for label, build in (("ios", ARTIFACT / "build-ios"), ("sim", ARTIFACT / "build-sim"),
                         ("host", HOST / "build/kernel")):
        for toolkit in TOOLKITS:
            path = build / ("lib" + toolkit + ".a")
            files[str(path.relative_to(ROOT))] = sha(path)
        for suffix in ("flags.make", "link.txt", "build.make"):
            path = build / "CMakeFiles/OtterCADKernel.dir" / suffix
            files[str(path.relative_to(ROOT))] = sha(path)
        path = build / "occt-include/Standard_Version.hxx"
        files[str(path.relative_to(ROOT))] = sha(path)
    return files


def live_toolchain():
    previous = json.loads((ARTIFACT / "verification.json").read_text())["build_fingerprint"]["toolchain"]
    require(previous["xcode"] == command("/usr/bin/xcodebuild", "-version").strip(), "Xcode changed")
    require(previous["clang"] == command("/usr/bin/xcrun", "clang++", "--version").strip(), "Compiler changed")
    require(previous["compiler_path"] == command("/usr/bin/xcrun", "--find", "clang++").strip(), "Compiler path changed")
    for sdk in ("iphoneos", "iphonesimulator"):
        sdk_path = command("/usr/bin/xcrun", "--sdk", sdk, "--show-sdk-path").strip()
        require(previous[sdk]["path"] == sdk_path, "SDK path changed")
        require(previous[sdk]["version"] == command("/usr/bin/xcrun", "--sdk", sdk, "--show-sdk-version").strip(), "SDK changed")
        require(previous[sdk]["settings_sha256"] == sha(pathlib.Path(sdk_path) / "SDKSettings.plist"), "SDK settings changed")
    return previous


def verify_baseline():
    require(BASELINE.is_file() and not BASELINE.is_symlink(), "Capture a verified archive baseline before editing the bridge")
    saved = json.loads(BASELINE.read_text())
    require(saved["status"] == "PASS", "Archive baseline is not PASS")
    require(saved["files"] == pinned_files(), "OCCT archive or generated bridge compile/link recipe changed")
    require(saved["toolchain"] == live_toolchain(), "Pinned archive toolchain drift")
    for path, expected in saved["immutable_source_files"].items():
        require(sha(ROOT / path) == expected, "Non-bridge source/recipe drift: " + path)
    command("/usr/bin/python3", str(ROOT / "Scripts/verify-cad-kernel-source.py"))
    return saved


def run_target(build, target, label):
    # /fast's generated rule has only the bridge object and existing archives.
    preview = command("/usr/bin/make", "-n", "-C", str(build), target)
    compile_lines = [line for line in preview.splitlines() if " -c " in line]
    require(all(str(VENDOR / "Bridge/OtterCADKernel.cxx") in line for line in compile_lines),
            "Fast target would compile an OCCT source; refusing dependency rebuild")
    require(len(compile_lines) <= 1, "Expected at most one bridge translation unit")
    log_path = ARTIFACT / ("bridge-relink-" + label + ".log")
    start = time.monotonic()
    with log_path.open("w") as log:
        log.write("Dry run:\n" + preview + "\nActual:\n")
        log.flush()
        process = subprocess.Popen([str(CMAKE), "--build", str(build), "--target", target,
                                    "--parallel", "1"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            while process.poll() is None:
                budget()
                time.sleep(1)
            require(process.returncode == 0, "Bridge-only build failed; inspect " + str(log_path))
        except BaseException:
            if process.poll() is None:
                os.killpg(process.pid, 15)
                process.wait()
            raise
    return {"target": target, "build": str(build.relative_to(ROOT)),
            "command": [str(CMAKE.relative_to(ROOT)), "--build", str(build.relative_to(ROOT)),
                        "--target", target, "--parallel", "1"],
            "seconds": round(time.monotonic() - start, 3),
            "log_sha256": sha(log_path), "translation_units": len(compile_lines)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-archive-baseline", action="store_true")
    parser.add_argument("--host-only", action="store_true")
    args = parser.parse_args()
    budget()
    require(sha(CMAKE) == "93f2fdbb4a671796a4660f51b1838e8a93ee903f8d345355440ce538fe187e0e", "Pinned CMake changed")
    if args.capture_archive_baseline:
        require(not BASELINE.exists(), "Baseline already exists; never overwrite provenance")
        verified = json.loads(command("/usr/bin/python3", str(ROOT / "Scripts/verify-cad-kernel-binaries.py"), "--check-receipt"))
        baseline = {"status": "PASS", "captured_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "basis": "previous shipping source/binary receipt PASS; exact existing source-built archives",
                    "previous_verification_sha256": sha(ARTIFACT / "verification.json"),
                    "previous_build_fingerprint": verified["build_fingerprint"]["sha256"],
                    "toolchain": verified["build_fingerprint"]["toolchain"],
                    "immutable_source_files": {key: value for key, value in verified["build_fingerprint"]["source_files"].items()
                                               if key not in MUTABLE},
                    "files": pinned_files()}
        BASELINE.write_text(json.dumps(baseline, indent=2) + "\n")
        print("CAD_ARCHIVE_BASELINE_PASS " + sha(BASELINE))
        return
    baseline = verify_baseline()
    if args.host_only:
        result = run_target(HOST / "build", "OtterCADKernel/fast", "host")
        print(json.dumps({"status": "PASS", "scope": "host bridge-only relink, not iOS", "build": result}))
        return
    # Device and simulator are intentionally sequential; at most one compiler.
    results = [run_target(ARTIFACT / "build-ios", "OtterCADKernel/fast", "ios"),
               run_target(ARTIFACT / "build-sim", "OtterCADKernel/fast", "sim")]
    verify_baseline()
    output = ARTIFACT / "OtterCADKernel.xcframework"
    previous = ARTIFACT / ("OtterCADKernel.previous-bridge-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ".xcframework")
    require(output.is_dir() and not output.is_symlink() and not previous.exists(), "Invalid XCFramework replacement scope")
    output.rename(previous)
    try:
        command("/usr/bin/xcodebuild", "-create-xcframework", "-framework", str(ARTIFACT / "build-ios/OtterCADKernel.framework"),
                "-framework", str(ARTIFACT / "build-sim/OtterCADKernel.framework"), "-output", str(output))
        receipt = {"status": "PASS", "built_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "scope": "two bridge translation units; unchanged identity-pinned OCCT archives reused",
                   "archive_baseline_sha256": sha(BASELINE), "previous_build_fingerprint": baseline["previous_build_fingerprint"],
                   "bridge_sha256": sha(VENDOR / "Bridge/OtterCADKernel.cxx"),
                   "relink_script_sha256": sha(pathlib.Path(__file__)), "builds": results,
                   "owned_disk_bytes": budget(),
                   "slices": {label: sha(ARTIFACT / ("build-" + label) / "OtterCADKernel.framework/OtterCADKernel")
                              for label in ("ios", "sim")}}
        RELINK.write_text(json.dumps(receipt, indent=2) + "\n")
        verified = command("/usr/bin/python3", str(ROOT / "Scripts/verify-cad-kernel-binaries.py"))
        pending = ARTIFACT / "verification.pending.json"
        pending.write_text(verified)
        pending.replace(ARTIFACT / "verification.json")
        command("/usr/bin/python3", str(ROOT / "Scripts/verify-cad-kernel-binaries.py"), "--check-receipt")
    except BaseException:
        # Preserve both the previous known-good output and any failed candidate.
        raise
    print("CAD_BRIDGE_RELINK_PASS " + sha(RELINK))


if __name__ == "__main__":
    main()
