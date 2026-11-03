"""SPICE simulation of the I2SBoard (ngspice via KiCad's libngspice). Values come from design.py.

What is simulated (the PCM1808 itself is modelled only by its analog input and its supply currents):
  1. input network: preamp output stage -> R4 -> C11 -> ADC input (DC, frequency response, level, start-up, tolerances)
  2. power path: USB-C -> PTC -> 5 V rail, analog 5 V filter, hot-plug
"""
import os, re, sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from design import PARTS
from spice import Ngspice

OUT = os.path.join(os.path.dirname(__file__), '..', 'sim')
P = {ref: value for ref, lib, sym, value, fp, nets in PARTS}

def num(v):
    m = re.match(r'([\d.]+)\s*(meg|[pnuµmkKM]?)', v)
    return float(m.group(1)) * {'': 1, 'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'µ': 1e-6, 'm': 1e-3, 'k': 1e3, 'K': 1e3, 'M': 1e6, 'meg': 1e6}[m.group(2)]

R4, C11, C13 = num(P['R4']), num(P['C11']), num(P['C13'])
RADC = 60e3          # PCM1808 input impedance per channel (datasheet, typical)
FB_R = 0.4           # ferrite bead DC resistance (assumed)

def ng_run(net, cmd):
    ng = Ngspice(); d, log = ng.run(net, cmd); return d

# ---------------------------------------------------------------- 1. input network
def input_net(r4=R4, c11=C11, c13=C13, radc=RADC, vcc=5.0, src='aux', amp=1.0, freq=1000.0, dc_step=False):
    """Preamp output -> this board's input -> ADC. src='aux': the preamp's AUX output (op-amp -> C13 1uF -> R9 1k, R10 100k to GND,
    0 V centred, no output filter), src='out': the preamp's OUT (op-amp -> 1k/4.7n -> 1k/4.7n, biased at 1.65 V).
    The ADC input is two channels in parallel, each radc to VREF = vcc/2 (+ 20 pF pin capacitance)."""
    L = ["* I2SBoard input", f"VCC vcc 0 {vcc}",
         "RVR vcc vref 1k", "RVR2 vref 0 1k", "CVREF vref 0 10.1u"]          # VREF = VCC/2 (about 500 ohm source, 10 uF + 100 nF)
    if dc_step:   # preamp bias appears at t=0 (worst case for the coupling capacitors)
        L.append("VB opout 0 PWL(0 0 1u 1.65)")
    else:
        L.append(f"VB opout 0 DC 1.65 SIN(1.65 {amp} {freq}) AC 1")
    if src == 'aux':
        L += ["C13p opout auxa 1u", "R10p auxa 0 100k", "R9p auxa pout 1k"]
    else:
        L += ["R5 opout f1 1k", "C11p f1 0 4.7n", "R6 f1 pout 1k", "C12p pout 0 4.7n"]
    L += [f"R4 pout g1 {r4}", f"C11 g1 ain {c11}", f"C13 ain 0 {c13}",
          f"RL ain vref {radc/2}", "CPIN ain 0 20p", ".end"]
    return "\n".join(L)

def edges(f, a, f0=1000.0):
    i0 = np.argmin(abs(f - f0)); ref = a[i0]
    lo = f[(f < f0)][::-1][np.argmax((a[(f < f0)][::-1] < ref - 3))]
    hi = f[(f > f0)][np.argmax(a[(f > f0)] < ref - 3)]
    return lo, hi

def power_net(vusb=5.0, i_vcc=11e-3, i_vdd=8e-3, i_preamp=6e-3, i_ldo_q=0.1e-3, hotplug=False, ripple=None, vf_scale=1.0, lfb=6e-6):
    """USB-C -> cable -> PTC -> +5V rail -> J1 (preamp), LDO, FB1 -> 5VA -> PCM1808 VCC."""
    L = ["* I2SBoard power", ".model DS D(IS=2e-6 N=1.1 RS=0.25 CJO=60p BV=40 M=0.5 VJ=0.5)",
         ".model DZ D(IS=1e-14 N=1 RS=2 BV=6.2 IBV=1m)"]
    if hotplug:
        L.append(f"VU usbsrc 0 PWL(0 0 10u {vusb})")
    elif ripple:
        L.append(f"VU usbsrc 0 DC {vusb} AC 1")
    else:
        L.append(f"VU usbsrc 0 DC {vusb}")
    L += ["RCAB usbsrc cab1 0.05", "LCAB cab1 vbus 1u",                       # cable resistance / inductance
          "RPTC vbus vbusf 0.15",                                              # PTC cold resistance (1206L050YR: 0.15 ohm typ)
          "D1a vbusf d1m DZ", "D1b 0 d1m DZ",                                  # TVS (bidirectional)
          "C1 vbusf c1x 10u", "RC1 c1x 0 5m", "C2 vbusf 0 100n",
          "RD3 vbusf rail 1m",                                                 # USB feeds the rail directly (no diode)
          f"IPRE rail 0 {i_preamp}",                                           # preamp (J1 pin 1)
          # LDO: ME6211C33, ideal 3.3 V with 100 mV dropout, Iq 100 uA
          f"BLDO rail l3 I={i_ldo_q}", "B3 v3p 0 V=(v(rail)>3.4) ? 3.3 : (v(rail)-0.1)", "R3 v3p v3 0.1",
          f"IVDD v3 0 {i_vdd}",
          f"RFB rail fbm {FB_R}", f"LFB fbm va {lfb}",                             # ferrite bead 600R@100MHz (about 6 uH equivalent)
          "C5 va c5x 10u", "RC5 c5x 0 5m", "C6 va 0 100n", "C9 va 0 100n",
          f"IVCC va 0 {i_vcc}", ".end"]
    return "\n".join(L)

def main():
    os.makedirs(OUT, exist_ok=True)
    rep = []; add = lambda k, v: rep.append((k, v))
    fig, ax = plt.subplots(2, 3, figsize=(17, 9))

    # ---- 1a. DC
    d = ng_run(input_net(), "op"); g = lambda k: float(np.real(d[k][0]))
    add("DC", f"VREF={g('vref'):.3f} V, ADC input AIN={g('ain'):.3f} V (mid-scale); the preamp AUX output is at {g('g1'):.3f} V, so C11 holds {g('ain')-g('g1'):.3f} V")

    # ---- 1b. AC
    d = ng_run(input_net(), "ac dec 80 0.5 5meg"); f = np.real(d['frequency'])
    a = 20 * np.log10(np.abs(d['ain'])); ap = 20 * np.log10(np.abs(d['pout']))
    i1k = np.argmin(abs(f - 1000)); lo, hi = edges(f, a); lo_p, hi_p = edges(f, ap)
    ratio = 10 ** (a[i1k] / 20)
    add("AC (preamp AUX -> ADC pin)", f"gain@1k = {ratio:.3f} ({a[i1k]:.2f} dB), -3 dB at {lo:.1f} Hz .. {hi/1e3:.1f} kHz "
        f"(preamp AUX output: C13 1 uF with R10 100k gives its own HPF; no output low-pass)")
    ax[0, 0].semilogx(f, a, label="ADC pin"); ax[0, 0].semilogx(f, ap, '--', label="preamp OUT")
    ax[0, 0].set(title="Response from the preamp op-amp output", xlabel="Hz", ylabel="dB", xlim=(0.5, 1e6), ylim=(-30, 3)); ax[0, 0].grid(True, which='both', alpha=.3); ax[0, 0].legend()

    # ---- 1c. level / headroom vs ADC full scale (0.6 x VCC)
    rows = []
    for vcc in (4.5, 4.7, 5.0, 5.5):
        d = ng_run(input_net(vcc=vcc), "ac lin 1 1000 1000")
        r = float(np.abs(d['ain'][0]) / np.abs(d['opout'][0]))
        fs = 0.6 * vcc
        rows.append(f"VCC {vcc:.1f} V: FS {fs:.2f} Vpp, preamp 3.3 Vpp -> {3.3*r:.2f} Vpp ({'OK' if 3.3*r <= fs else 'CLIPS by %.1f dB' % (20*np.log10(3.3*r/fs))})")
    add("Level", " | ".join(rows))
    # same with other R4 values (recommendation)
    rows = []
    for r4 in (4.7e3, 5.6e3, 6.8e3, 8.2e3):
        d = ng_run(input_net(r4=r4, vcc=4.5), "ac lin 1 1000 1000"); r = float(np.abs(d['ain'][0]) / np.abs(d['opout'][0]))
        d2 = ng_run(input_net(r4=r4), "ac dec 80 0.5 5meg"); f2 = np.real(d2['frequency']); a2 = 20*np.log10(np.abs(d2['ain'])); lo2, hi2 = edges(f2, a2)
        rows.append(f"R4={r4/1e3:.1f}k: 3.3 Vpp -> {3.3*r:.2f} Vpp at VCC 4.5 V (FS 2.70), HPF {lo2:.1f} Hz, LPF {hi2/1e3:.1f} kHz")
    add("R4 choice", "\n" + " " * 39 + ("\n" + " " * 39).join(rows))

    # ---- 1d. transient: start-up charge of the coupling capacitor
    d = ng_run(input_net(dc_step=True), "tran 1m 4")
    t = np.real(d['time']); y = np.real(d['ain'])
    v_end = y[-1]; step = abs(y - v_end)
    t_1mv = t[np.where(step > 1e-3)[0][-1]]; t_lsb = t[np.where(step > 3 / 2**24 * 1000)[0][-1]] if False else None
    # 24-bit step of a 3 Vpp scale is 0.18 uV; use 16-bit (46 uV) and 12-bit (0.7 mV) criteria
    t16 = t[np.where(step > 3 / 2**16)[0][-1]]; t12 = t[np.where(step > 3 / 2**12)[0][-1]]
    add("Start-up", f"ADC pin (preamp AUX output + coupling capacitors) settles to within 12-bit LSB after {t12*1e3:.0f} ms, 16-bit LSB after {t16*1e3:.0f} ms, within 1 mV after {t_1mv*1e3:.0f} ms (initial value {y[0]:.2f} V, final {v_end:.3f} V)")
    ax[0, 1].plot(t * 1e3, y); ax[0, 1].set(title="Start-up: ADC input after the preamp bias appears", xlabel="ms", ylabel="V"); ax[0, 1].grid(alpha=.3)

    # ---- 1e. large signal: 1 kHz, 1.4 V peak
    d = ng_run(input_net(amp=1.4), "tran 5u 40m"); t = np.real(d['time']); y = np.real(d['ain']); m = t > 0.02
    ax[0, 2].plot(t[m] * 1e3, y[m], label="ADC pin"); ax[0, 2].plot(t[m] * 1e3, np.real(d['opout'])[m], alpha=.5, label="preamp op-amp out")
    ax[0, 2].axhline(2.5 + 1.5, ls=':', c='r'); ax[0, 2].axhline(2.5 - 1.5, ls=':', c='r')
    ax[0, 2].set(title="1 kHz, preamp output 2.8 Vpp (red: ADC full scale at VCC 5 V)", xlabel="ms", ylabel="V"); ax[0, 2].grid(alpha=.3); ax[0, 2].legend(fontsize=8)
    add("Large signal", f"preamp 2.8 Vpp -> ADC pin {y[m].min():.2f} .. {y[m].max():.2f} V = {y[m].max()-y[m].min():.2f} Vpp around {y[m].mean():.2f} V")

    # ---- 1f. Monte Carlo (tolerance): R4 1 %, C11 10 %, ADC input 60k +-20 %, VCC 4.5..5.0
    rng = np.random.default_rng(1); G = []; HP = []
    for _ in range(100):
        d = ng_run(input_net(r4=R4 * rng.normal(1, 0.005), c11=C11 * rng.normal(1, 0.05), radc=RADC * rng.uniform(0.8, 1.2)), "ac dec 40 0.5 1meg")
        f = np.real(d['frequency']); a = 20 * np.log10(np.abs(d['ain'])); G.append(10 ** (a[np.argmin(abs(f - 1000))] / 20)); HP.append(edges(f, a)[0])
    G = np.array(G); HP = np.array(HP)
    add("Monte Carlo (100 runs)", f"gain@1k {G.min():.3f} .. {G.max():.3f} (mean {G.mean():.3f}), HPF {HP.min():.1f} .. {HP.max():.1f} Hz; "
        f"max swing {3.3*G.max():.2f} Vpp for a 3.3 Vpp preamp output")
    ax[1, 0].hist(G, bins=20); ax[1, 0].set(title="Gain at 1 kHz, 100 random tolerance runs", xlabel="gain"); ax[1, 0].grid(alpha=.3)

    # ---- 1g. noise of R4 (analytical)
    k, T = 1.38e-23, 300
    rs = R4 + 2000  # R4 plus preamp output resistors, (preamp output stage is lower noise), conservative
    vn = np.sqrt(4 * k * T * R4 * 20e3)
    add("Noise", f"thermal noise of R4 = {vn*1e6:.2f} uV rms in 20 kHz (9.6 nV/rtHz at 5.6k); the PCM1808 floor is about 15 uV rms (97 dB at 3 Vpp), so R4 is not significant")

    # ---- 2a. power rail DC
    for vusb in (5.0, 4.75):
        d = ng_run(power_net(vusb=vusb), "op"); g = lambda k: float(np.real(d[k][0]))
        add(f"Power DC, USB {vusb:.2f} V", f"VBUS_F={g('vbusf'):.3f}  +5V rail={g('rail'):.3f} V  5VA (ADC VCC)={g('va'):.3f} V  +3V3={g('v3'):.3f} V  "
            f"USB current={-g('vu#branch')*1e3:.1f} mA  -> ADC VCC {'OK (>=4.5 V)' if g('va') >= 4.5 else 'BELOW 4.5 V MINIMUM'}")
    # 96 kHz worst case
    d = ng_run(power_net(vusb=4.75, i_vcc=11e-3, i_vdd=10.2e-3, i_preamp=10e-3), "op")
    add("Power DC worst case", f"USB 4.75 V, ICC 11 mA, IDD 10.2 mA, preamp 10 mA: 5VA={float(np.real(d['va'][0])):.3f} V, rail={float(np.real(d['rail'][0])):.3f} V")

    # ---- 2b. supply ripple rejection to the ADC VCC pin
    d = ng_run(power_net(ripple=True), "ac dec 40 10 10meg"); f = np.real(d['frequency'])
    rej_va = 20 * np.log10(np.abs(d['va'])); rej_rail = 20 * np.log10(np.abs(d['rail']))
    pick = lambda fx: rej_va[np.argmin(abs(f - fx))]
    add("Ripple USB -> 5VA", f"attenuation: 1 kHz {pick(1e3):.1f} dB, 100 kHz {pick(1e5):.1f} dB, 1 MHz {pick(1e6):.1f} dB, 10 MHz {pick(1e7):.1f} dB (the PCM1808 and the preamp add their own supply rejection)")
    ax[1, 1].semilogx(f, rej_va, label="USB -> 5VA (ADC VCC)"); ax[1, 1].semilogx(f, rej_rail, '--', label="USB -> +5V rail")
    ax[1, 1].set(title="Supply ripple transfer", xlabel="Hz", ylabel="dB", ylim=(-90, 5)); ax[1, 1].grid(True, which='both', alpha=.3); ax[1, 1].legend()

    # ---- 2c. hot plug (ferrite bead L is not specified at low frequency: 6 uH pessimistic, 1.5 uH more typical)
    peaks = {}
    for lfb in (6e-6, 1.5e-6):
        d = ng_run(power_net(hotplug=True, lfb=lfb), "tran 0.2u 2m"); t = np.real(d['time'])
        peaks[lfb] = (np.real(d['vbusf']), np.real(d['rail']), np.real(d['va']))
    vb, rail, va = peaks[6e-6]
    add("Hot plug (5 V step, 1 uH cable)", f"VBUS_F peak {vb.max():.2f} V, rail peak {rail.max():.2f} V; 5VA (ADC VCC, abs. max 6.5 V) peak "
        f"{peaks[6e-6][2].max():.2f} V with a 6 uH bead model, {peaks[1.5e-6][2].max():.2f} V with 1.5 uH")
    ax[1, 2].plot(t * 1e3, vb, label="VBUS_F"); ax[1, 2].plot(t * 1e3, rail, label="+5V rail"); ax[1, 2].plot(t * 1e3, va, label="5VA (6 uH bead)")
    ax[1, 2].plot(t * 1e3, peaks[1.5e-6][2], ':', label="5VA (1.5 uH bead)")
    ax[1, 2].set(title="USB hot-plug", xlabel="ms", ylabel="V", xlim=(0, 0.5)); ax[1, 2].grid(alpha=.3); ax[1, 2].legend(fontsize=8)

    # ---- 3. clock plan (analytical)
    rows = []
    for fs in (44100, 48000, 96000):
        ok = [f"{r}fs={r*fs/1e6:.4f} MHz" for r in (256, 384, 512) if 2.048e6 <= r * fs <= 49.152e6 and (fs <= 48000 or r * fs <= 49.152e6)]
        rows.append(f"fs {fs/1e3:g} kHz: BCK={64*fs/1e6:.4f} MHz, MCLK " + ", ".join(ok))
    add("Clock plan", "\n" + " " * 39 + ("\n" + " " * 39).join(rows))

    plt.tight_layout(); plt.savefig(os.path.join(OUT, 'sim.png'), dpi=100)
    txt = "\n".join(f"{k:38s} {v}" for k, v in rep)
    open(os.path.join(OUT, 'results.txt'), 'w').write(txt + "\n"); print(txt)

if __name__ == '__main__':
    main()
