# agent-statusline handoff

This is the tracked, public-safe current-state record. Machine-local operational
notes may add detail, but they do not override this file, [AGENTS.md](AGENTS.md),
the roadmap, or accepted ADRs.

## Current release boundary

- Current release target: 0.6.0, correct Claude Code subagent counting.
- Preceding release: v0.5.14, verified on GitHub, TestPyPI and PyPI.
- Branch owner: Codex on `codex/fix/v0.6.0-subagent-count`.
- Reviewer role: independent exact-candidate review pending.
- Next planned slices: 0.6.1 schema-2 element visibility and 0.6.2 interactive editor.
- Hosted CI, Release, and paired package-index promotion workflows are active.
  Every pull request and `main` push runs one
  complete-ancestry audit. Documentation-only refs skip both hosted test lanes;
  full-scope refs run the Linux Python matrix and representative macOS evidence.
  One stable aggregate job reports whether all required work passed or was
  deliberately skipped. Missing, malformed, failed, cancelled, or inconsistent
  results fail closed; only reviewed canonical direct keys are accepted.
- The repository is public. Active no-bypass ruleset `22966865` protects
  `main`: pull requests and resolved review threads are required, the aggregate
  GitHub Actions result must pass against current `main`, and deletion and
  force-push are blocked.
- Runtime dependencies remain empty and versions remain Git-tag-derived.

v0.4.5 is tagged and released with one exact artifact pair on GitHub, TestPyPI,
and production PyPI. It corrects session-bound context fallback and compaction
boundary/summary counting, with schema-4 transcript-cache replay and synthetic
concurrency coverage. It preserves the approved display, accounting, installer,
and dependencies. TestPyPI and PyPI are
bound respectively to `publish-testpypi.yml` and `publish-pypi.yml`; both
GitHub environments require maintainer approval, accept only branch `main`,
and allow no bypass. No package-index token or secret is stored.

## Stable product boundary

The Claude Code renderer retains ten rows in this order:

`PROJECT`, `MODEL`, `CONTEXT`, `USAGE`, `COST`, `SYSTEM`, `TOOLS`, `CACHE`,
`TOKENS`, `TIMING`.

Their current fields and priority order remain approved. Runtime behavior stays
local, state stays outside the repository, runtime dependencies stay empty, and
currency-labelled values remain exactly accountable. Codex remains a separate
widget-based host; [PORTING.md](docs/PORTING.md) records the verified boundary.

## Release train

Released slices through v0.2.14 cover ownership-safe installation, the locked
quality gate, malformed-input resilience, private serialized state, exact
rolling-cost attribution, session-scoped process evidence, and bounded
observation state, tracked governance, deterministic rendering safety, and
hermetic installed-renderer evidence, isolated self-test, and safe diagnostics.
They also cover pinned lean workflows, the ordinary reachable-history rewrite,
accepted historical pull-ref boundary, prospective ancestry protection,
oversized-evidence closure, protected public conversion, and exact aggregate CI.

v0.2.14 completed public-CI alignment after conversion. v0.3.0 completed the
production-ready records-and-metadata milestone promised by ADR 0030. v0.3.1
completed measured hot-path import reduction and source-hermetic benchmark
evidence. v0.3.2 completed public package metadata, portable package-page
rendering, and package-manager guidance. v0.3.3 completed locked build-once
artifact promotion and exact GitHub Release publication. v0.3.4 completed
trusted TestPyPI publication and exact public-index verification. v0.3.5
completed the public landing page and first production PyPI publication.
v0.3.6 completed separate, reusable TestPyPI and PyPI promotion workflows.
v0.4.0 completed the explicit host-acquisition architecture boundary. v0.4.1
completed the normalized Claude acquisition adapter without changing display.
v0.4.2 completed the documented local per-session metrics contract. v0.4.3
completed configurable context warnings and user-visible Stop timing. v0.4.4
completed native Linux and WSL memory pressure parity. v0.4.5 completed
session-safe context fallback and verified compaction counting.

The complete sequence and exclusions are authoritative in
[ROADMAP.md](docs/ROADMAP.md). Do not merge the historical hardening branch as
a whole or import a later slice into the current release.

## Resume point

