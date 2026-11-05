# RTVC USB-C Voice Module v0.1 (design package, not built)

A small USB audio module: **USB Type-C in**, **CM108B codec**, level attenuator, **3.5 mm TRRS jack out** to the phone. No HAT, no GPIO.

![USB-C module schematic](../../docs/usbc_schematic.png)

| File | Use |
|---|---|
| `rtvc_usbc.net` | KiCad netlist |
| `bom.csv` | Bill of materials |
| `../../docs/usbc_schematic.svg` | Schematic drawing |

## What is and is not finished
* **Finished from the USB Type-C spec:** receptacle wiring, 5.1 kΩ CC pull-downs (device), D+/D− tied across both rows, ESD part, VBUS filter and decoupling, attenuator and jack wiring.
* **Not finished: the CM108B (`U1`).** I could not reach the datasheet from the build session, so pin numbers, regulator/decoupling capacitors, mode/EEPROM pins and whether the headphone DC-blocking caps (`C6`/`C7`) are needed are **placeholders**. Pin names in the netlist are functional (DVDD, AVDD, DP, DM, HPOUTL, HPOUTR, DGND, AGND), not LQFP-48 pad numbers. Get the C-Media CM108B datasheet and complete `U1` before ordering a board. The CM119 needs its own datasheet.
* **Other assumptions to check:** the Type-C receptacle pad names (`A1B12`, `A4B9`, ...) follow KiCad's HRO TYPE-C-31-M-12 footprint, and the jack pad names (`TIP`, `RING1`, `RING2`, `SLEEVE`) are generic. Map them to the parts you pick.
* **Untested:** not opened in KiCad, not fabricated. The attenuator gain (about -41 dB) is a calculation.

## Connecting it
* **To the Pi:** USB-C to **USB-A** cable into a Pi USB-A port. The Pi's own USB-C port is power-input only; it cannot host this module. USB 2.0 is all that is needed.
* **To the phone:** a 4-pole male-male TRRS cable (CTIA) from `J2` to the phone's headset port, or the phone's USB-C/Lightning-to-3.5 mm adapter if it has no jack. If the far end hears nothing, try an OMTP/CTIA swap adapter.
* **Software:** `rtvc devices`, then set `output_device` to the module's name. The USB microphone stays on a separate Pi USB port.
* Calibrate with `rtvc tone --output-gain-db -30` and start at very low volume.
