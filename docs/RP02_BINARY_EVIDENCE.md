# RP-02 binary evidence audit

Status: **target inputs received; static paths traced**. See
[the 01.00 findings](RP02_BASE_100_FINDINGS.md) for build identity, original
instructions, xrefs, initialization order and limits. The checked-in
[evidence manifest](evidence/ratchet-cusa01047-0100-candidates.json) verifies
11 unique sites against the analyzed SELF. The
[capability registry](evidence/ratchet-cusa01047-0100-capabilities.json) keeps
static research separate from runtime support; every runtime feature is disabled.

Source baseline: `8ea873c654110a8d42697c8cfae515103a522b37`.

Keep game binaries and raw private diagnostics outside Git and release assets.
A source hash mismatch requires independent investigation; do not copy offsets
from 1.09 or change APP_VERSION to bypass verification.

## Read-only inventory

Run from a source checkout with Python 3.12:

```powershell
python scripts/ratchet_binary_audit.py --game-dir "C:/path/to/CUSA01047" --output "rp02-inventory.json"
```

Use the actual dump directory. The report must be a new file outside that
directory. The tool reads eboot and SFO only. It does not launch the game, prepare
an executable, change settings, export game byte ranges or write patches.bin.

The report contains source/parsed-ELF SHA-256 hashes, loaded segment metadata,
and capped string-hint locations. String presence is not feature support.
Source-file offsets, ELF file offsets and ELF virtual addresses are separate.
`prelink_image_offset` follows prepare.py's mapping of p_vaddr directly into its
image; it is not a relocated host address or a physical SELF offset.

## Candidate checks

Pass `--manifest evidence.json` to mechanically check the sites recorded in the manifest.
The JSON object uses schema_version 1, title_id CUSA01047, app_version 01.00,
source_sha256, elf_sha256 and a nonempty sites array. Each site requires:

- id: unique nonempty name;
- feature: fps, motion_blur or internal_resolution;
- signature: space-separated hex byte pairs and optional ?? wildcards;
- offset_in_signature: nonnegative offset of the original-byte range;
- elf_vaddr: the expected address in the parsed ELF;
- original_hex: exact original bytes, entirely inside the signature;
- consumer: elf_vaddr and original_hex for a file-backed executable range;
- purpose, initialization and evidence_reference: researcher evidence notes.

These notes are recorded by the researcher, not semantically proven by the tool.
Matching a consumer's bytes does not prove an xref or instruction boundary. Human
disassembly review must establish the data/control flow and initialization order.
The tool never sets a capability to supported, even if every byte check matches.
Replacement bytes, patch groups and loader application belong to RP-03 onward.

The scanner searches file-backed loaded segments (PT_LOAD and SCE_RELRO), not
zero-filled BSS, gaps or SELF headers. It rejects absent/duplicate signatures,
wrong fingerprints, coordinate mismatches, incorrect original bytes, ambiguous
virtual mappings and out-of-bounds consumer ranges. Report paths are not allowed
inside the game directory, and existing reports are not overwritten.

Exit 0 means inventory/candidate-byte checks succeeded, **not RP-02 acceptance**.
Exit 2 means an input or candidate check failed. The report always keeps
rp02_complete false and all runtime capabilities disabled.

## Checkpoint validation

`python -m unittest discover -s tests -p test_ratchet_binary_audit.py -v`

27 synthetic tests passed locally on 23 October 2026. They cover coordinate
mapping, fingerprints, uniqueness, original bytes, loaded ranges, consumer
permissions, malformed evidence and read-only CLI behavior. The analyzed SELF additionally passed all 11 candidate checks.
Actual-game execution is not claimed.

The tool never declares semantic acceptance. The separate findings document
records the reviewed static data flow. Byte matching and static review are not
runtime validation; feature enablement belongs to RP-03 and later tasks.
