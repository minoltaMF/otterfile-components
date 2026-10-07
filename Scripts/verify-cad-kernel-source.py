#!/usr/bin/env python3
"""Verify the recorded exact OCCT subset; never mutate the source tree."""
import hashlib
import json
import pathlib
import sys

def require(condition, message):
    if not condition:
        raise SystemExit(message)

root = pathlib.Path(__file__).resolve().parents[1]
vendor = root / "OtterFile/Vendor/OtterCADKernel"
require(hashlib.sha256((vendor / "SOURCE-MANIFEST.json").read_bytes()).hexdigest() ==
        "ce1edbd27a4abc38d68b98929f29033204d3ecd6a4c0654ec45dcb5d3f2a0df6", "Exact-source manifest SHA mismatch")
require(hashlib.sha256((vendor / "SourceClosure.cmake").read_bytes()).hexdigest() ==
        "38c512ddfd2dd31505321191d0b1f3965eb5d1602d663a9e5b2774b3994cf826", "Source closure SHA mismatch")
metadata = json.loads((vendor / "SOURCE.json").read_text())
manifest = json.loads((vendor / "SOURCE-MANIFEST.json").read_text())
require(metadata["commit"] == "a016080bf6738d6aeae020badee4e888ad1540a5", "Unexpected OCCT pin")
require(metadata["archive_sha256"] == "c533f2667b59921bd6bd40ce82e7b9900b0289ccc731af5fdeeba097de80ef0f", "Unexpected archive SHA")
require(metadata["selected_bytes"] <= 100 * 1024 * 1024 and len(manifest) <= 20000,
        "Source audit exceeds declared budget")
selected = set()
total = 0
for row in manifest:
    relative = pathlib.PurePosixPath(row["path"])
    require(not relative.is_absolute() and ".." not in relative.parts, "Invalid manifest path")
    require(row["path"] not in selected, "Duplicate manifest path")
    file = vendor / "OCCT" / relative
    require(not file.is_symlink() and file.is_file(), "Invalid source file: " + row["path"])
    data = file.read_bytes()
    require(len(data) == row["size"], "Source size mismatch: " + row["path"])
    require(hashlib.sha256(data).hexdigest() == row["sha256"], "Source hash mismatch: " + row["path"])
    selected.add(row["path"])
    total += len(data)
actual = {str(file.relative_to(vendor / "OCCT")) for file in (vendor / "OCCT").rglob("*") if file.is_file()}
require(actual == selected, "Unrecorded or missing upstream source")
require(total == metadata["selected_bytes"] and len(selected) == metadata["selected_files"], "Source receipt count mismatch")
require(total <= 100 * 1024 * 1024 and len(selected) <= 20000, "Source audit exceeds declared budget")
license_directory = root / "OtterFile/OtterFile/OpenSourceLicenses"
for source_name, app_name in [
    ("OCCT/LICENSE_LGPL_21.txt", "OCCT-7.9.3-LGPL-2.1.txt"),
    ("OCCT/OCCT_LGPL_EXCEPTION.txt", "OCCT-7.9.3-Exception.txt"),
    ("NOTICE.txt", "OCCT-7.9.3-NOTICE.txt"),
]:
    source = vendor / source_name
    app_copy = license_directory / app_name
    require(app_copy.is_file() and not app_copy.is_symlink(), "Missing App license copy: " + app_name)
    require(hashlib.sha256(source.read_bytes()).digest() == hashlib.sha256(app_copy.read_bytes()).digest(),
            "App license SHA mismatch: " + app_name)
print(json.dumps({"status": "PASS", "version": "7.9.3", "files": len(selected), "bytes": total, "source_patches": 0}))
