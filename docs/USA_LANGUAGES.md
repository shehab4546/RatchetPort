# CUSA01047 USA v1.00: text and voice

The launcher offers independent Text / Subtitles and Voice selectors for the five supported American-edition languages. Same as text preserves the original pairing.

| Selection | Text / subtitles | Voice | System ID | Internal text / voice IDs |
|---|---|---|---:|---|
| English | American English | American English | 1 | 1 / 1 |
| French | French | French | 2 | 6 / 6 |
| Portuguese (Portugal) | European Portuguese | European Portuguese | 7 | 13 / 13 |
| Portuguese (Brazil) | Brazilian Portuguese | Brazilian Portuguese | 17 | 18 / 18 |
| Spanish (Latin America) | Latin American Spanish | Mexican Spanish | 20 | 21 / 17 |

System ID 22 is an alias for the same French content under NA. It does not add another voice pack. Game language and launcher language are separate settings. Changes to game language require a full restart.

## Evidence and limits

The original executable's system-language conversion table at RVA `0x2c8ec40`, NA mask instruction at `0x338b2d` (`0x242042`), and secondary-language table at `0x2c8a9f0` were re-read from the supplied CUSA01047 v1.00 binary. The mask admits internal IDs 1, 6, 13, 18 and 21. The secondary table maps 21 to 17 and leaves the other four unchanged. The executable SHA-256 is `fdf72d683f305ab1a70adfe246e9ac1dbbd4ceb988b1327157b6bda55476697d`.

The supplied game-research report, `08_LANGUAGES.md`, records decoded localization samples for `.us`, `.fr`, `.pt`, `.br` and `.la` and physical large voice archives `a00s003.us`, `a00s007.fr`, `a00s013.pt`, `a00s018.br` and `a00s017.mx`. This content inventory agrees with the executable's selector. Its underlying archive payloads were not included in that research bundle, so this update does not claim a new full audio playback or whole-game localization test. The report also identifies `.ar` as English placeholder content, not an Arabic translation.

Public research was restricted to Ratchet & Clank (2016), PS4, and the American edition. The [US PlayStation page](https://www.playstation.com/en-us/games/ratchet-and-clank/) identifies the game but does not expose a language table in the retrieved page. European store language lists and the Insomniac support article for Rift Apart are not evidence for CUSA01047. The executable and edition-specific content inventory determine this selector.

The numeric mapping is recorded in [language runtime evidence](evidence/ratchet-cusa01047-0100-languages.json).

## Selection behavior

Unsupported languages from older configurations are labelled unavailable, retained in settings, and use English at launch. They are not advertised as usable languages. Supported saved values, including system ID 20 from issue #14 and ID 17 from issue #5, pass through unchanged.

## Independent selection in V1.7

`settings.json` keeps `language` (text) and `voice_language` (voice, or `same`). The launcher sends `RATCHET_TEXT_LANGUAGE` and `RATCHET_VOICE_LANGUAGE` to `run.py`. The preparation step selects the verified text override and sends the effective voice choice through `RATCHET_LANGUAGE`. `src/runtime_services.c:system_param` returns that value to `sceSystemServiceParamGetInt(1)`. The game's original NA selector continues to select its own voice and fallback locale.

The game's generic resource lookup tries primary language, secondary language and neutral. Changing only its secondary language does not separate voice when primary-language voice data exists. No independent built-in voice switch was identified in the inspected executable. The override therefore changes only requests for `localization_all` (asset hash `0xbe55d94f171bf8de`) to the selected text index. Other resource hashes retain the voice-selected language, including movie resources. This preserves the Bink/RAD path; it does not replace a decoder or modify sound banks. Cinematic track playback still needs an in-game check with mixed languages.

`scripts/language_split.py` replaces the 93-byte sorted-index lookup at RVA `0x1889d70` without a trampoline or executable allocation. It is limited to the existing CUSA01047 v1.00 profile: source/ELF fingerprints, unique original signature, exact original bytes, linked-image bounds, relocation/ISA overlap checks and runtime transaction validation all apply. Preparation rejection restores matching text/voice using the text choice. Runtime rejection is reported by the existing patch receipt; a prepared override alone does not prove it was applied. No source game file is modified.

An isolated native comparison against the original lookup passed 17,550 calls across all 25 language combinations, six variants, empty/odd/even indices, missing hashes and unrelated assets. This checks resource routing, not actual speech or subtitle playback. The text-asset hash comes from the supplied decoded localization inventory.

## Voice archive diagnostics

| Voice | User archive |
|---|---|
| English US | `asset_archive/a00s003.us` |
| French | `asset_archive/a00s007.fr` |
| Portuguese Portugal | `asset_archive/a00s013.pt` |
| Spanish LATAM | `asset_archive/a00s017.mx` |
| Portuguese Brazil | `asset_archive/a00s018.br` |

`scripts/voice_archive.py` checks existence, size and at most eight distributed 1 MiB samples. It looks for RIFF/WAVE headers and compares block hashes. Identical samples across an archive of at least eight full blocks are flagged as repeated-block corruption. Missing headers alone are inconclusive; a successful sample is not a full layout/WEM audit. No size or content hash tied to one dump is required. The launcher checks in a background thread; launch logs record the effective voice locale, expected archive, size and findings. Warnings never block play.

Reported playback with intact French and Portuguese Portugal archives demonstrates that missing dialogue in the repeated-block dumps does not establish a Wwise, ATRAC9, AJM or output-backend fault. Diagnostics recommend re-dumping language data from the user's own game. They never rename European Spanish/Portuguese to Mexican Spanish/Brazilian Portuguese, fetch replacement assets, or add European-only languages.

## Gameplay acceptance still required

Test English/English, English/French, French/English, French/French and Portuguese Portugal with intact archives after a full restart. Check menus, subtitles, gameplay dialogue and cinematics separately. Test a repeated-block French archive for a visible warning and continued launch. Automated tests cover routing, settings and synthetic integrity cases; these playback cases require the game and are not reported as passed by CI.
