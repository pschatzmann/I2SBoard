"""Tiny ctypes wrapper around libngspice (shipped with KiCad)."""
import ctypes as C, numpy as np

class VecInfo(C.Structure):
    _fields_ = [("v_name", C.c_char_p), ("v_type", C.c_int), ("v_flags", C.c_short),
                ("v_realdata", C.POINTER(C.c_double)), ("v_compdata", C.c_void_p), ("v_length", C.c_int)]

class NGComplex(C.Structure):
    _fields_ = [("re", C.c_double), ("im", C.c_double)]

class VecInfoAll(C.Structure):
    _fields_ = [("name", C.c_char_p), ("title", C.c_char_p), ("date", C.c_char_p), ("type", C.c_char_p),
                ("veccount", C.c_int), ("vecs", C.POINTER(C.POINTER(VecInfo)))]

SEND = C.CFUNCTYPE(C.c_int, C.c_char_p, C.c_int, C.c_void_p)
STAT = C.CFUNCTYPE(C.c_int, C.c_char_p, C.c_int, C.c_void_p)
EXIT = C.CFUNCTYPE(C.c_int, C.c_int, C.c_bool, C.c_bool, C.c_int, C.c_void_p)
DATA = C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_int, C.c_int, C.c_void_p)
INIT = C.CFUNCTYPE(C.c_int, C.c_int, C.c_int, C.c_void_p)
BGR = C.CFUNCTYPE(C.c_int, C.c_bool, C.c_int, C.c_void_p)

class Ngspice:
    def __init__(self):
        self.lib = C.CDLL('libngspice.so.0')
        self.log = []
        self._cb = (SEND(lambda s, i, u: (self.log.append(s.decode(errors='replace')), 0)[1]),
                    STAT(lambda s, i, u: 0), EXIT(lambda a, b, c, d, u: 0), DATA(lambda a, b, c, u: 0),
                    INIT(lambda a, b, u: 0), BGR(lambda a, b, u: 0))
        self.lib.ngSpice_Init(*self._cb, None)
        self.lib.ngGet_Vec_Info.restype = C.POINTER(VecInfo)
        self.lib.ngSpice_CurPlot.restype = C.c_char_p
        self.lib.ngSpice_AllVecs.restype = C.POINTER(C.c_char_p)

    def run(self, netlist, command):
        self.log.clear()
        lines = [l.encode() for l in netlist.splitlines()] + [None]
        arr = (C.c_char_p * len(lines))(*lines)
        self.lib.ngSpice_Circ(arr)
        self.lib.ngSpice_Command(command.encode())
        plot = self.lib.ngSpice_CurPlot().decode()
        out = {}
        vecs = self.lib.ngSpice_AllVecs(plot.encode())
        i = 0
        while vecs and vecs[i]:
            name = vecs[i].decode()
            info = self.lib.ngGet_Vec_Info(f"{plot}.{name}".encode()).contents
            n = info.v_length
            if info.v_realdata:
                out[name.lower()] = np.ctypeslib.as_array(info.v_realdata, shape=(n,)).copy()
            else:
                a = C.cast(info.v_compdata, C.POINTER(NGComplex))
                out[name.lower()] = np.array([complex(a[k].re, a[k].im) for k in range(n)])
            i += 1
        return out, "\n".join(self.log)
