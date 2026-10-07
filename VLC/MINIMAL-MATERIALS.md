# Minimal materials to close the MobileVLCKit 3.7.3 source offer

This is an exact retrieval/verification plan, not an already-delivered source closure or a legal compliance verdict. Machine-readable URLs, patch/recipe hashes and original archive checksums are in `CLOSURE-PLAN.json`.

## What is now resolved

The packaged `libvlc_version.h` is byte-for-byte the fixed `Headers/libvlc_version.h` from official wrapper commit `319ed2c0724e3d4c4d34889a62fef1ae269491bc`. The same Xcode project explicitly references that fixed header at `project.pbxproj:296`; it was not regenerated from the current libVLC version template. The fixed header still declares 3.0.17, while exact base `79128878ddb2c280bbb6c89c76a46b31a80ade1c/configure.ac:5` declares 3.0.23. The binary version strings match the base version. The difference is therefore explained by the upstream fixed header lagging the base; it is not evidence that the package was replaced or tampered with.

All 47 ordered `libvlc/patches/*.patch` texts at that wrapper commit were read and hashed (255,908 bytes). They modify 97 unique source paths. Candidate contrib recipes were examined at the fixed base, and recipe/checksum modifications from the patch series were applied in memory with exact context checks. These are source-audit operations, not a native build or a final binary reproducibility result.

## Required material sets

1. **Exact wrapper source tree.** Obtain the full pinned wrapper tree or a provably build-complete selection containing original `Sources/`, `Headers/`, `Resources/`, `MobileVLCKit.xcodeproj/`, `buildMobileVLCKit.sh`, `COPYING`, required metadata, and the complete ordered 47-patch directory. No App Swift/business code is needed for this library source set. Official source URL: `https://codeload.github.com/videolan/vlckit/tar.gz/319ed2c0724e3d4c4d34889a62fef1ae269491bc`.

2. **Exact libVLC base and patched source.** Obtain the full pinned base tree, its original notices/licenses, build tools and `contrib/` recipes, then preserve/apply all 47 patches in order (or provide an identity-verifiable resulting tree plus patch provenance). Official source URL: `https://codeload.github.com/videolan/vlc/tar.gz/79128878ddb2c280bbb6c89c76a46b31a80ade1c`. The bare base alone is insufficient: the wrapper recipe runs `git am` on its patch directory. A generated Git changeset can differ from original patch `From` IDs because applying patches creates new commits; do not treat a missing GitHub commit for the binary's `g3f8bd11fd0` suffix as proof of an invalid source chain.

3. **Actual production module/contrib closure.** Obtain the actual production configure flags, selected contrib package list, generated `Resources/MobileVLCKit/vlc-plugins-iPhone.h` / `.xcconfig`, build/link logs or equivalent provenance. The wrapper recipe generates these from the built plugin/archive directories; they are not a constant list determined by the version alone. For each linked third-party component, retain its original source archive, recorded SHA512 checksums, exact `rules.mak`, every applied patch, and original licenses/notices. The plan records 117 candidate recipes and their checksum/URL facts, not 117 proven shipping components. Runtime exported-plugin-name inspection did not yield a complete module list and must not be treated as an exclusion proof.

4. **Production library identity and end-user materials.** Bind the material sets above to the existing package runtime SHA/UUID and ultimately to the exact embedded runtime in the signed App. Preserve actual compiler/SDK/build options. Establish and verify whichever final-user library replacement/relink materials and instructions are applicable to the actual delivered App; the App business-source release is not authorized by this component plan.

## Retrieval budget and sequencing

Only bounded small-text metadata was fetched: the 47 patch texts, named exact build/header/project/configure files, and candidate contrib recipe/checksum texts. They were kept in memory and reduced to auditable facts/identities; full source archives and third-party tarballs were not downloaded or added to this draft.

The wrapper archive HEAD returned 200 but no Content-Length; the base archive compressed size also has not been established. Before archive retrieval, confirm the exact URL, compressed/unpacked budget, checksum basis and isolated local destination. Never pull an archive larger than the approved budget; the proposed per-source hard cap is 256,000,000 bytes and is not a download authorization or an observed archive size.

Recommended next smallest step is to acquire the pinned wrapper tree and base tree into an isolated component-source workspace, validate all 47 patch applications, and capture the production link/contrib closure. Fetch only the dependency archives justified by that closure. Rebuilding a generic current/default wrapper and collecting whatever it downloads would not prove the source of the existing distributed package.

## Official evidence

- [Fixed header](https://raw.githubusercontent.com/videolan/vlckit/319ed2c0724e3d4c4d34889a62fef1ae269491bc/Headers/libvlc_version.h) and [exact Xcode project](https://raw.githubusercontent.com/videolan/vlckit/319ed2c0724e3d4c4d34889a62fef1ae269491bc/MobileVLCKit.xcodeproj/project.pbxproj).
- [Exact wrapper build recipe](https://raw.githubusercontent.com/videolan/vlckit/319ed2c0724e3d4c4d34889a62fef1ae269491bc/buildMobileVLCKit.sh) and [ordered patch directory](https://github.com/videolan/vlckit/tree/319ed2c0724e3d4c4d34889a62fef1ae269491bc/libvlc/patches).
- [Exact base configure](https://raw.githubusercontent.com/videolan/vlc/79128878ddb2c280bbb6c89c76a46b31a80ade1c/configure.ac) and [contrib selection/checksum recipe](https://raw.githubusercontent.com/videolan/vlc/79128878ddb2c280bbb6c89c76a46b31a80ade1c/contrib/src/main.mak).
