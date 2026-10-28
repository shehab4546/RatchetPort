# Controls and diagnostics

The control editor has separate Primary and Secondary bindings. Either input
holds the same PS4 button. Releasing one does not release the button while the
other remains held. Editing an assignment never moves another binding.
Duplicate keyboard or mouse inputs are rejected on Save and Play, including
conflicts with stick inputs. Direct `run.py` launches apply the same checks.

Each stick has one selector: WASD, Arrow keys, Mouse movement or None. Existing
custom direction maps remain available as Custom (saved). New installations use
WASD for movement and mouse movement for the camera. The new button defaults put
R2 on Mouse Left, L2 on Mouse Right, Square on E and Triangle on Q. Existing
settings keep their effective assignments when migrated; Reset applies the new
defaults.

Icons follow Primary, falling back to Secondary when Primary is unbound. The
standalone tutorial drawings for Cross, left stick and right stick now follow
the same mapping. The original timelines, animation placement and bytecode stay
intact. Selecting Original still disables the artwork override.

## Held buttons and triggers

Keyboard and mouse buttons are sampled as held states, not repeated taps.
Physical trigger pressure is preserved when no digital trigger binding is held.
Digital L2/R2 use 0 or 255; the game decides how each weapon responds. Mouse wheel
notches are brief taps and cannot represent a held trigger. Closing the port
menu keeps both trigger bits and trigger pressure neutral until held buttons
are released.

No weapon-specific delayed release or synthetic grenade action is added.
Grenade aiming and throwing still require gameplay verification in the reported
scene. Original controls can differ by character, vehicle and the game's control
mode. The 2016 game must not inherit Rift Apart's DualSense trigger behavior.

## Updates

Check for updates reads the public `shehab4546/RatchetPort` latest release.
Drafts, prereleases and equal or older versions are excluded. Release tags use
numeric versions, such as `v1.7.1`; display names can include a subtitle.
Failures display an error instead of claiming the installation is current.

A unique `RatchetPort-*-Windows.zip` asset with GitHub's SHA-256 digest can be
installed after confirmation. The download hash and archive paths are checked
before extraction. Missing or ambiguous packages open the release page. Source
archives are never selected as executable updates. Future releases must increment
the version to be offered to an existing installation.

## Hardware reports and Firebase

Each run adds a hardware header: OS, architecture, CPU model, logical CPU count
and RAM. Windows also records GPU names and driver versions through selected CIM
fields. Collection failure does not prevent startup.

Automatic upload is optional and off by default. It requires a configured
distribution and the Send diagnostic reports automatically setting. After a
session, selected technical log lines are filtered, bounded and queued. Reports
exclude game files, saves and account names; path and credential-like text is
redacted. Up to ten reports remain queued, with at most two uploads attempted
per session. Failed deliveries remain queued. No administrator credentials are
shipped with the client.

Reports use Firebase Anonymous Authentication and the Firestore REST API directly.
The Spark configuration requires no Cloud Functions, Cloud Storage, billing
account, scheduled backup, PITR or TTL. Keep the project on Spark. Reports have
at most 32 KiB of filtered log text. The log field is excluded from indexing.
Each installation attempts at most two queued reports per session and accepts
at most two per UTC day, retaining at most ten pending reports. A persistent
anonymous refresh token is kept only in the local user directory with restricted
file permissions where supported. It is never packaged or included in reports.

Security Rules allow authenticated anonymous clients to create immutable,
validated reports with their own UID and a server timestamp. Clients cannot
read, update or delete reports. The maintainer can inspect and delete reports
through the Firebase console. Client-side daily limits are not a server-enforced
quota or protection against hostile clients. Anonymous users can consume Spark
quotas; do not treat this endpoint as abuse-proof. Check Firestore usage and
manually remove old reports before storage fills. Automatic TTL is not enabled.
A lost network response after a successful write can leave the local report
queued; immutable document IDs prevent duplicate storage. Deleted anonymous
identities require removing the local diagnostics-auth.json file before retrying.

Configuration and activation:

1. Keep project `ratchetport-diagnostics` on Spark with no linked billing account.
2. Create the Standard `(default)` Firestore database in any supported location.
3. Enable Authentication > Sign-in method > Anonymous.
4. In Firestore > Rules, replace the rules with
   `services/diagnostics/firestore.rules` and publish them.
5. In Firestore > Indexes > Single field, add an exemption for collection group
   `diagnostics`, field `log`, and disable its indexes. Alternatively, from
   `services/diagnostics`, deploy only the checked-in Firestore configuration:
   `firebase deploy --only firestore --project ratchetport-diagnostics`.
6. Enable Send diagnostic reports automatically in the launcher only when ready.

`diagnostics.public.json` contains the project's public ID and Firebase Web API
key supplied for this distribution. The packager validates and copies these to
`diagnostics.json`. A local `diagnostics.json` overrides the bundled public
configuration. This is Firebase client configuration, not an administrator key.
No service-account credentials are included. Cloud rules, Anonymous Auth and
project readiness are not inferred from the presence of this configuration.

## Verification scope

Local checks cover held/released input, alternative bindings, analog pressure,
overlay capture, migration, duplicate rejection, secondary-only icons, update
selection, archive traversal rejection, report redaction, direct Firestore delivery and report schema.
The Firestore emulator checks schema and UTF-8 size limits, UID ownership, server
timestamps, denied reads/updates/deletes, and the Python REST commit transport.
Run `tests/test_firestore_rules.cjs` with firebase-tools 14, firebase 11 and
@firebase/rules-unit-testing 4 against the local `demo-ratchetport` emulator on
127.0.0.1:8087; the test never uses production credentials.
The original 68 prompt assets were checked; 36 replacement assets round-trip
through the overlay for keyboard, remapped keyboard and Xbox styles. Source
segments and GFX bytecode remain unchanged.

Gameplay verification, a Windows release build, an installed update and a live
Firebase round trip are separate checks and are not claimed by these tests.

References: [SDL keyboard state](https://wiki.libsdl.org/SDL3/SDL_GetKeyboardState),
[SDL trigger axes](https://wiki.libsdl.org/SDL3/SDL_GamepadAxis),
[GitHub releases API](https://docs.github.com/en/rest/releases/releases),
[Firestore REST API](https://firebase.google.com/docs/firestore/use-rest-api),
[Firebase Security Rules](https://firebase.google.com/docs/firestore/security/rules-conditions).
