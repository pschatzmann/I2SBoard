# I2SBoard: specification

An add-on board for the **GuitarPreAmp** or the **PiezoPreAmp** (one at a time). It digitises the preamp output with a stereo
I2S ADC (PCM1808) for an **ESP32** or **RP2040**. The microcontroller provides the master clock. A USB-C connector powers this
board and the preamp.

Board: **47 x 29 mm, the same outline as the preamp boards**, 2 layers, four M2.5 mounting holes (2.7 mm) at (3,3), (44,3), (3,26),
(44,26) (the same as the preamps), top-side SMD assembled by JLCPCB.

## Alignment with the preamp boards
- Same outline (47 x 29) and same four mounting holes, so the boards can be stacked on M2.5 standoffs.
- **J1 (5V, GND) sits at the position of pins 1 and 2 of the preamp's J2**: pin 1 at (41.5, 8.5) mm, vertical, pitch 2.54 mm.
  Pins 3 and 4 of the preamp's J2 (OUT, GND) are not used.
- **J2 (AUX, GND) sits at exactly the position of the preamp's J3** (its AUX output): pin 1 `AUX` at (28.0, 27.0) mm, pin 2 `GND` at
  (30.54, 27.0) mm, horizontal. Both preamp boards have J2 and J3 at the same places, so either one fits.
- Pin direction: on this board `5V` is an **output** (to the preamp's `5V` pin) and `AUX` is an **input** (from the preamp's `AUX OUT`).
- Mounting: preamp below, this board above, same orientation. Fit female sockets on this board's J1 and J2 (or male pins on both and
  short jumpers) so that they meet the preamp's J2 (pins 1-2) and J3. Everything on this board is on the top side, so only the header pins
  reach down. Use standoffs of 10 mm or more. The preamp's gain trimmer is covered when stacked: set it first.
  The preamp's J3 must be populated (it is not assembled by JLCPCB). Wires between the headers work as well.

## Layout (top view)
USB-C on the left edge, J1 (preamp power) on the right edge, PCM1808 in the centre; J3 (I2S), J2 (AUX in) and J5 (5V IN) on the bottom edge.

## Signal path
- The signal is taken from the preamp's **AUX output** (op-amp output -> 1 uF -> 1k, 100k to GND: 0 V centred, up to about +-1.65 V,
  no output low-pass filter). It suits the ADC better than the preamp's OUT: no bias to remove and no 13 kHz low-pass in front of the ADC.
- J2 `AUX` -> R4 5.6k -> C11 1 uF -> PCM1808 VINL **and** VINR (same signal on both channels, so either I2S slot works).
- The ADC input impedance is 60 kOhm per channel (30 kOhm together). With the preamp's R9 (1k) and R4, a 3.3 Vpp preamp swing becomes
  2.70 Vpp at the ADC pin (gain 0.82 at 1 kHz). The ADC full scale is 0.6 x VCC = 3 Vpp at 5 V (2.7 Vpp at 4.5 V).
- C11 couples the 0 V centred signal and lets the ADC set its own 2.5 V bias (VCC/2). C13 220 pF to GND at the ADC input: RF filter.
- The ADC has its own anti-alias filter (-3 dB at 1.3 MHz) and a digital filter.

## ADC and clocking
- PCM1808, TSSOP-14, 24-bit, up to 96 kHz, **slave mode**: MD1 = MD0 = low (tied to GND). BCK, LRCK and the system clock (SCKI)
  come from the microcontroller. FMT = low: I2S format (Philips), 24 bit.
- MCLK (SCKI) must be 256, 384 or 512 x fs, synchronous to LRCK (auto-detected). 64 BCK per frame (or 48 for 384 fs).
  Example: fs = 48 kHz, MCLK = 12.288 MHz (256 fs), BCK = 3.072 MHz. Other rates are in `sim/results.txt`.
- MCLK must be running before and during use. The ADC halts when MCLK or the LRCK relation stops.
- After power-up wait about 2 s before using samples (see Simulation: the coupling capacitors charge).

