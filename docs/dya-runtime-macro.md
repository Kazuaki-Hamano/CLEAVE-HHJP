# Runtime Macro key assignment trial

The macro editor/RPC was enabled but the keymap did not include
`<behaviors/runtime_macro.dtsi>`. The macro subsystem could store macros without
instantiating the `Runtime Macro` behavior needed for key assignment.

Include the pinned module's definition; no stock key binding, macro data/schema,
module revision or timing changes. `&rmacro <slot>` plays the stored macro in that
slot. DYA should now expose Runtime Macro and its macro-slot parameter.

Trial branch: feature/dya-runtime-macro. Based on b0c9f322 transport trial (docs
commit a62b4adb) to preserve the firmware currently being evaluated. This does
not merge the stopped browser reconnect experiment or change the public website.
Main integration and the DYA milestone commit wait for physical acceptance.
Build-trigger/source commit is separate so CI can produce reviewable trial UF2s.

Hardware acceptance:

1. Flash respective left/right UF2s; do not flash settings_reset.
2. Open DYA (fresh tab for BLE reconnect), select an existing macro or create a
   short harmless macro, e.g. three letter taps.
3. Keymap -> select a spare key -> Runtime Macro -> select the macro/slot. Apply
   and save the keymap; save macro changes as needed.
4. Press the physical key and confirm its sequence. A key on the right half
   should also be usable: macro execution stays on the central.
5. Power cycle, reopen DYA, check the saved binding and physical playback.
6. Restore the test key if desired. Report acceptance before main integration.

Artifact validation checks actual merged devicetree, central behavior metadata
in the UF2, both role configurations, UF2 structure and existing feature checks.
A build cannot confirm DYA picker rendering, real playback or persistence.


Build evidence: source 9b4ba539, identity e377a35a, Actions 39358929004.
All UF2/configuration/metadata/keymap checks PASS. Left image contains Runtime
Macro metadata; both merged devicetrees contain the new one-parameter behavior.
Canonical delivery: V:/Projects/CLEAVE-HHJP/output/firmware/9b4ba539 .
Copied files verified by SHA256. Physical acceptance is still pending.
