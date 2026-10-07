# CAD component build materials license

SPDX-License-Identifier: LGPL-2.1-or-later

On 2026-10-07 the project owner explicitly extended the component-only
LGPL-2.1-or-later grant to the CAD component's CMake build glue and six CAD
build/verification scripts. The grant covers project-owned contributions in
these files, relative to the OtterFile repository root:

- `OtterFile/Vendor/OtterCADKernel/CMakeLists.txt`
- `OtterFile/Vendor/OtterCADKernel/FrameworkMetadata.cmake`
- `OtterFile/Vendor/OtterCADKernel/SourceClosure.cmake`
- `Scripts/build-cad-kernel.sh`
- `Scripts/relink-cad-kernel-bridge.py`
- `Scripts/verify-cad-kernel-source.py`
- `Scripts/verify-cad-kernel-binaries.py`
- `Scripts/vendor-cad-kernel-source.py`
- `Scripts/ensure-cad-kernel-xcframework.sh`

These contributions may be redistributed and modified under the GNU Lesser
General Public License, version 2.1 or (at your option) any later version,
without any warranty. The complete version 2.1 text is provided at
[`OCCT/LICENSE_LGPL_21.txt`](OCCT/LICENSE_LGPL_21.txt).

The six bridge files have their separately recorded component grant in
[`Bridge/LICENSE.md`](Bridge/LICENSE.md). Existing third-party source,
generated upstream source metadata, copyrights, licenses and the
OCCT-specific exception are preserved; this grant does not relicense
third-party contributions or extend the OCCT exception to project-owned code.

The grant does not cover the App's Swift business source, other App modules,
other project scripts, or unrelated repositories. They remain outside this
component-source authorization.

Public source availability, final signed binary notices and the applicable
final-user relink/replacement workflow must still be prepared and verified.
This license grant alone does not close those distribution requirements.
