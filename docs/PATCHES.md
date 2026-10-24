# Verified binary patches in RatchetPort

CUSA01047 USA version 1.00 defaults to **Original/30 with no binary feature patches**.
RP-04 adds one opt-in, fingerprinted experimental 60 FPS group containing paired
interval/clock replacements. Gameplay acceptance remains pending; see
[frame timing evidence and tests](RP04_FRAME_TIMING.md). Motion blur and internal
resolution patches remain disabled. Host output size and VSync are separate.

The exact supported source and extracted ELF SHA-256 hashes are recorded in that profile and `docs/RP02_BASE_100_FINDINGS.md`. Requested groups are checked against TITLE_ID, APP_VER and both hashes. An unknown dump may run the unpatched baseline, but cannot receive a verified feature patch.

## Selection and checks

`game_fps=60` in ratchet.ini selects the experimental group; any other value
selects Original. It overrides stale selections of that group in RATCHET_PATCHES.
Other reviewed names may be supplied via RATCHET_PATCHES (semicolon separated);
unknown names are skipped explicitly. XML/mod patch files cannot activate
executable patches. The loader rejects nonempty legacy G3PATCH2 packets.

Each reviewed group must list writes with `signature`, `offset`, `elf_vaddr`, `original_hex` and `replacement_hex`. A signature must match exactly once in source file-backed loadable segments. The original bytes, address, segment boundary and unchanged write length must match. Writes into BSS or across segments are rejected. A group is accepted whole or rejected whole. Conflicting groups are both rejected; valid independent groups can still be prepared.

Linking must leave the original bytes unchanged. Full signature windows must avoid relocation slots, ISA rewrite sites (including a relocated following instruction), and Windows TCB instructions. New feature authors must document their instruction/data semantics and regression evidence in addition to these mechanical guards. A successful signature match alone does not approve a feature.

## Loader order and acknowledgement

1. At launch start, invalidate the previous receipt and replace any old packet with an empty transaction, before CPU/game preparation can fail.
2. Prepare and link a fresh boot image. Generate an ISA table if needed. Validate selected groups and write a transaction bound to the SHA-256 of the complete linked memory image.
3. The native loader reads and validates the **entire** packet against the raw image, mapped segments and reserved transformation ranges. No guest bytes are written at this point.
4. Perform relocations, TCB redirection and ISA rewrites. Recheck **all** original patch bytes before applying any write. Any failure aborts the launch; no partial feature reaches guest execution.
5. Apply the transaction in writable guest memory, set segment protection and validate the entry point. Publish the matching loader receipt. Original game files and `boot-linked.bin` are never patched.

`out/patch_status.json` distinguishes `prepared`, `applied` and `skipped` with reasons. `prepared` means only that a packet was generated. `patches.patch_status(out)` / `ratchet_patches.status(out)` reports `applied` only when `patch_receipt.bin` matches the current transaction's random token **and** write count. `run.py` persists that result when the loader exits. A stale, missing, malformed or mismatched receipt cannot confirm a feature. Confirmation means bytes were applied by the loader, not that gameplay or performance has passed testing.

Disabling all selections creates a fresh empty packet and removes the previous receipt. The next launch uses the original linked bytes, without reverse-patching files. Output directories inside the original game directory are rejected.

## Transport

All integers are little endian. `RCPATCH3` has a 72-byte header: magic (8), linked image size (u64), SHA-256 (32), transaction token (16), write count (u64). Each record contains image-relative address and length (u64 each), expected bytes and replacement bytes. Records are ordered, disjoint, length-preserving, at most 4096 bytes each and at most 1024 per transaction. The disabled packet has zero image size/hash and no records. No relocation-pointer rebasing is supported.

The 32-byte receipt is `RCPACK3\0`, the 16-byte token and the u64 write count. The loader publishes it through a temporary file after successful application. It is a local acknowledgement protocol, not a signed security boundary against someone editing their own port files.

## Verification and user testing

`tests/test_ratchet_patches.py` covers identity/fingerprint rejection, signature absence/ambiguity, original-byte and boundary failures, conflicts, whole-group rejection, transformation exclusions, stale acknowledgements and disable/restart behavior. `tests/test_verified_patches.c` tests the native parser, truncated packets, bad hashes, bounds, overlapping writes and atomic rejection of a late original-byte mismatch. Set `RATCHET_PATCH_TEST` to the compiled native test executable to run the Python-to-C transaction/receipt test. Windows CI builds and runs both.

For the 30/60 comparison, follow [RP-04 testing](RP04_FRAME_TIMING.md#gameplay-validation-still-required).
A default launch is still Original. Selecting 60 requests an experiment, not a
claim of successful gameplay. Returning to Original and restarting must remove
both writes and the previous receipt. Never use synthetic test patches in-game.
