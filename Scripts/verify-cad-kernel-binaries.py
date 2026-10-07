#!/usr/bin/env python3
"""Inspect only the rebuilt project-local iOS CAD slices, not user CAD files."""
import datetime
import argparse
import hashlib
import json
import pathlib
import plistlib
import re
import subprocess

root = pathlib.Path(__file__).resolve().parents[1]
artifact = root / ".artifacts/cad-kernel-20261006"
vendor = root / "OtterFile/Vendor/OtterCADKernel"
xcframework = artifact / "OtterCADKernel.xcframework"

def require(condition, message):
    if not condition:
        raise SystemExit(message)

def command(*arguments):
    return subprocess.check_output(arguments, text=True, stderr=subprocess.STDOUT)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def sdk_framework_metadata(sdk, sdk_path):
    sdk_root = pathlib.Path(sdk_path)
    settings = plistlib.loads((sdk_root / "SDKSettings.plist").read_bytes())
    platform_root = sdk_root.parents[2]
    platform = plistlib.loads((platform_root / "Info.plist").read_bytes())
    platform_version = plistlib.loads((platform_root / "version.plist").read_bytes())
    developer = pathlib.Path(command("/usr/bin/xcode-select", "--print-path").strip())
    xcode = plistlib.loads((developer.parent / "version.plist").read_bytes())
    version = [int(part) for part in xcode["CFBundleShortVersionString"].split(".")]
    require(len(version) in (2, 3), "Unknown Xcode metadata version")
    xcode_actual = version[0] * 100 + version[1] * 10 + (version[2] if len(version) == 3 else 0)
    families = [int(item["Identifier"]) for item in settings["SupportedTargets"][sdk]["DeviceFamilies"]]
    require(families == [1, 2], "Unexpected SDK device families")
    return {"DTPlatformVersion": platform["Version"],
            "DTPlatformBuild": platform_version["ProductBuildVersion"],
            "DTSDKName": settings["CanonicalName"],
            "DTSDKBuild": command("/usr/bin/xcrun", "--sdk", sdk, "--show-sdk-build-version").strip(),
            "DTXcode": str(xcode_actual).zfill(4), "DTXcodeBuild": xcode["ProductBuildVersion"],
            "DTCompiler": settings["DefaultProperties"]["DEFAULT_COMPILER"],
            "BuildMachineOSBuild": command("/usr/bin/sw_vers", "-buildVersion").strip(),
            "UIDeviceFamily": families}

def expected_framework_info(variant, build_metadata):
    require(variant in ("device", "simulator"), "Unexpected framework Info platform")
    info = {
        "CFBundleDevelopmentRegion": "en", "CFBundleExecutable": "OtterCADKernel",
        "CFBundleIdentifier": "com.otterfile.cadkernel", "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": "OtterCADKernel", "CFBundlePackageType": "FMWK",
        "CFBundleShortVersionString": "7.9.3", "CFBundleVersion": "7.9.3",
        "CFBundleSupportedPlatforms": ["iPhoneOS" if variant == "device" else "iPhoneSimulator"],
        "DTPlatformName": "iphoneos" if variant == "device" else "iphonesimulator",
        "MinimumOSVersion": "17.0",
    }
    info.update(build_metadata)
    return info

def validate_framework_info(info, variant, build_metadata):
    require(info == expected_framework_info(variant, build_metadata),
            "Incomplete or unexpected iOS framework Info.plist: " + variant)
    require(re.fullmatch(r"[1-9][0-9]{0,3}\.[0-9]{1,2}\.[0-9]{1,2}", info["CFBundleVersion"]),
            "Invalid framework bundle version")

parser = argparse.ArgumentParser()
parser.add_argument("--check-receipt", action="store_true")
parser.add_argument("--self-test-metadata", action="store_true")
parser.add_argument("--full-source-build", action="store_true",
                    help="Record a scheduled full build rather than an archive-reuse relink")
