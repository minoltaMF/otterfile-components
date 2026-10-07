# OtterFile CAD / VLC — partial component material set

Status: **PARTIAL COMPONENT MATERIAL SET / VLC SOURCE OFFER AND FINAL DISTRIBUTION REVIEW OPEN**.

This repository is a narrowly scoped, owner-authorized partial component material set. It is not the OtterFile App repository, an App source release, a complete LGPL compliance certificate, or an end-user relink kit. The App business source remains private; the VLC corresponding-source offer remains **OPEN**.

## Included materials

- `OtterFile/Vendor/OtterCADKernel/OCCT/`: the exact, unmodified OCCT 7.9.3 geometry subset, commit `a016080bf6738d6aeae020badee4e888ad1540a5`. 10,355 files / 69,764,821 bytes; per-file identities remain in `SOURCE-MANIFEST.json`.
- The narrow C/C++ CAD bridge, framework metadata templates, CMake source closure, source/build-tool receipts, and six existing CAD build/verification/relink scripts.
- OCCT's original LGPL 2.1, OCCT exception and component NOTICE. The three historical App license copies are included only because the unmodified source verifier compares them; no App implementation is included.
- `VLC/COPYING.txt` and named, original MobileVLCKit 3.7.3 metadata. `VLC/SOURCE-RECEIPT.json` records the official package URL, exact runtime identities and candidate corresponding-source locations. It does **not** assert that the complete VLC dependency source closure has been delivered.
- `VLC/Sources/`: v2 exact-source archive receipts, complete original regular-file manifests, independently reconstructed Git trees, all 47 ordered patch identities and full-context application evidence. The two unmodified upstream source archives are prepared as separate Release assets; they are not committed into Git. See the v2 source-delivery details below.
- `FILE-MANIFEST.jsonl`: one hash, size, license location and authorization-status row for every payload file except the manifest itself. The source files are not changed or relicensed by this manifest.

The payload excludes App Swift code, application configuration, all Secrets, user documents, fixtures, Pods trees, Git metadata, downloads, dependency caches and compiled products. Runtime binaries are identified, not redistributed here.

## Exact VLC source archives — v2

