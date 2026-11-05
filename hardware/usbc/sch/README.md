# KiCad schematic (generated, not yet opened in KiCad)

`rtvc_usbc.kicad_sch` is the editable schematic for the USB-C Voice Module. It is generated from `../rtvc_usbc.net`, so it matches the netlist and the PCB.

## Open it
1. KiCad: File → New Project (e.g. a folder `rtvc`).
2. Copy `rtvc_usbc.kicad_sch` and `../pcb/rtvc_usbc.kicad_pcb` into that folder.
3. Open the project's **Schematic Editor**, then File → Open → `rtvc_usbc.kicad_sch`. KiCad may offer to update the file format: accept.
4. Run **Inspect → Electrical Rules Checker** and read the result before trusting anything.

## How it is built (read this)
* **Connections are by net label**, not drawn wires: each pin has a short stub with a label at its end (`GND`, `AVDD5V`, `USB_DP`, ...). Same name = same net. Unused pins carry no-connect marks. It is a connection-correct schematic, not a pretty one; move parts and add real wires if you like.
* **Symbols are embedded**, drawn by the generator (so the file does not depend on a library). Pin numbers match the real footprints (`USB_C_Receptacle_HRO_TYPE-C-31-M-12`, `Jack_3.5mm_PJ320D_Horizontal`, `LQFP-48`) and, for U1, the CM108B datasheet rev 1.11 table (section 4.1). Replace them with library symbols later if you prefer (keep the pin numbers).
* **All pins are typed `passive`** to avoid a flood of false ERC errors. That also means ERC will not catch power-pin problems: add power flags and real pin types if you want a strict check.
* **Footprints** are assigned on each symbol, so the board can be updated from this schematic (Tools → Update PCB from Schematic) in KiCad.

## Verification so far
* My generator re-derived each pin's net from the labels and compared it with `rtvc_usbc.net`: 0 mismatches across all pins.
* The file re-loads with the `kiutils` Python parser (KiCad 6 format).
* **Not done:** opening it in KiCad, running ERC, or running "Update PCB from Schematic". Treat those as your first steps.
