# Binary patches in RatchetPort

CUSA01047 USA version 1.00 starts with **no binary patches**. The former game's offsets, signature fixtures and patch XML files have been removed. A saved launcher patch selection cannot enable those patches.

The generic parser/compiler remains in `scripts/patches.py` for development and its tests use synthetic fixtures. No offsets are claimed valid for Ratchet. Adding a patch requires evidence from this exact game build, validation of the original bytes, a documented purpose and real-game regression testing. Do not copy offsets or timing patches from another title.

Host output size and FPS limiting are runtime settings, not game executable patches. The guest display clock is not an engine speed patch.
