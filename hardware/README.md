# Hardware files

| File | Use |
|---|---|
| `bom.csv` | Bill of materials (generic values, no prices or vendor part numbers) |
| `rtvc_attenuator.net` | KiCad netlist (resistors, capacitor, connectors with footprints) |
| `rtvc_attenuator.cir` | SPICE netlist for LTspice / ngspice (simulates the divider) |
| `../docs/schematic.svg` | Drawn schematic (human-readable) |

**Status:** the values were checked with a nodal AC calculation (about -41 dB, flat from 300 Hz). The files have **not** been opened in KiCad, LTspice or ngspice yet, and nothing has been built. Check the result in your tool, then verify the build with a multimeter and low volume.

## Pin map
* J1 (from USB adapter headphone-out): 1 = Tip (L), 2 = Ring (R), 3 = Sleeve (GND)
* J2 (to phone, CTIA TRRS): 1 = Sleeve (MIC), 2 = Ring2 (GND), 3 = Ring1 (R), 4 = Tip (L)
* J3 (optional monitor): 1 = L, 2 = R, 3 = GND
* C1: pin 1 (+) = MIC side (toward phone), pin 2 (-) = MIXED node

## KiCad
1. New project, open the PCB Editor.
2. File > Import > Netlist (or, in the schematic editor, redraw from the pin map above).
3. Select `rtvc_attenuator.net`. Footprints are standard KiCad library names (the connectors are screw terminals for wiring to jack breakouts, not jack footprints).
If KiCad complains about a footprint name, assign it manually from your library: the connection list is what matters.

## LTspice / ngspice
Open `rtvc_attenuator.cir`, run the `.ac` analysis, plot `V(mic)` in dB.