## Connectors (2.54 mm pin headers, hand-soldered, NOT assembled by JLCPCB)
- J1 (preamp power, 2 pins, right edge): `5V`, `GND` (the preamp's J2 pins 1 and 2)
- J2 (preamp signal, 2 pins, bottom edge, horizontal): `AUX`, `GND` (the preamp's J3 `AUX OUT`, `GND`)
- J3 (I2S, 6 pins, bottom edge, horizontal): `GND`, `MCLK`, `BCK`, `WS`, `DOUT`, `GND`. The board has **no power pin on this header**:
  it is powered by USB-C. Connect the GND of the microcontroller.
- J4 USB-C receptacle (assembled, left edge): power only, data pins unused. CC1 and CC2 have 5.1k pull-downs (sink).
- J5 (2 pins, bottom edge, optional): `5V IN` and `GND`, for an external 5 V module (for example a LiPo charger/boost module).
  The Schottky D4 stops the board's 5 V from feeding the module. **Use one source at a time** (USB or J5): the USB path has no diode,
  so a module above about 5.2 V could push a small current back into the USB port.

## Microcontroller wiring (3.3 V logic)
| J3 | Signal | ESP32 (example) | RP2040 (example) |
|---|---|---|---|
| MCLK | master clock, input to the board | I2S MCLK output | PIO / clock output |
| BCK | bit clock, input | I2S BCLK | PIO side-set pin |
| WS | word select / LRCK, input | I2S WS | PIO side-set pin + 1 |
| DOUT | data, output of the board | I2S DIN | PIO `in` pin |
| GND | ground | GND | GND |
The pins are free to choose in firmware. DOUT has a 33 Ohm series resistor.

## Power
- USB-C VBUS -> 500 mA PTC (F1) -> **+5 V** rail (5 V ESD diode D1, 10 uF + 100 nF). The rail equals the USB voltage minus a few mV.
- J5 -> Schottky D4 -> the same rail (about 0.2 V lower than the module output).
- +5 V -> **J1 pin 1**: powers the preamp (a few mA; the preamp has its own regulator).
- +5 V -> ferrite bead FB1 -> **5VA** (10 uF + 100 nF) -> PCM1808 VCC (analog 5 V).
- +5 V -> ME6211C33M5 LDO (U1) -> **+3V3** (10 uF + 100 nF) -> PCM1808 VDD (digital 3.3 V).
- Green LED (D2) shows that the 5 V rail is on. Total current about 17 mA (up to about 30 mA at 96 kHz).
- Do not connect the board's 5 V to a 3.3 V pin. If the microcontroller is also on USB, only the grounds are shared.

## Bill of materials (LCSC numbers looked up 2026-11-03, re-check stock when ordering)
| Ref | Value | Package | LCSC |
|---|---|---|---|
| U2 | PCM1808PWR stereo ADC | TSSOP-14 | C55513 |
| U1 | ME6211C33M5 LDO 3.3 V | SOT-23-5 | C82942 |
| J4 | USB-C receptacle HRO TYPE-C-31-M-12 | SMD | C165948 |
| F1 | PTC resettable fuse 500 mA (Littelfuse 1206L050YR) | 1206 | C163512 |
| D1 | CDSOD323-T05C bidirectional 5 V ESD diode | SOD-323 | C711706 |
| D4 | B5819W Schottky | SOD-123 | C64885 |
| D2 | LED KT-0603YG (yellow-green) | 0603 | C2289 |
| FB1 | ferrite 600R @ 100 MHz | 0603 | C19330 |
| C1, C3, C5, C8 | 10 uF | 0805 | C15850 |
| C2, C7, C9, C10 | 100 nF | 0603 | C1591 |
| C11 | 1 uF | 0603 | C15849 |
| C13 | 220 pF C0G | 0603 | C156398 |
| R1, R2 | 5.1k | 0603 | C23186 |
| R3 | 1k | 0603 | C21190 |
| R4 | 5.6k | 0603 | C23189 |
| R6 | 33R | 0603 | C23140 |

Notes: the USB-C connector and the PCM1808 are probably extended parts (fee). The LED C2289 is yellow-green; the Kento KT-0603G
(C12624) is emerald green. Check stock, extended-part fees and part rotations (SOT-23-5, TSSOP-14, USB-C, diodes) in the 3D preview.

## Simulation (`python3 tools/sim.py`; results in `sim/results.txt`, plots in `sim/sim.png`)
ngspice through KiCad's libngspice. Netlist values come from `design.py`. The PCM1808 is modelled only by its analog input
(60 kOhm to VCC/2 per channel) and its supply currents; its internal behaviour, the I2S timing and the MCU are **not** simulated.
The preamp is an ideal op-amp output followed by the preamp's AUX network (1 uF, 100k to GND, 1k). The supply model uses a
USB cable of 0.05 Ohm + 1 uH, the PTC at 0.15 Ohm, and an assumed ferrite bead (0.4 Ohm, 6 uH or 1.5 uH).
- DC: ADC pin 2.500 V; the preamp AUX output is at 0 V, so C11 holds 2.5 V.
- Gain from the preamp op-amp output to the ADC pin: 0.82 at 1 kHz; **-3 dB from 9.4 Hz to 126 kHz** (the HPF is the preamp's 1 uF / 100k
  together with C11; the ADC's own filters limit the top end).
- Level: 3.3 Vpp from the preamp gives 2.70 Vpp at the ADC pin. Full scale is 0.6 x VCC = 2.70 Vpp at VCC 4.5 V and 3.0 Vpp at 5 V, so it does not clip
  over the VCC range. (With R4 = 4.7k it clipped by 0.2 dB at 4.5 V, hence 5.6k.) With tolerances (100 random runs) the gain is 0.78 to 0.84
  (2.79 Vpp maximum), HPF 7.9 to 11.2 Hz. A swing of 3.3 Vpp only occurs when the preamp itself clips.
- Start-up: the preamp's AUX coupling capacitor charges through its 100k and C11 through the ADC input. The ADC pin settles to 12-bit accuracy in
  about 1.1 s and to 16-bit accuracy in about 1.7 s. Discard the first 2 s of samples.
- R4 noise 1.4 uV rms (20 kHz): negligible against the ADC floor (about 15 uV rms).
- Power: USB 5.00 V gives rail 4.997 V, 5VA 4.992 V, 3.3 V rail 3.299 V, 17 mA. At the USB minimum of 4.75 V: 5VA 4.74 V (limit 4.5 V). Worst case
  (96 kHz, ADC max currents, preamp 10 mA): 5VA 4.74 V. (An earlier version with a Schottky in the USB path gave 4.48 V here, below
  the limit; that diode was removed.)
- Ripple: the bead and 10 uF filter only act above about 20 kHz (-37 dB at 100 kHz). At audio frequencies the USB ripple reaches the ADC supply
  without attenuation, so the PCM1808's own supply rejection and a clean USB supply matter. If that becomes an issue, power VCC from the LDO instead.
- Hot plug (5 V step, 1 uH cable): rail peaks at 5.39 V (clamped by D1, 6.2 V model); 5VA peaks at 5.37 V (1.5 uH bead) or 6.34 V
  (pessimistic 6 uH bead), against an absolute maximum of 6.5 V for VCC.

## Files
- `kicad/I2SBoard.kicad_sch`, `kicad/I2SBoard.kicad_pcb`: KiCad 9 project (generated)
- `fab/I2SBoard_gerber.zip`, `fab/BOM.csv`, `fab/CPL.csv`: JLCPCB order package
- `tools/design.py`: single source of truth (parts, nets, positions, LCSC numbers)
- `tools/Local.kicad_sym`: PCM1808 symbol (not in the KiCad library)
- `tools/gen_sch.py`, `tools/route.sh` (board + Freerouting + DRC), `tools/export_jlc.py`, `tools/sim.py`, `tools/spice.py`
- Edit `design.py` and regenerate; do not edit the `.kicad_*` files by hand.
- After `route.sh`, check that the default netclass clearance in `kicad/I2SBoard.kicad_pro` is 0.15 mm (the USB-C pads need it).

## Status
Untested design. Checked: KiCad design-rule check (0 errors, 0 unconnected; remaining items are silkscreen warnings), outline, holes and the J1 / J2
positions against the preamp boards, simulation of the analog input and power path.
Not done: simulation of the PCM1808 and I2S timing, 3D rotation check of the assembly parts, a real test with an ESP32 / RP2040.
Verify on the first board: MCLK / LRCK ratio at your sample rate, no clipping at maximum preamp output, USB rail voltage under load, the
fit of J1 / J2 onto the preamp's J2 and J3 (stack height), and the ripple on the analog supply.