arguments = parser.parse_args()
if arguments.self_test_metadata:
    cases = 0
    controlled_build = {"DTPlatformVersion": "27.0", "DTPlatformBuild": "ControlledSDK",
                        "DTSDKName": "controlled-sdk", "DTSDKBuild": "ControlledSDK",
                        "DTXcode": "2700", "DTXcodeBuild": "ControlledXcode",
                        "DTCompiler": "com.apple.compilers.llvm.clang.1_0",
                        "BuildMachineOSBuild": "ControlledHost", "UIDeviceFamily": [1, 2]}
    for variant in ("device", "simulator"):
        valid = expected_framework_info(variant, controlled_build)
        validate_framework_info(plistlib.loads(plistlib.dumps(valid)), variant, controlled_build)
        cases += 1
        invalid = []
        for key in valid:
            missing = dict(valid)
            del missing[key]
            invalid.append(missing)
            empty = dict(valid)
            empty[key] = ""
            invalid.append(empty)
        invalid.append(expected_framework_info("simulator" if variant == "device" else "device", controlled_build))
        for key, value in (("CFBundlePackageType", "BNDL"), ("CFBundleExecutable", "OtherKernel"),
                           ("CFBundleVersion", "invalid"), ("MinimumOSVersion", "27.0")):
            malformed = dict(valid)
            malformed[key] = value
            invalid.append(malformed)
        for info in invalid:
            try:
                validate_framework_info(info, variant, controlled_build)
            except SystemExit:
                cases += 1
            else:
                raise SystemExit("Framework metadata gate accepted an invalid fixture")
    print(json.dumps({"status": "PASS", "metadata_cases": cases,
                      "scope": "controlled plist gate cases, not installation"}))
    raise SystemExit(0)
source_paths = [
    "OtterFile/Vendor/OtterCADKernel/Bridge/OtterCADKernel.cxx",
    "OtterFile/Vendor/OtterCADKernel/Bridge/include/OtterCADKernel.h",
    "OtterFile/Vendor/OtterCADKernel/Bridge/include/module.modulemap",
    "OtterFile/Vendor/OtterCADKernel/Bridge/exports.txt",
    "OtterFile/Vendor/OtterCADKernel/Bridge/Info.plist.in",
    "OtterFile/Vendor/OtterCADKernel/Bridge/PackageFramework.cmake",
    "OtterFile/Vendor/OtterCADKernel/CMakeLists.txt",
    "OtterFile/Vendor/OtterCADKernel/FrameworkMetadata.cmake",
    "OtterFile/Vendor/OtterCADKernel/SourceClosure.cmake",
    "OtterFile/Vendor/OtterCADKernel/SOURCE-MANIFEST.json",
    "OtterFile/Vendor/OtterCADKernel/SOURCE.json",
    "OtterFile/Vendor/OtterCADKernel/BUILD-TOOLS.json",
    "OtterFile/Vendor/OtterCADKernel/OCCT/LICENSE_LGPL_21.txt",
    "OtterFile/Vendor/OtterCADKernel/OCCT/OCCT_LGPL_EXCEPTION.txt",
    "OtterFile/Vendor/OtterCADKernel/NOTICE.txt",
    "Scripts/build-cad-kernel.sh", "Scripts/vendor-cad-kernel-source.py",
    "Scripts/verify-cad-kernel-source.py", "Scripts/verify-cad-kernel-binaries.py",
    "Scripts/ensure-cad-kernel-xcframework.sh",
    "Scripts/relink-cad-kernel-bridge.py",
]
toolchain = {"xcode": command("/usr/bin/xcodebuild", "-version").strip(),
             "clang": command("/usr/bin/xcrun", "clang++", "--version").strip(),
             "compiler_path": command("/usr/bin/xcrun", "--find", "clang++").strip()}
for sdk in ("iphoneos", "iphonesimulator"):
    sdk_path = command("/usr/bin/xcrun", "--sdk", sdk, "--show-sdk-path").strip()
    toolchain[sdk] = {"path": sdk_path,
                      "version": command("/usr/bin/xcrun", "--sdk", sdk, "--show-sdk-version").strip(),
                      "settings_sha256": digest(pathlib.Path(sdk_path) / "SDKSettings.plist"),
                      "framework_build_metadata": sdk_framework_metadata(sdk, sdk_path)}
