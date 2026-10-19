# DYA right-side layout stagger

Branch: `feature/dya-layout-stagger`.
The user supplied a physical-layout drawing and requested the first four rows
match it, with the fifth row retained.

Only right-side display x coordinates in `cleave_hhjp.dtsi` are changed:
number row and N row move right 0.5U; H row moves right 0.25U; Y row stays put,
except Enter moves right 0.25U to align its right edge with Backspace and Shift.
Enter retains its existing rectangular 1.25U x 2U representation.

All 70 physical key entries retain order, dimensions, y coordinate and rotation.
Left-side geometry, fifth-row geometry, matrix transform and every key binding
are unchanged. A source comparison against main verified these invariants.
The generated geometry preview was visually checked against the supplied drawing.
No keymap or settings reset is needed.

Firmware source: `e2c6203d`. Build and artifact evidence follows when available.
Hardware/DYA rendering confirmation is pending before main integration.

## Artifact verification

Actions run `39342402444`, firmware identity `11744408`, folder
`output/firmware/e2c6203d/`. Both UF2 integrity/HID checks, all previous feature
configuration checks and original keymap/hold-tap checks passed. All 70 compiled
physical geometry tuples in each side's actual DTS match the modified source.
Left GNU build-id: `37326e20f1a80407e5505ce23440f7a38a1657ac`.
`layout-preview.png` is a source-generated geometry preview, not a DYA screenshot.
Actual DYA display acceptance remains pending. Main is unchanged.

## Hardware acceptance

On 2026-10-20, the user confirmed that the corrected layout is displayed in DYA
Studio. The trial is accepted for main integration. Firmware source remains
`e2c6203d`, identity `11744408`; no additional flash or settings reset is needed.