v0.5.14 is verified on GitHub. [PR #64](https://github.com/nachiketbhujbal/agent-statusline/pull/64)
merged reviewed candidate `a15445b74c7e32a48026af73047b6ea92ef5d937` as `f1683c2a0bef86d0e0203dcec64bfc1802efd20a`. The exact
main CI run 42393289307 passed before annotated tag object
`8268a6fa84ef35e8517d269113e1b8e41205c2da`. GitHub Release run 42393387725
published the verified artifact pair:

- Wheel SHA-256 `492c022c3a7afea6c0f152cd974cd4d4ab7c3cfd2fbfd8fbf24615893419ef16`.
- Source SHA-256 `e537aa17e7f6d8bc7e36e3d4ad117540013e8e7d03233078f7be3ef2e71d4283`.

The exact wheel clean-installed and passed version, isolated self-test and
config checks. [TestPyPI run 42393479848](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42393479848)
verified the exact pair and isolated installation after approval.
[Production run 42393883813](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42393883813)
passed after separate approval. Direct index verification matched both
hashes and the installer listing. The clean installation and self-test passed.

v0.5.13 is verified on GitHub. [PR #62](https://github.com/nachiketbhujbal/agent-statusline/pull/62)
merged reviewed candidate `f78d69c2155a5b96e13c50d23ad6c2a5bd9d39f1` as `2308173be6a50f176852f94e9ce4c2a355811064`. The exact
main CI run 42390986006 passed before annotated tag object
`0e719f8ebe8445b57c9d751ca932de9dc76bd812`. GitHub Release run 42391079192
published the verified artifact pair:

- Wheel SHA-256 `934310cc29d5a7711b773e06dc3dbe73a9400c4ae4d4549ab1fb83d8955b638b`.
- Source SHA-256 `de0a1457b9c4d907b48bddb2a00f11f6d9810897ecd123d4d9f140a9643fc9d6`.

The exact wheel clean-installed and passed version, isolated self-test and
config checks. [TestPyPI run 42391169563](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42391169563)
verified the artifact pair and clean installation after approval.
[Production run 42391457249](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42391457249)
passed after approval and verified the identical artifact hashes, installer
listing, clean installation and isolated self-test.

v0.5.12 is verified on GitHub. [PR #61](https://github.com/nachiketbhujbal/agent-statusline/pull/61)
merged reviewed candidate `42645b189f01fcd0e3686e6fbfcdbced744ff7cc` as `cd9476ed3088ca2e362816e0d7ec91a73427fcf4`. The exact
main CI run 42390015848 passed before annotated tag object
`ae0dcc8af11c015e9787f5a9f6fac09aa0160465`. GitHub Release run 42390101223
published the verified artifact pair:

- Wheel SHA-256 `7010997a0d7f71ab87d7f11dc4e141918761ad003ce909283d8640c2cdf57c01`.
- Source SHA-256 `7be0ea405091cff0cf71adc31a014012bb33b7d5d449a606992e05bbfb348591`.

The exact wheel clean-installed and passed version, isolated self-test and
config checks. [TestPyPI run 42390195049](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42390195049)
verified the artifact pair and clean installation after approval.
[Production run 42391433494](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42391433494)
passed after approval and verified the identical artifact hashes, installer
listing, clean installation and isolated self-test.

v0.5.11 is verified on GitHub. [PR #60](https://github.com/nachiketbhujbal/agent-statusline/pull/60)
merged reviewed candidate `312ca4e7170823a026dc40c2762827bd4498442c` as `78da91bf4b4fc4bd2558242727b85e2da0de25ce`. The exact
main CI run 42389302556 passed before annotated tag object
`a3c2e82c04072b81d9d8ffd35564390cec483a2d`. GitHub Release run 42389400758
published the verified artifact pair:

- Wheel SHA-256 `369336074c0f125ac293fddc5b2353f28b00e31a008ffb486d8bc5548c9ad154`.
- Source SHA-256 `7ebe893f0f845d0987a51109a6b020f920d3d5453c419bc11ea6e1fd1625addf`.

The exact wheel clean-installed and passed version, isolated self-test and
config checks. [TestPyPI run 42389477232](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42389477232)
verified the artifact pair and clean installation after approval.
[Production run 42391426138](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42391426138)
passed after approval and verified the identical artifact hashes, installer
listing, clean installation and isolated self-test.

v0.5.10 is verified on GitHub. [PR #59](https://github.com/nachiketbhujbal/agent-statusline/pull/59)
merged reviewed candidate `1646b25bf500dcf37724fbb54f0dcd54a952d4d5` as `46d08da4f6ef0f467d834ddaf83173d26d2112e3`. The exact
main CI run 42388232317 passed before annotated tag object
`ec26756c1b74e91a67d28ec297419b0d480138b0`. GitHub Release run 42388339747
published the verified artifact pair:

- Wheel SHA-256 `39182de85bbfd2dd0243364c2c777f0ed72288fa8afb18308fbd347088afc715`.
- Source SHA-256 `2da392af1da3eccac4793f2b07b864d5b84adf05f07055e566907584b0fc7229`.

The exact wheel clean-installed and passed version, isolated self-test and
config checks. [TestPyPI run 42388413515](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42388413515) verified the exact pair
and clean installation after approval. [Production run 42388958597](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42388958597)
passed after approval and verified the identical artifact hashes, installer
listing, clean installation and isolated self-test.

v0.5.9 is verified on GitHub. Exact candidate
`f1b23ce99d69d103d34cf24277e63f443c8b611a`, based on
`bb529f60e2241d36e89a67e221f62fcd70800d83`, passed the complete local gate:
838 tests, 91.30% subprocess-aware coverage, locked documentation/all-files/static
checks, build, privacy/metadata and Twine. Independent detached Python 3.12
review passed 23 verifier tests and locked/build/artifact checks with no findings.
The regression fails the preceding verifier and passes this candidate. Both
index endpoints were checked read-only against already released v0.5.8 artifacts.
An isolated v0.5.8 upgrade preserved full synthetic settings/ledger bytes and modes.

[PR #57](https://github.com/nachiketbhujbal/agent-statusline/pull/57) merged as
`6f642e688dd8c2bc8b0937f74d1b1d2e76004d00`. Exact PR run 42338545863 and
main run 42338654277 passed Linux Python 3.11–3.13, macOS and the required result.
Annotated tag object `c89014d169cd85e9a177e2702d500af9ac6849b2` peels to that merge.
[GitHub Release run 42338736056](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42338736056)
published the pair. Downloaded hashes matched GitHub, privacy/metadata and Twine
passed, and the exact wheel clean-installed on Python 3.11, reported 0.5.9 and
passed its isolated self-test and config check.

- Wheel SHA-256 `dd24de46b4fcc9fe32f1618782a3861eb6ac64881967bdbf5e703b42fe9ff3a2`.
- Source SHA-256 `5d58f27822aaead4bb52ff837951e2526219276f4f650a1d54cfad2292da22db`.

[TestPyPI run 42338823484](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42338823484)
passed preparation, publication and verification on attempt one after maintainer
approval. It verified the exact pair, installer listing, clean Python 3.11 index
installation, exact version and isolated self-test.
[Production run 42339018724](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42339018724)
passed preparation, publication and verification on attempt one after
separate approval. Direct production verification matched both hashes and the
installer listing. The clean Python 3.11 installation and self-test passed.

The maintainer approved a broader plan without forcing a version ceiling:
remaining 0.5.x correctness/refresh/measured performance, schema-2 element controls
and an early interactive editor, later typed presentation and
native host facts, optional 0.7.x layouts, then capability-dependent 0.8.x host
acquisition. Keep one config location, no profiles/path option, and collection
independent of hiding. Numbers after 0.5.9 are provisional slots; fixes can take
any next patch and shift planned work. See
[CUSTOMIZATION_DESIGN.md](docs/CUSTOMIZATION_DESIGN.md),
[roadmap](docs/ROADMAP.md#next-release-and-milestones) and ADRs
[0059](docs/adrs/0059-verify-installer-listing-before-index-install.md)/
[0060](docs/adrs/0060-evolve-one-config-with-collection-independent-views.md).

### Completed v0.5.8 boundary

v0.5.8 corrects cache-state acquisition: prefer the current payload's validated
native TTL, warmth and expiry; retain explicitly estimated transcript fallback
for older clients. It keeps ten rows, the 41 field IDs, TOML and environment
behavior, ledger and installer contracts. New cache statistics and other host
fields follow as separate opt-in slices after the capability inventory.
See [ADR 0058](docs/adrs/0058-prefer-native-prompt-cache-state.md) and the
[research inventory](docs/RESEARCH.md#claude-code-status-line-capability-audit).
Exact final candidate `0b76de6e810b7ad3280e6e3f39b311973618633b` passed
renewed independent review after correcting its packaged README link.
The owner gate passed 827 tests with 91.53% subprocess-aware coverage,
locked documentation/all-files/static checks, build and artifact checks.
The reviewer proved the native precedence regression fails v0.5.7 and passes
the candidate. An isolated v0.5.7 wheel upgrade retained complete synthetic
settings and ledger bytes and modes; the installed self-test passed.

[PR #54](https://github.com/nachiketbhujbal/agent-statusline/pull/54) merged as
`e92100d114304fcbd5e7597ced7ff833548f2164`. Exact PR run 42333105488 and main
run 42333217426 passed Linux Python 3.11–3.13, macOS and the aggregate.
Annotated tag object `5f338a0526b42be5860db9dd95d0a4b4dd4bf26f` peels to that merge.
[GitHub Release run 42333313478](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42333313478)
published the verified pair, which passed a clean Python 3.11 install,
exact version check, isolated self-test, artifact privacy/metadata and Twine.

- Wheel SHA-256 `371a75f9a75aca5e34c811d0eae1d5b4af23c1e9928d393b97acb14a8929dbec`.
- Source SHA-256 `e72a9638bca7f3fdac26064543d7aefe63653f19d48d79b1518085e77633a628`.

[TestPyPI run 42333384663](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42333384663)
and [production PyPI run 42334219594](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42334219594)
passed after separate maintainer approvals. Both verified the same exact
artifact pair, a clean Python 3.11 index installation, the exact version and
isolated self-test. Independent direct index checks matched both hashes.
TestPyPI passed on attempt one. Production's upload succeeded on attempt one;
the first install verification reached its installer listing before v0.5.8
appeared. After the listing exposed the exact wheel and hash, only failed
verification was retried; attempt two passed. No upload or artifact was replaced.
No deployment approval or publication step remains pending.
Tests must use disposable state; live settings and ledger are not fixtures.

The separately requested terminal Claude Code update completed from 2.1.270 to
2.1.319. Both Claude settings files retained exact bytes and modes. The live
ledger remained valid with its mode preserved but changed during the update
window while a Desktop-managed Code process was running; no accounting code
was exercised against it and no ledger restoration or mutation was performed.


The planned configuration series and documentation patch are complete.
Every release from v0.5.1 through v0.5.7 is available on GitHub, TestPyPI,
and production PyPI. Separate maintainer approvals preceded each package
publication. The same wheel and source hashes were verified across all
three locations, followed by a clean Python 3.11 installation and isolated
self-test from each package index.

| Release and artifacts | TestPyPI | Production PyPI |
| --- | --- | --- |
| [v0.5.1](https://github.com/nachiketbhujbal/agent-statusline/releases/tag/v0.5.1) | [verified](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42304308635) | [verified](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42324969960) |
| [v0.5.2](https://github.com/nachiketbhujbal/agent-statusline/releases/tag/v0.5.2) | [verified](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42305217679) | [verified](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42325409610) |
| [v0.5.3](https://github.com/nachiketbhujbal/agent-statusline/releases/tag/v0.5.3) | [verified](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42306218265) | [verified](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42327557266) |
| [v0.5.4](https://github.com/nachiketbhujbal/agent-statusline/releases/tag/v0.5.4) | [verified](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42306938542) | [verified](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42328724606) |
| [v0.5.5](https://github.com/nachiketbhujbal/agent-statusline/releases/tag/v0.5.5) | [verified](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42307651660) | [verified](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42329755636) |
| [v0.5.6](https://github.com/nachiketbhujbal/agent-statusline/releases/tag/v0.5.6) | [verified](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42308556413) | [verified](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42330263250) |
| [v0.5.7](https://github.com/nachiketbhujbal/agent-statusline/releases/tag/v0.5.7) | [verified](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42330932831) | [verified](https://github.com/nachiketbhujbal/agent-statusline/actions/runs/42331071908) |

v0.5.7 is tagged on reviewed merge `c88aed96889f3c557874d0ac8814eef08b8c39b6`.
PR #51 used the documentation-only CI lane, with exact main run 42319063882.
GitHub Release run 42319102964 published the verified pair.

- Wheel SHA-256 `06d794b32bed17fabf04af22165c52b717b26f9ae270df8d67017ced2ef5d2e4`.
- Source SHA-256 `0f131e006c794544e272a5214ebc0a9098fd1f12592806ef70a44361b93cbdad`.

v0.5.6 release merge `49683fadce56849c50d1f64d3a1fbe2931fcfa5e` passed
independent exact review, 798 owner tests, Linux/macOS CI, and GitHub Release
run 42308425622. A disposable upgrade from v0.4.5 preserved complete settings
and ledger bytes and modes.

Several first install checks reached the package index before its installer
listing contained the new version. The failed verification jobs passed
after propagation. Published artifacts were retained and upload jobs were
not repeated.

The live iMac installation remains outside the release work. No live ledger
or Claude settings were used by the tests or installation checks.

v0.5.2 corrected a reproduced width violation in the malformed-input fallback.
It took the next patch slot, shifting the remaining features forward by one.

v0.5.0 implements optional TOML, plain output, display-only
row switches and read-only configuration validation, with a Python 3.11
minimum and no runtime dependencies. See [ADR 0052](docs/adrs/0052-add-opt-in-toml-configuration-at-v0-5.md)
and the [roadmap](docs/ROADMAP.md#050--package-owned-toml-configuration).
The 0.4.x line retains Python 3.9 support. v0.5.1 adds selection of existing
field groups. See [ADR 0053](docs/adrs/0053-select-existing-display-field-groups.md)
and the [configuration release sequence](docs/ROADMAP.md#05x--display-customization).

Exact candidate `0ceafa28683ebd2109c647952d4c47f926502284` passed
independent review with no blockers against the v0.4.5 main closeout
`ef7a8975df2ff53ac0ba054fe4467d5770279d81`. Both local runs passed 763
tests, locked checks, build and artifact verification. The exact candidate
wheel passed a disposable upgrade from v0.4.5; synthetic ledger and Claude
settings bytes were unchanged. The reviewer confirmed default output parity
and plain output at 1, 28 and 240 columns. Checkout users switching interpreters
must uninstall using the old checkout and interpreter first.

PR #42 run 42295563193 and automatic main run 42295824665 passed Python
3.11–3.13, macOS and the required aggregate. Annotated tag object
`f5365c92e772163a46fed59ea0cb13c21dbecd6c` peels to
`7b9597f3b20d86c4a9e504e0b9db1335ecbd04ed`, the verified release merge.
GitHub Release run 42296084386 published the exact pair:

- Wheel SHA-256: `ea86d6fa73c2bb461f60e8a02f84a0f19437c979dd62ed8a81b8583dd8b61cd1`
- Source SHA-256: `add9085874b7b497f4e0878b5ba5daa1c13b67f84fcb86d58e7944508afc2343`

TestPyPI run 42296245579 and production PyPI run 42296697147 passed after
separate maintainer approvals, with exact public hashes and clean Python 3.11
installs and self-tests. Direct production-index verification matched both
hashes. No live ledger, Claude settings or installed tool was changed.

v0.4.5 is tagged at merge `735ed343c1b4a965d7ef7d3d94f3ab56d5a9da28`.
Exact implementation candidate `1f8605f400f0855423a5b8245d41ab65308917b2`
passed independent no-findings review against v0.4.4 and the full local gate:
736 tests, owner coverage 90.18%, independent coverage 89.97% on Python 3.11,
build, artifact privacy/metadata, and an isolated Python 3.9 installed-wheel
self-test. New fallback and boundary regressions reject v0.4.4. PR #39 run
40042908050 and merged-main run 40043090603 passed Linux Python 3.9–3.13,
macOS, and the required aggregate result.

Annotated tag object `e494cc7bee182007714e3e98f8676124a4d01ec7` peels to
that exact merge. GitHub Release run 40043218170 published one exact pair:
wheel `702f624d570838a7685cb9de06318ccda81b11fc223d5c0532ac853cc32f49e4`
and source archive
`e7b5b33b0cff9e71f9c2125c81febddfe86103f1729da4c288cef310729a502b`.
The downloaded release pair passed privacy/metadata checks; the exact wheel
reports 0.4.5 and passed an isolated Python 3.9 clean-install self-test.

TestPyPI promotion run 40043331875 and production PyPI run 40043731533
passed after their separate maintainer approvals. Both verified the same exact
artifact hashes and clean Python 3.9 installations, versions and isolated
self-tests. Direct production-index verification also matched the recorded
wheel and source hashes. No publication step remains pending.

PR #40 independently reviewed record candidate
`d0757bec3230904eafa484c366b88815bd7efa90` and merged the earlier pending
publication checkpoint as `0f445937ef007804ac8b3608921632b159005095`;
PR run 40043985388 and automatic main run 40044032831 passed their deliberate
documentation-only ancestry lane. This final record closes the now-satisfied
production prerequisite without moving the release tag. Final-record review
also found the development verifier required stale Current/Unreleased labels
after publication. The post-tag closure accepts a fully released roadmap with
no selected next target, retaining version-agreement checks with synthetic
coverage. This development-only correction is not in the immutable v0.4.5 pair.

This patch confines context fallback to matching session evidence and verifies
compaction boundary/summary counting, schema-4 cache replay, and six concurrent
synthetic sessions. General configuration-file customization is separate.
The live ledger and unrelated Claude settings were not test inputs or modified.
The iMac was separately upgraded to v0.4.5 after release, with managed hooks
refreshed and the live ledger and Claude settings verified unchanged.

v0.4.4 is complete at tagged merge
`d92077d1cb79fc92ae0a296df00ad3fbd3eeb353`. Exact candidate
`79335ec1360808ff69b6c1292b52a3cae659a6ad` passed independent no-findings
review and the complete local gate: 714 tests, owner coverage 89.38%, artifact
privacy and metadata, an isolated Python 3.9 wheel self-test, and the native
macOS probe. PR #37 CI run 35052560738 and merged-main run 35052651782 passed
the complete Linux matrix, direct Linux memory assertion, representative
macOS lane, and required aggregate result.

Annotated tag object `ebe8a28001cb608d91afcde088e160340e3dfeeb`
peels to that exact merge. GitHub Release run 35052809112, TestPyPI run
35052901590, and production PyPI run 35054311789 published and verified the
same wheel at
`ff235e542952438f1b3cf61729e8149b83a7740df5ebc63b7e859a8f0b4e1e45`
and source archive at
`425d6a42da5274e8b511ce3e020380cfb903aeab2a741d0918a6153af6c9e489`.
Production's initial clean-install step reached its Simple Index before v0.4.4
appeared there, after exact JSON hash verification; the failed verification
rerun passed after propagation. No GitHub issue tracked this
maintainer-requested slice. At that release boundary the iMac installation was
v0.3.6; changing it or live Claude configuration was outside v0.4.4.

v0.4.3 is complete at tagged merge
`dc7000b4c2bbb5b659b8837cee28b9055b95787e`. Exact candidate
`e4a0d91762fbb1bc08bb891c07766bec0ea86cec` passed independent no-findings
review and the complete local gate. PR #35 closed issues 31 and 32; PR CI run
35009998711 and merged-main CI run 35010141037 passed before annotated tag
object `c1d894e5f0b24f3f82c960873df0c9d7fe056292` and GitHub Release run
35010394642. TestPyPI run 35010556768 and production PyPI run 35011232785
published and clean-install verified the same exact wheel at
`adda5eccc1e82279a37608c9aeec06518b9596aef68700009b21ee18fe9d00ae`
and source archive at
`bf8637bc0e0ca2877869194e9f5487468bd9e49fe23788604d77631716836b7b`.
TestPyPI's first clean-install attempt reached its Simple Index before v0.4.3
appeared there, after its JSON hashes had already matched; the failed-job rerun
passed after propagation. Production PyPI passed on its first verification.

v0.4.2 is complete at tagged merge
`5dcbb5792bb718925a02ca4e9ee6952126184157`. Exact candidate
`dd4b55d17faf5c7b9b86bf8283b2a1e7437ab62f` passed renewed independent review;
PR #34 closed issue 30, merged-main CI run 35006217099, GitHub Release run
35006440871, TestPyPI run 35006652209, and production PyPI run 35008034856
passed. The production clean-install check initially reached the Simple Index
before it exposed the already hash-verified files; its rerun passed after
propagation. GitHub, TestPyPI, and PyPI expose the same exact wheel at
`a1696f885a880bd15b9c8b2bcad9c51c5ecac33b7b08a02e29b3fd2df94decad`
and source archive at
`669124024f6fd3c8f27830395ee9e49a5274cb86330e3d0b5828206be3bbefd1`.

v0.4.1 is complete at tagged merge
`d7b8341ed9cfea801f8f8d50c9832ead10e7548e`. Exact candidate
`3193300a70dfc9d8f892cc330d694126c84e37af` passed independent review; PR #33,
merged-main CI run 35000480030, GitHub Release run 35000669543, TestPyPI run
35000820947, and production PyPI run 35001447162 passed. GitHub, TestPyPI, and
PyPI expose the same exact wheel at
`ffe0f61c134158bc6894590ecc47c1f7509f37bebcf7ae20b31ddd4b5af9266c`
and source archive at
`173a95ee032e03f011d0b3638e1bc0945b8fbbce0a28686be5e43ca0c97ad45f`.

v0.4.0 is complete at tagged merge
`125f60527d44cc3dcf20ff8c384542944dacbf8d`. GitHub Release run 34997267833,
TestPyPI run 34997383308, and production PyPI run 34997703359 published and
verified the same exact artifact pair. The initial PyPI clean-install check ran
before the Simple Index exposed the already verified files; its isolated rerun
passed after propagation.

v0.3.6 is complete at tagged merge
`9a92560be103a56e542a27ce2aee423c4255f9e0`. Exact candidate
`ca4a0af180d24e8e9f5462771447ad97adb5f32f` passed the complete local gate and
one independent review. PR #26, merged-main CI, annotated tag object
`598b3667dec7c2c1bba984b7ce69600fddc63623`, GitHub Release run 34801071659,
TestPyPI run 34801160225, and production PyPI run 34801290059 passed.

GitHub, TestPyPI, and PyPI report the same exact published pair:
`agent_statusline-0.3.6-py3-none-any.whl` at
`786f74d79311b2c6c7dbdc9cde460156426941beb85a977a823c0b6fcbbe20ff` and
`agent_statusline-0.3.6.tar.gz` at
`d4802e833701b30c06b22b31dc2ca73fff49d991d69649302b7c0902e4b4fe55`.
The local uv-managed command was upgraded from production PyPI and reports
0.3.6; Claude Code's managed command and complete settings bytes were unchanged,
and an isolated self-test passed without reading live accounting state.

The v0.4.0 research boundary is now measured and recorded in ADR 0046. Installed
Codex still exposes a built-in-widget footer rather than an arbitrary command;
stable hooks provide a credible acquisition trigger, and local rollouts expose
exact token/session facts but no exact cost field. ADR 0047 preserves that
architecture while updating the follow-on order: v0.4.2 published local
per-session metrics for issue 30, and v0.4.3 completed the configurable
context guard and Stop timing from issues 31 and 32. The synthetic-fixture
Codex parser and any opt-in Codex collector/query surface follow that local
integration sequence.

Exact architecture candidate
`d8ceb7bb5537b745df070214aafd68c866f226ea` passed the complete local gate and
one independent no-findings review. PR #28 passed the documentation-only hosted
gate and merged it as `5fe305a6643b8141dd1874662730b1f020dea32d`;
automatic main run 34873106649 passed the same lean required lane.

The v0.4.1 adapter does not add a Codex implementation, configuration mutation,
renderer claim, or Codex currency accounting. Accepted pull refs, unreachable
objects, and recovery cleanup remain separate.
[PUBLIC_READINESS.md](docs/PUBLIC_READINESS.md) records the protected baseline.

Durable decisions live in [ADRs](docs/adrs/README.md), completed behavior in the
[changelog](docs/CHANGELOG.md), review evidence in
[CODE_REVIEW.md](docs/CODE_REVIEW.md), and measured or open questions in
[RESEARCH.md](docs/RESEARCH.md).
