# OtterFile CAD / VLC — partial component material set

Status: **PARTIAL COMPONENT MATERIAL SET / VLC SOURCE OFFER AND FINAL DISTRIBUTION REVIEW OPEN**.

This repository is a narrowly scoped, owner-authorized partial component material set. It is not the OtterFile App repository, an App source release, a complete LGPL compliance certificate, or an end-user relink kit. The App business source remains private; the VLC corresponding-source offer remains **OPEN**.

## Included materials

- `OtterFile/Vendor/OtterCADKernel/OCCT/`: the exact, unmodified OCCT 7.9.3 geometry subset, commit `a016080bf6738d6aeae020badee4e888ad1540a5`. 10,355 files / 69,764,821 bytes; per-file identities remain in `SOURCE-MANIFEST.json`.
- The narrow C/C++ CAD bridge, framework metadata templates, CMake source closure, source/build-tool receipts, and six existing CAD build/verification/relink scripts.
- OCCT's original LGPL 2.1, OCCT exception and component NOTICE. The three historical App license copies are included only because the unmodified source verifier compares them; no App implementation is included.
- `VLC/COPYING.txt` and named, original MobileVLCKit 3.7.3 metadata. `VLC/SOURCE-RECEIPT.json` records the official package URL, exact runtime identities and candidate corresponding-source locations. It does **not** assert that the complete VLC dependency source closure has been delivered.
- `FILE-MANIFEST.jsonl`: one hash, size, license location and authorization-status row for every payload file except the manifest itself. The source files are not changed or relicensed by this manifest.

The payload excludes App Swift code, application configuration, all Secrets, user documents, fixtures, Pods trees, Git metadata, downloads, dependency caches and compiled products. Runtime binaries are identified, not redistributed here.

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
