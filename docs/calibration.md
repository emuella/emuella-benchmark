# Calibration and qualification

## Question and protocol

Can fresh-process batches distinguish ordinary local variability from a controlled
slowdown while rejecting incorrect output? The smallest probe uses locked
project-authored generated-core inputs, unchanged Emuella builds, and an explicitly
synthetic copy-and-sleep worker. Evidence is owned here, not in a codec's
conformance record.

The initial protocol retains every batch and uses alternating AB/BA acquisition,
seven fresh-process rounds, warm inputs, explicit warmups and a configurable 5%
practical threshold. Per-case uncertainty uses the documented conservative ratio
interval. This is not a universal noise floor or a statistical guarantee for
uncontrolled hosts. The synthetic baseline sleeps 5 ms and the delayed treatment
25 ms inside the measured operation; corruption is separately injected into
output and must produce an invalid verdict. Retain the protocol only after these
acquisition and correctness paths are observed as intended. An unchanged real
codec can legitimately remain inconclusive and should then prompt a better
controlled host or a larger measurement budget, not a claimed improvement.

## Reproduction

Run the commands in the root README using a clean committed benchmark revision
and explicitly identified worker builds. `scripts/qualify.py` produces raw run
records, factual summaries and static reports in a new caller-selected scratch
root. `scripts/calibrate.py` produces the three synthetic observations and a
retain/reject record. Ordinary CI verifies deterministic invariants; the separate
worker job exercises real codecs with the pinned generated catalogue.

The full journey contains six U8/U16 greyscale/RGB generated inputs, shared classic
codestream decode, native lossless encode, selected native ROI/reduced output,
two-thread decode, lossy 2/4-bpp requests, Emuella diagnostics, and native/application
HT lossless and lossy runs. Failed or invalid outputs cannot be accepted as
successful points; documented unsupported or unattainable lossy points remain
visible. The minimum lossy PSNR of zero in this harness qualification is a
mechanism test, not an application quality target.

## Evidence scope

Committed evidence contains factual identities, aggregate outcomes and measurements
only. Input pixels, recompressed codestreams and external-tool diagnostics stay
in the authorised scratch store. Each retained observation identifies the exact
source revision and built executable digests. Later exact-head/merged-source
qualification is recorded with the owning pull request to avoid a self-referential
source-revision update loop.

These small generated cases validate the harness and selected adapter routes.
They do not qualify photographic/HDR quality, large-image memory scaling, all
codec profiles, arbitrary hardware, or a universal implementation ranking.
Encoder defaults differ where public APIs differ: in particular Emuella classic
RGB applies MCT, while the selected OpenJPEG profile does not. Effective profiles
are recorded with each response; native output equivalence is the comparison
contract. Application-journey OpenJPH timing is distinct from native operation
timing. RSS is a native worker process high-water mark including verification.
