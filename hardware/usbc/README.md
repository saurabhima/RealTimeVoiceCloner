# RTVC USB-C Voice Module v0.1 (design package, not built)

A small USB audio module: **USB Type-C in**, **CM108B codec**, level attenuator, **3.5 mm TRRS jack out** to the phone. No HAT, no GPIO.

![USB-C module schematic](../../docs/usbc_schematic.png)

| File | Use |
|---|---|
| `rtvc_usbc.net` | KiCad netlist |
| `bom.csv` | Bill of materials |
| `../../docs/usbc_schematic.svg` | Schematic drawing |

## What is and is not finished
* **Verified against the C-Media CM108B datasheet (rev 1.11):** U1's pin numbers (section 4.1) are in the netlist. Supply is 5 V (DVDD 35, AVDD 29/34). Straps: `MODE` (10) = GND for headset mode, `PWRSEL` (7) = GND for 500 mA bus power, `MSEL` (38) = GND (mixer off), `ADSEL` (22) and `TEST` (23) = GND. USB data on `USBDP` (41) / `USBDM` (42). The outputs are **line outs** `LOL` (30) / `LOR` (32), biased at 1.75 V DC, so DC-blocking capacitors C6/C7 are required. Full-scale output is 0.995 Vrms into 10 kΩ, so the -41 dB attenuator gives about 9 mV rms at full scale.
* **Finished from the USB Type-C spec:** receptacle wiring, 5.1 kΩ CC pull-downs (device), D+/D− tied across both rows, ESD part, VBUS filter, attenuator and jack wiring.
* **Open items the datasheet does not answer** (it has no application circuit): 
  1. Values of the capacitors on `DREG18` (8), `DREG33` (9), `AREG36` (37) and `VREF` (26). I assumed 4.7 µF each (C11–C14). Confirm against C-Media's reference design.
  2. Whether external USB D+ pull-up or series resistors are needed. None are added; the datasheet only says "only a few passive components are necessary".
  3. What `LOBS` (31, "DC 1.75 V output for line out bias") is meant to connect to. Left open.
* **Left unconnected on purpose:** `MICIN`, `VBIAS`, volume/mute pins (internal pull-ups), EEPROM pins (default USB descriptors), I2S, GPIO, SPDIF, LED pins, `PDSW`, N.C. pins 11 and 28.
* **Other assumptions to check:** the Type-C receptacle pad names (`A1B12`, `A4B9`, ...) follow KiCad's HRO TYPE-C-31-M-12 footprint, and the jack pad names (`TIP`, `RING1`, `RING2`, `SLEEVE`) are generic. The CM119 is not covered (different datasheet).
* **Untested:** not opened in KiCad, not fabricated. The attenuator gain (about -41 dB) is a calculation. The CM108B is a 0.5 mm-pitch LQFP-48: hand soldering is hard, so plan for hot-air or a fab assembly service.

## Connecting it
* **To the Pi:** USB-C to **USB-A** cable into a Pi USB-A port. The Pi's own USB-C port is power-input only; it cannot host this module. USB 2.0 is all that is needed.
* **To the phone:** a 4-pole male-male TRRS cable (CTIA) from `J2` to the phone's headset port, or the phone's USB-C/Lightning-to-3.5 mm adapter if it has no jack. If the far end hears nothing, try an OMTP/CTIA swap adapter.
* **Software:** `rtvc devices`, then set `output_device` to the module's name. The USB microphone stays on a separate Pi USB port.
* Calibrate with `rtvc tone --output-gain-db -30` and start at very low volume.