fingerprint = {"source_files": {path: digest(root / path) for path in source_paths}, "toolchain": toolchain}
fingerprint["sha256"] = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()

require(xcframework.is_dir() and not xcframework.is_symlink(), "Missing local CAD XCFramework")
metadata = plistlib.loads((xcframework / "Info.plist").read_bytes())
require(metadata.get("CFBundlePackageType") == "XFWK", "Unexpected XCFramework package type")
require(metadata.get("XCFrameworkFormatVersion") == "1.0", "Unexpected XCFramework format version")
xcframework_info_sha = digest(xcframework / "Info.plist")
libraries = metadata.get("AvailableLibraries", [])
require(len(libraries) == 2, "Expected exactly the iOS device and Simulator slices")
expected_exports = {"_otter_cad_read_mesh", "_otter_cad_mesh_view",
                    "_otter_cad_mesh_release", "_otter_cad_kernel_version"}
seen = set()
receipts = []
for library in libraries:
    identifier = library["LibraryIdentifier"]
    require("/" not in identifier and ".." not in identifier, "Unexpected slice identifier")
    require(library["SupportedPlatform"] == "ios", "Unexpected shipping platform")
    require(library["SupportedArchitectures"] == ["arm64"], "Unexpected shipping architecture")
    variant = library.get("SupportedPlatformVariant", "device")
    require(variant in ("device", "simulator") and variant not in seen, "Duplicate or unexpected slice")
    seen.add(variant)
    require(library["LibraryPath"] == "OtterCADKernel.framework", "Unexpected CAD bundle path")
    framework = xcframework / identifier / library["LibraryPath"]
    info_path = framework / "Info.plist"
    require(info_path.is_file() and not info_path.is_symlink(), "Missing framework Info.plist")
    info = plistlib.loads(info_path.read_bytes())
    require(info_path.read_bytes().startswith(b"bplist00"), "Shipping framework Info is not normalized binary plist")
    sdk = "iphoneos" if variant == "device" else "iphonesimulator"
    validate_framework_info(info, variant, toolchain[sdk]["framework_build_metadata"])
    binary = framework / "OtterCADKernel"
    require(binary.is_file() and not binary.is_symlink(), "Missing slice binary")
    require(command("/usr/bin/lipo", "-archs", str(binary)).strip() == "arm64", "Invalid Mach-O architecture")
    load_commands = command("/usr/bin/xcrun", "vtool", "-show-build", str(binary))
    expected_platform = "IOS" if variant == "device" else "IOSSIMULATOR"
    require(re.search(r"platform\s+" + expected_platform + r"\s", load_commands), "Wrong LC_BUILD_VERSION platform")
    require(re.search(r"minos\s+17\.0\s", load_commands), "Wrong minimum iOS deployment target")
    dependencies = [line.strip().split(" (", 1)[0]
                    for line in command("/usr/bin/otool", "-L", str(binary)).splitlines()[1:]]
    require(dependencies == ["@rpath/OtterCADKernel.framework/OtterCADKernel",
                             "/usr/lib/libc++.1.dylib", "/usr/lib/libSystem.B.dylib"],
            "Unexpected runtime dependency or non-rpath library identity")
    exports = {line.split()[-1] for line in command("/usr/bin/nm", "-gU", str(binary)).splitlines() if line.strip()}
    require(exports == expected_exports, "Unexpected public CAD symbols")
    require(digest(framework / "Headers/OtterCADKernel.h") == digest(vendor / "Bridge/include/OtterCADKernel.h"),
            "Framework public header mismatch")
    require(digest(framework / "Modules/module.modulemap") == digest(vendor / "Bridge/include/module.modulemap"),
            "Framework module map mismatch")
    require(not (framework / "Resources").exists() and not (framework / "Resources").is_symlink(),
            "iOS CAD framework must be flat; legacy Resources layout failed real installation")
    license_receipts = {}
    for source in [vendor / "OCCT/LICENSE_LGPL_21.txt", vendor / "OCCT/OCCT_LGPL_EXCEPTION.txt", vendor / "NOTICE.txt"]:
        require((framework / source.name).is_file() and not (framework / source.name).is_symlink(),
                "Missing flat framework license/NOTICE")
        require(digest(framework / source.name) == digest(source), "Framework license/NOTICE mismatch")
        license_receipts[source.name] = digest(framework / source.name)
    receipts.append({"variant": variant, "path": str(binary.relative_to(root)),
                     "bytes": binary.stat().st_size, "sha256": digest(binary),
                     "platform": expected_platform, "minos": "17.0", "arch": "arm64",
                     "info_plist_sha256": digest(info_path), "info_plist": info,
                     "resource_layout": "ios-flat", "license_sha256": license_receipts,
                     "dependencies": dependencies, "exports": sorted(exports),
                     "load_commands": load_commands.splitlines()[1:]})
