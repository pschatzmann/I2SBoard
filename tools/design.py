"""Single source of truth for the I2SBoard (schematic + PCB are generated from this).

Stereo I2S ADC (PCM1808) for the GuitarPreAmp or PiezoPreAmp, USB-C powered.
Board outline, mounting holes and the J1 connector match the preamp boards exactly (47 x 29 mm, 4 holes, J1 = preamp J2).
"""

R0603 = "Resistor_SMD:R_0603_1608Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
HDR = "Connector_PinHeader_2.54mm:PinHeader_1x0%d_P2.54mm_Vertical"

# ref, library, symbol, value, footprint, {pin number: net}
# Nets named GND / +5V / +3V3 become power symbols in the schematic.
PARTS = [
    # --- preamp power: pins 1-2 of the preamp's J2 (pin 1 at 41.5/8.5). Pins 3-4 (OUT, GND) are not used. ---
    ("J1", "Connector_Generic", "Conn_01x02", "PREAMP 5V/GND", HDR % 2, {"1": "+5V", "2": "GND"}),
    # --- preamp signal: the preamp's AUX output (its J3: AUX_OUT, GND, pin 1 at 28.0/27.0, horizontal) ---
    ("J2", "Connector_Generic", "Conn_01x02", "AUX IN/GND", HDR % 2, {"1": "AUX_IN", "2": "GND"}),
    # --- I2S to the microcontroller (MCLK is an input: the MCU provides it) ---
    ("J3", "Connector_Generic", "Conn_01x06", "I2S GND/MCLK/BCK/WS/DOUT/GND", HDR % 6,
     {"1": "GND", "2": "MCLK", "3": "BCK", "4": "WS", "5": "DOUT_C", "6": "GND"}),
    # --- power input ---
    ("J4", "Connector", "USB_C_Receptacle_USB2.0_16P", "USB-C (power only)",
     "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
     {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND",
      "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS", "A5": "CC1", "B5": "CC2"}),
    ("J5", "Connector_Generic", "Conn_01x02", "5V IN / GND (optional module)", HDR % 2, {"1": "EXT5V", "2": "GND"}),
    ("R1", "Device", "R", "5.1k", R0603, {"1": "CC1", "2": "GND"}),
    ("R2", "Device", "R", "5.1k", R0603, {"1": "CC2", "2": "GND"}),
    ("F1", "Device", "Polyfuse", "500mA PTC", "Fuse:Fuse_1206_3216Metric", {"1": "VBUS", "2": "+5V"}),
    ("D1", "Device", "D_TVS", "CDSOD323-T05C", "Diode_SMD:D_SOD-323", {"1": "+5V", "2": "GND"}),
    ("C1", "Device", "C", "10uF", C0805, {"1": "+5V", "2": "GND"}),
    ("C2", "Device", "C", "100nF", C0603, {"1": "+5V", "2": "GND"}),
    # optional external 5 V module (J5): the Schottky stops the rail from feeding the module
    ("D4", "Device", "D_Schottky", "B5819W", "Diode_SMD:D_SOD-123", {"1": "+5V", "2": "EXT5V"}),
    ("R3", "Device", "R", "1k", R0603, {"1": "+5V", "2": "LEDA"}),
    ("D2", "Device", "LED", "green", "LED_SMD:LED_0603_1608Metric", {"1": "GND", "2": "LEDA"}),
    # --- 3.3 V digital rail and filtered 5 V analog rail ---
    ("U1", "Regulator_Linear", "ME6211C33M5", "ME6211C33M5", "Package_TO_SOT_SMD:SOT-23-5",
     {"1": "+5V", "2": "GND", "3": "+5V", "5": "+3V3"}),
    ("C3", "Device", "C", "10uF", C0805, {"1": "+3V3", "2": "GND"}),
    ("FB1", "Device", "FerriteBead", "600R@100MHz", "Inductor_SMD:L_0603_1608Metric", {"1": "+5V", "2": "5VA"}),
    ("C5", "Device", "C", "10uF", C0805, {"1": "5VA", "2": "GND"}),
    # --- ADC ---
    ("U2", "Local", "PCM1808", "PCM1808PWR", "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
     {"1": "VREF", "2": "GND", "3": "5VA", "4": "+3V3", "5": "GND", "6": "MCLK", "7": "WS", "8": "BCK",
      "9": "DOUT", "10": "GND", "11": "GND", "12": "GND", "13": "AIN", "14": "AIN"}),
    ("C7", "Device", "C", "100nF", C0603, {"1": "VREF", "2": "GND"}),
    ("C8", "Device", "C", "10uF", C0805, {"1": "VREF", "2": "GND"}),
    ("C9", "Device", "C", "100nF", C0603, {"1": "5VA", "2": "GND"}),
    ("C10", "Device", "C", "100nF", C0603, {"1": "+3V3", "2": "GND"}),
    ("R6", "Device", "R", "33R", R0603, {"1": "DOUT", "2": "DOUT_C"}),
    # --- input from the preamp AUX output (0 V centred, AC coupled): 4.7k + 2x60k (both ADC channels), 1uF sets the ADC's 2.5 V bias ---
    ("R4", "Device", "R", "5.6k", R0603, {"1": "AUX_IN", "2": "G1"}),
    ("C11", "Device", "C", "1uF", C0603, {"1": "G1", "2": "AIN"}),
    ("C13", "Device", "C", "220pF", C0603, {"1": "AIN", "2": "GND"}),
]

