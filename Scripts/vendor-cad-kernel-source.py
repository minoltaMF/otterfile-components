#!/usr/bin/env python3
"""Materialize the declared OCCT geometry subset from the exact official archive.

This mechanical vendor step does not alter any upstream source. It includes
toolkit metadata, the corresponding package FILES and full LGPL/exception text.
"""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import tarfile

PIN = "a016080bf6738d6aeae020badee4e888ad1540a5"
ARCHIVE_SHA256 = "c533f2667b59921bd6bd40ce82e7b9900b0289ccc731af5fdeeba097de80ef0f"
SEEDS = ["TKDESTEP", "TKDEIGES", "TKMesh", "TKPrim"]
OMIT_PACKAGES = {"STEPCAFControl", "IGESCAFControl"}
PARTIAL_PACKAGES = {
    "DESTEP": {"DESTEP_Parameters.cxx", "DESTEP_Parameters.hxx"},
    "DEIGES": {"DEIGES_Parameters.cxx", "DEIGES_Parameters.hxx"},
}
OMIT_TOOLKITS = {"TKDE", "TKCAF", "TKCDF", "TKLCAF", "TKXCAF"}

def nonempty_lines(path):
    return [x.strip() for x in path.read_text().splitlines() if x.strip()]

def preserve_generated(path, text):
    if path.exists():
        if path.read_text() != text:
            raise SystemExit("Existing generated receipt differs; preserve and inspect: " + str(path))
        return
    path.write_text(text)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=pathlib.Path, required=True)
    parser.add_argument("--archive", type=pathlib.Path, required=True)
    parser.add_argument("--destination", type=pathlib.Path, required=True)
    args = parser.parse_args()
    archive_digest = hashlib.sha256()
    with args.archive.open("rb") as archive_stream:
        for chunk in iter(lambda: archive_stream.read(1024 * 1024), b""):
            archive_digest.update(chunk)
    actual = archive_digest.hexdigest()
    if actual != ARCHIVE_SHA256:
        raise SystemExit("OCCT archive SHA-256 mismatch")
    upstream = args.upstream.resolve(strict=True)
    destination = args.destination.resolve()
    closure = set()
    pending = list(SEEDS)
    dependencies = {}
    while pending:
        toolkit = pending.pop()
        if toolkit in closure:
            continue
        closure.add(toolkit)
        entries = nonempty_lines(upstream / "src" / toolkit / "EXTERNLIB")
        deps = [x for x in entries if x.startswith("TK") or x == "TKernel"]
        if toolkit in ("TKDESTEP", "TKDEIGES"):
            deps = [x for x in deps if x not in OMIT_TOOLKITS]
        dependencies[toolkit] = sorted(set(deps))
        pending.extend(deps)
    selected = set()
    sources = {}
    for toolkit in sorted(closure):
        selected.update("src/" + toolkit + "/" + x for x in ("PACKAGES", "EXTERNLIB"))
        sources[toolkit] = []
        for package in nonempty_lines(upstream / "src" / toolkit / "PACKAGES"):
            if package in OMIT_PACKAGES:
                continue
            selected.add("src/" + package + "/FILES")
            for filename in nonempty_lines(upstream / "src" / package / "FILES"):
                if package in PARTIAL_PACKAGES and filename not in PARTIAL_PACKAGES[package]:
                    continue
                relative = "src/" + package + "/" + filename
                if not (upstream / relative).is_file():
                    raise SystemExit("Missing exact-source file: " + relative)
                selected.add(relative)
                if pathlib.Path(filename).suffix in (".cxx", ".c", ".cpp", ".mm"):
                    sources[toolkit].append(relative)
    selected.update(("LICENSE_LGPL_21.txt", "OCCT_LGPL_EXCEPTION.txt", "README.md", "adm/templates/Standard_Version.hxx.in"))
    selected.update(("src/DE/FILES", "src/DE/DE_ShapeFixParameters.hxx"))
    # Resource lookup for translation/shape healing remains local to the framework.
    for package in ("XSTEPResource", "SHMessage", "XSMessage"):
        folder = upstream / "src" / package
        if folder.is_dir():
            for file in folder.iterdir():
                if file.is_file():
                    selected.add(str(file.relative_to(upstream)))
    manifest = []
    total = 0
    archive_tree = tarfile.open(args.archive, "r:gz")
    for relative in sorted(selected):
        source = upstream / relative
        if source.is_symlink():
            raise SystemExit("Unexpected upstream symbolic link: " + relative)
        data = source.read_bytes()
        member = archive_tree.getmember("OCCT-" + PIN + "/" + relative)
        if not member.isfile() or archive_tree.extractfile(member).read() != data:
            raise SystemExit("Extracted upstream differs from the verified official archive: " + relative)
        target = destination / relative
        if target.is_symlink() or (target.exists() and target.read_bytes() != data):
            raise SystemExit("Existing vendor source differs; preserve and inspect: " + relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copyfile(source, target)
        # The exact archive timestamp prevents a no-op restore from invalidating
        # all build objects. Content is verified above before touching metadata.
        os.utime(target, (member.mtime, member.mtime))
        total += len(data)
        manifest.append({"path": relative, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    parent = destination.parent
    archive_tree.close()
    preserve_generated(parent / "SOURCE-MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    metadata = {"project": "Open CASCADE Technology", "version": "7.9.3", "commit": PIN,
                "url": "https://github.com/Open-Cascade-SAS/OCCT", "archive_sha256": actual,
                "archive_bytes": args.archive.stat().st_size, "selected_files": len(manifest),
                "selected_bytes": total, "toolkits": sorted(closure),
                "excluded_packages": sorted(OMIT_PACKAGES),
                "partial_packages": {k: sorted(v) for k, v in PARTIAL_PACKAGES.items()},
                "extra_headers": ["src/DE/DE_ShapeFixParameters.hxx"],
                "sources": sources, "dependencies": dependencies,
                "selection": "Geometry STEPControl/IGESControl + meshing; omit CAF/DE wrapper packages; no upstream source patches"}
    preserve_generated(parent / "SOURCE.json", json.dumps(metadata, indent=2) + "\n")
    cmake = ["# Generated by Scripts/vendor-cad-kernel-source.py from the exact official FILES metadata.",
             "set(OTTER_OCCT_TOOLKITS " + " ".join(sorted(closure)) + ")"]
    for toolkit in sorted(closure):
        cmake.append("set(OTTER_OCCT_" + toolkit + "_DEPS " + " ".join(dependencies[toolkit]) + ")")
        cmake.append("set(OTTER_OCCT_" + toolkit + "_SOURCES")
        cmake.extend('  "${CMAKE_CURRENT_LIST_DIR}/OCCT/' + x + '"' for x in sources[toolkit])
        cmake.append(")")
    preserve_generated(parent / "SourceClosure.cmake", "\n".join(cmake) + "\n")
    print(json.dumps({"toolkits": sorted(closure), "files": len(manifest), "bytes": total,
                      "translation_units": sum(map(len, sources.values()))}, indent=2))

if __name__ == "__main__":
    main()