require(seen == {"device", "simulator"}, "Missing shipping slice")
archive_reuse = None
relink_path = artifact / "bridge-relink-receipt.json"
saved_build_uses_relink = (not arguments.check_receipt or
    json.loads((artifact / "verification.json").read_text()).get("archive_reuse") is not None)
if not arguments.full_source_build and saved_build_uses_relink and relink_path.exists():
    baseline_path = artifact / "archive-reuse-baseline.json"
    require(not relink_path.is_symlink() and not baseline_path.is_symlink(), "Unsafe archive-reuse receipt")
    relink = json.loads(relink_path.read_text())
    baseline = json.loads(baseline_path.read_text())
    require(relink.get("status") == "PASS" and baseline.get("status") == "PASS", "Archive reuse is not PASS")
    require(relink["archive_baseline_sha256"] == digest(baseline_path), "Archive baseline receipt drift")
    require(relink["bridge_sha256"] == digest(vendor / "Bridge/OtterCADKernel.cxx"), "Relink bridge source drift")
    require(relink["relink_script_sha256"] == digest(root / "Scripts/relink-cad-kernel-bridge.py"), "Relink recipe drift")
    require(baseline["toolchain"] == toolchain, "Archive reuse toolchain drift")
    for path, expected in baseline["immutable_source_files"].items():
        require(digest(root / path) == expected, "Reused archive source/recipe drift: " + path)
    for path, expected in baseline["files"].items():
        require(digest(root / path) == expected, "Reused archive/compile/link recipe drift: " + path)
    for receipt in receipts:
        label = "ios" if receipt["variant"] == "device" else "sim"
        require(receipt["sha256"] == relink["slices"][label], "Relink output binary drift")
    archive_reuse = {"baseline_sha256": digest(baseline_path), "relink_receipt_sha256": digest(relink_path),
                     "previous_build_fingerprint": baseline["previous_build_fingerprint"],
                     "scope": relink["scope"]}
if arguments.check_receipt:
    receipt_path = artifact / "verification.json"
    require(receipt_path.is_file() and not receipt_path.is_symlink(), "Missing native build receipt; rebuild exact source")
    saved = json.loads(receipt_path.read_text())
    require(saved.get("status") == "PASS", "Native build receipt is not PASS")
    require(saved.get("build_fingerprint") == fingerprint, "CAD source or Xcode/SDK/toolchain drift; rebuild exact source")
    require(saved.get("slices") == receipts, "CAD binary drift; rebuild exact source")
    require(saved.get("xcframework_info_sha256") == xcframework_info_sha, "CAD XCFramework metadata drift")
    require(saved.get("archive_reuse") == archive_reuse, "CAD archive reuse provenance drift")
print(json.dumps({"status": "PASS", "verified_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "scope": "binary/platform/framework Info/header/license identity; not installer, runtime, user approval or release compliance",
                  "build_fingerprint": fingerprint,
                  "xcframework_info_sha256": xcframework_info_sha,
                  "archive_reuse": archive_reuse,
                  "slices": receipts}, indent=2))
