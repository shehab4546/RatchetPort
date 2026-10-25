# CUSA01047 USA v1.00: text and voice

The launcher offers the five language pairs accepted by the American edition's startup selector.

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

Independent text and voice selection is not enabled. Two startup language outputs alone do not prove that arbitrary pairings are supported by the voice-bank and movie loaders. The game keeps its verified default pairing, including Latin American text with Mexican voice. No region-mask bypass, missing-language download or audio-bank patch is applied.