PWR_FLAGS = [("VBUS", "J4", "A4"), ("GND", "J4", "A1"), ("+5V", "C1", "1"), ("5VA", "C5", "1"), ("EXT5V", "J5", "1")]
NC_PARTS = {"J4"}   # unused pins get a no-connect flag

# ---- board layout (mm, relative to the board corner) ----
OX, OY, W, H = 100.0, 100.0, 47.0, 29.0
SX, SY = 0.0, 0.0
# Same outline (47 x 29), same four M2.5 holes and same connector positions as the preamp boards: J1 = pins 1-2 of the
# preamp's J2 (5V, GND; pin 1 at 41.5 / 8.5, vertical), J2 = the preamp's J3 (AUX, GND; pin 1 at 28.0 / 27.0, horizontal). Mount this board on standoffs above the preamp.
POS = {
    "J1": (41.5, 8.5, 0), "J2": (28.0, 27.0, 90), "J3": (10.0, 27.0, 90), "J5": (35.0, 27.0, 90),
    "J4": (3.2, 14.5, 270),
    "U2": (26.0, 11.0, 270),
    "R4": (31.5, 23.0, 0), "C11": (31.5, 20.0, 0), "C13": (29.5, 17.0, 90),
    "C7": (30.0, 6.0, 90), "C8": (33.0, 3.8, 0), "C9": (27.5, 4.8, 90), "C10": (23.0, 5.0, 90),
    "R6": (22.0, 17.0, 0),
    "U1": (17.0, 10.5, 0), "C3": (20.5, 11.5, 90),
    "FB1": (19.0, 3.0, 0), "C5": (14.0, 3.0, 0),
    "R1": (10.3, 13.3, 90), "R2": (10.3, 16.3, 90), "F1": (14.5, 21.5, 0), "D1": (10.5, 21.5, 0),
    "C1": (18.5, 20.5, 0), "C2": (22.0, 20.5, 0), "D4": (35.5, 21.0, 0),
    "R3": (12.5, 6.5, 0), "D2": (9.5, 6.5, 0),
}
HOLES = [(3, 3), (44, 3), (3, 26), (44, 26)]   # the preamp's four M2.5 holes

# not assembled by JLCPCB (hand-soldered)
NOT_ASSEMBLED = {"J1", "J2", "J3", "J5"}

# LCSC part numbers (looked up on lcsc.com / jlcpcb.com 2026-11-03; re-check stock when ordering)
LCSC = {
    "C1": "C15850", "C3": "C15850", "C5": "C15850", "C8": "C15850",                    # 10uF 0805
    "C2": "C1591", "C7": "C1591", "C9": "C1591", "C10": "C1591",                       # 100nF 0603
    "C11": "C15849",                                                                   # 1uF 0603
    "C13": "C156398",                                                                  # 220pF C0G 0603
    "R1": "C23186", "R2": "C23186",                                                    # 5.1k 0603
    "R3": "C21190",                                                                    # 1k 0603
    "R4": "C23189",                                                                    # 5.6k 0603
    "R6": "C23140",                                                                    # 33R 0603
    "F1": "C163512",                                                                   # Littelfuse 1206L050YR 500mA PTC
    "D1": "C711706",                                                                   # CDSOD323-T05C
    "D2": "C2289",                                                                     # KT-0603YG LED (yellow-green); C12624 is KT-0603G
    "D4": "C64885",                                                                    # B5819W SOD-123 Schottky
    "J4": "C165948",                                                                   # HRO TYPE-C-31-M-12
    "U1": "C82942",                                                                    # ME6211C33M5G-N
    "FB1": "C19330",                                                                   # 600R@100MHz 0603
    "U2": "C55513",                                                                    # PCM1808PWR TSSOP-14
}

# silkscreen labels: text, x, y, size
SILK = ([("OUT", 38.0, 7.85, 0.8), ("5V", 38.0, 9.15, 0.8), ("GND", 38.0, 11.04, 0.8)] +
        [(n, 10.0 + i * 2.54, 24.0 + (i % 2) * 1.3, 0.8) for i, n in enumerate(["GND", "MCLK", "BCK", "WS", "DOUT", "GND"])] +
        [("IN", 28.0, 23.3, 0.8), ("AUX", 28.0, 24.6, 0.8), ("GND", 30.7, 24.6, 0.8), ("IN", 35.0, 23.3, 0.8), ("5V", 35.0, 24.6, 0.8), ("GND", 37.54, 24.6, 0.8)])
