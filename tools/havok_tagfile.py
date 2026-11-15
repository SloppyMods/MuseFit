# MuseFit copy of XIVAutoFit builds/_e6022b/anim/tagfile.py (builds/ is not in git there; copied 2026-11-14). Changes: this header only.
# Minimal reader for Havok 2014 binary tagfiles (magic 1e0db0ca cefa11d0), enough for FFXIV .pap/.sklb.
import struct

T_VOID, T_BYTE, T_INT, T_REAL, T_VEC4, T_VEC8, T_VEC12, T_VEC16, T_OBJ, T_STRUCT, T_CSTR = range(11)
ARR, TUP = 0x10, 0x20
VECN = {T_VEC4: 4, T_VEC8: 8, T_VEC12: 12, T_VEC16: 16}


class Ref:
    def __init__(self, r, i): self.r, self.i = r, i
    def get(self): return self.r.objs[self.i] if self.i else None
    def __repr__(self): return "Ref(%d)" % self.i


class Reader:
    def __init__(self, d):
        assert d[:8] == bytes.fromhex("1e0db0cacefa11d0"), d[:8].hex()
        self.d, self.p = d, 8
        self.strings = ["", None]
        self.classes = [None]
        self.objs = [None]
        self.version = None

    def byte(self):
        b = self.d[self.p]; self.p += 1; return b

    def int(self):
        b = self.byte(); neg = b & 1; v = (b & 0x7F) >> 1; sh = 6
        while b & 0x80:
            b = self.byte(); v |= (b & 0x7F) << sh; sh += 7
        return -v if neg else v

    def str(self):
        n = self.int()
        if n > 0:
            s = self.d[self.p:self.p + n].decode("latin1"); self.p += n; self.strings.append(s); return s
        return self.strings[-n]

    def floats(self, n):
        v = struct.unpack_from("<%df" % n, self.d, self.p); self.p += 4 * n; return v

    def members(self, ci):
        c = self.classes[ci]; out = []
        if c["parent"]: out = self.members(c["parent"])
        return out + c["members"]

    def bits(self, n):
        nb = (n + 7) // 8; raw = self.d[self.p:self.p + nb]; self.p += nb
        return [(raw[i // 8] >> (i % 8)) & 1 for i in range(n)]

    def ref(self):
        return Ref(self, self.int())

    def object(self, remember=True, ci=None):
        if ci is None: ci = self.int()
        c = self.classes[ci]; o = {"__class__": c["name"]}
        if remember: self.objs.append(o)
        mem = self.members(ci); present = self.bits(len(mem))
        for (name, t, extra), pr in zip(mem, present):
            if pr: o[name] = self.value(t, extra)
        return o

    def value(self, t, extra):
        if t & ARR: return self.array(t & ~ARR, extra, self.int())
        if t & TUP: return self.array(t & ~TUP, extra[1], extra[0])
        if t == T_BYTE: return self.byte()
        if t == T_INT: return self.int()
        if t == T_REAL: return self.floats(1)[0]
        if t in VECN: return self.floats(VECN[t])
        if t == T_CSTR: return self.str()
        if t == T_OBJ: return self.ref()
        if t == T_STRUCT: return self.object(remember=False, ci=self.cindex(extra))
        raise ValueError(t)

    def cindex(self, name):
        for i, c in enumerate(self.classes):
            if c and c["name"] == name: return i
        raise KeyError(name)

    def array(self, t, extra, n):
        if t == T_BYTE:
            v = self.d[self.p:self.p + n]; self.p += n; return bytes(v)
        if t == T_INT:
            if self.version >= 3:
                sz = self.int()
                if sz == 0: return [0] * n
            return [self.int() for _ in range(n)]
        if t == T_REAL: return list(self.floats(n))
        if t in VECN:
            k = VECN[t]; f = self.floats(n * k); return [f[i * k:(i + 1) * k] for i in range(n)]
        if t == T_CSTR: return [self.str() for _ in range(n)]
        if t == T_OBJ: return [self.ref() for _ in range(n)]
        if t == T_STRUCT:
            ci = self.cindex(extra); mem = self.members(ci); present = self.bits(len(mem))
            out = [{"__class__": extra} for _ in range(n)]
            for (name, mt, mx), pr in zip(mem, present):
                if not pr: continue
                if mt & TUP:
                    vals = [self.array(mt & ~TUP, mx[1], mx[0]) for _ in range(n)]
                else:
                    vals = self.array(mt, mx, n)
                for o, v in zip(out, vals): o[name] = v
            return out
        if t & TUP:
            return [self.array(t & ~TUP, extra[1], extra[0]) for _ in range(n)]
        if t & ARR:
            return [self.array(t & ~ARR, extra, self.int()) for _ in range(n)]
        raise ValueError(("array", t))

    def read(self):
        root = None
        while True:
            tag = self.int()
            if tag == 1:
                self.version = self.int()
            elif tag == 2:
                name = self.str(); ver = self.int(); parent = self.int(); nm = self.int(); mem = []
                for _ in range(nm):
                    mn = self.str(); t = self.int(); extra = None
                    base = t & 0xF
                    if t & TUP:
                        cnt = self.int(); sub = self.str() if base in (T_OBJ, T_STRUCT) else None
                        extra = (cnt, sub)
                    elif base in (T_OBJ, T_STRUCT):
                        extra = self.str()
                    mem.append((mn, t, extra))
                self.classes.append({"name": name, "ver": ver, "parent": parent, "members": mem})
            elif tag in (3, 4):
                o = self.object(remember=(tag == 4))
                if root is None: root = o
            elif tag == 7:
                return root
            else:
                raise ValueError(("tag", tag, self.p))


def load(d):
    i = d.find(bytes.fromhex("1e0db0cacefa11d0"))
    return Reader(d[i:]).read()
