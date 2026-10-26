# RX 570 startup investigation and deferred recording lifetime

Issue #24 reports a startup exception in `amdvlk64.dll` on an RX 570, before the game menus. This differs from issue #19, where the 3D world is black while menus and audio continue.

## Address comparison

The examined executable is `RatchetPort/bin/ratchet-probe.exe` from the V1.6 Resolution Preview Windows package, SHA-256 `669c263aeecb656279c908e5b0e2c12a3cd1f8d4e1763b1684797ee406ac0da5`.

- `+0x15a6c2` matches the return from a deferred command's virtual `Execute()` call inside `Vulkan::Scheduler::RecorderThread`.
- `+0x161587` matches the thread entry wrapper that calls the scheduler worker.
- The reported `+0x1798d8` lies in the `Runtime::FlushBarriers()` command wrapper, but does not exactly match its Vulkan call return address (`+0x1798d0`) in this executable. The precise reporter executable is still needed to resolve this discrepancy.

These observations direct investigation toward deferred barrier recording. They do not establish that the driver, a missing optional extension, or the lifetime defect below caused the reported crash.

## Confirmed code defect

`Scheduler::RecordData()` allocated oversized payloads in overflow storage owned by the current `RecordChunk` without checking whether the consuming command could fit in that chunk. If `Record()` then moved the command to the next chunk, executing the previous chunk freed the payload before the command used its captured span.

`RecordChunk::CopyData()` now checks command headroom for both inline and overflow payloads. The scheduler rolls over before copying when necessary. Batch reservations also retain command headroom for oversized data. `RecordChunk` is isolated in a header so its actual allocation and execution code can be tested without a Vulkan device.

## Verification

- Thirty rollover cases cover inline and oversized payloads with 0, 8, 64, 1023, 1024 and 4096 bytes left in a chunk.
- Tests overwrite the source and execute earlier chunks before the consumer, checking every copied value. Additional cases cover multiple overflow allocations, chunk reuse and `vk::ImageMemoryBarrier2` payloads.
- AddressSanitizer and UndefinedBehaviorSanitizer pass with the correction. Leak detection is disabled because the local tracing environment does not support LeakSanitizer.
- Reintroducing the unchecked overflow allocation in a local negative-control build produces `heap-use-after-free` when the consuming command reads its span.
- The Windows workflow now runs `record-data-lifetime-test`. The preceding diagnostics build at `1658a4b` completed successfully; the lifetime correction requires its own Windows build.

This is a confirmed lifetime fix, not a confirmed resolution of issue #24. Validation still requires the full `user/last_run.log`, the affected AMD driver version, the matching executable identity and a fresh run on the affected hardware. Issue #19 also remains open.