The v2 material set is prepared to deliver these two original official source archives as assets of [`materials-20261007-v2`](https://github.com/minoltaMF/otterfile-components/releases/tag/materials-20261007-v2). Asset availability must be verified at publication; the checked-in receipts alone do not prove upload or close the complete VLC source offer.

| Archive | Bytes | SHA-256 |
| --- | ---: | --- |
| `vlckit-319ed2c0724e3d4c4d34889a62fef1ae269491bc.tar.gz` | 1,607,164 | `96717d00e81eba197c29136175c88ff40c15daecdc609e05466ac28ed0f55690` |
| `vlc-79128878ddb2c280bbb6c89c76a46b31a80ade1c.tar.gz` | 32,830,546 | `f6d93944a1d12213d31ee6c027b8a85c95b1f6f81f69d61dbf54d3076752db44` |

Both archive Git trees exactly match the pinned upstream commits. All 5,123 regular source files / 139,646,456 bytes match the original tar members and file manifests. The wrapper archive contains the complete 47-patch series; all 268 hunks apply to the exact base in memory with complete context retained, two recorded line offsets and no fuzz/context removal. This is not a rebuild or proof of the generated final `git am` commit.

The wrapper's sole `documentation.html` symlink has the original relative target `doc/html/index.html` and stays within its own source root. That target is present as an original 2,843-byte regular file in the archive and was independently extracted and hash-verified. The link itself was not followed or materialized; the original archive preserves it unchanged. No absolute or parent-traversal paths, hard links or special-file members occur.

The complete upstream archives retain their original license texts, headers, tests and examples, including upstream Swift examples. Those are not private OtterFile App business code and are not relicensed under the project's CAD grants. No contrib source archive, compiled library or App implementation is added by v2.

`VLC/Sources/SOURCE-ARCHIVES.json`, `GIT-TREES.json`, `PATCH-AND-BINARY.json` and the two file manifests are the authoritative v2 retrieval/verification evidence. Earlier `VLC/CLOSURE-PLAN.json`, `SOURCE-RECEIPT.json` and `MINIMAL-MATERIALS.md` remain the original v1 audit snapshots; their archive-not-yet-retrieved statements are superseded by these v2 receipts. Actual production contrib/module/link identities, each linked dependency's source/license, final signed-App binding and applicable end-user relink/replacement materials remain **OPEN**.

## CAD source verification and build

The historical directory layout is preserved solely so the component scripts can resolve their relative paths:

```sh
/usr/bin/python3 Scripts/verify-cad-kernel-source.py
```

This is a read-only exact-source verification. It is not a rebuild, an iOS runtime test, or a licensing verdict.

`Scripts/build-cad-kernel.sh` is the unchanged component rebuild recipe: macOS + Xcode, iOS 17 device arm64 and Simulator arm64, project-local pinned CMake 3.31.10, sequential slices, at most 4 jobs and a 4 GiB working-data cap. It may download the recorded build-only CMake wheel. That wheel is not included in this draft. No build is run while preparing this draft.

`Scripts/relink-cad-kernel-bridge.py` is an engineering bridge-only recompilation tool. It requires prior identity-pinned OCCT archives, generated make recipes, SDK identity and a captured baseline; its host mode also requires a host build tree. Those generated artifacts are intentionally absent. This script is **not** a working final-user OtterFile App relink or replacement workflow.

## Original licenses and authorization

OCCT terms are in `OtterFile/Vendor/OtterCADKernel/OCCT/LICENSE_LGPL_21.txt` and `OCCT_LGPL_EXCEPTION.txt`. Additional selected parser notices remain in the original source headers and `OtterFile/Vendor/OtterCADKernel/NOTICE.txt`. MobileVLCKit terms remain in `VLC/COPYING.txt`.

The owner has authorized the six named files inside `Bridge/` under LGPL-2.1-or-later, and separately the three named component CMake files plus six CAD scripts under LGPL-2.1-or-later. `Bridge/LICENSE.md` and `COMPONENT-LICENSE.md` record those exact scopes. OCCT's additional exception is not granted for the original project-owned Bridge/build glue. Original OCCT license/exception/NOTICE text and source metadata are preserved unchanged; no blanket new license is applied to third-party notices, metadata, other code, or App Swift/business source. Complete VLC corresponding source, final-user relink/replace material, final signed archive binding and distribution review remain **OPEN** in `RELEASE-GATES.md`.

The reviewed CAD source/license/build material can be published as a component-only materials package, with the VLC source-offer gap clearly stated. That publication is not an assertion that the full VLC corresponding-source offer, end-user relink workflow or final binary-distribution review is complete.

## Official provenance

- OCCT exact source: [official commit](https://github.com/Open-Cascade-SAS/OCCT/tree/a016080bf6738d6aeae020badee4e888ad1540a5).
- MobileVLCKit package: [official 3.7.3 production package](https://download.videolan.org/pub/cocoapods/prod/MobileVLCKit-3.7.3-319ed2c0-79128878.tar.xz), registry SHA in the [3.7.3 podspec](https://raw.githubusercontent.com/CocoaPods/Specs/master/Specs/b/f/7/MobileVLCKit/3.7.3/MobileVLCKit.podspec.json).
- VLCKit exact source candidate: [official mirror commit](https://github.com/videolan/vlckit/tree/319ed2c0724e3d4c4d34889a62fef1ae269491bc).
- libVLC base candidate: [official mirror commit](https://github.com/videolan/vlc/tree/79128878ddb2c280bbb6c89c76a46b31a80ade1c). The matching wrapper build script applies additional patches; this unpatched base alone must not be described as the complete source of the distributed runtime.

Prepared on 2026-10-07 with the owner's explicit component-only publication authorization. The public hosting location is `https://github.com/minoltaMF/otterfile-components`; retain versioned commits/tags when referring to this material set. The CAD source and build inputs match the source set rebuilt for the private App candidate; this standalone package has not independently been rebuilt. The complete VLC corresponding-source set and final-user relink/replacement workflow are still incomplete and must not be advertised as delivered.
