# -*- coding: utf-8 -*-
r"""CRI CPK 묶음 읽기 (2026-11-14, 소울칼리버 V PS3) — @UTF 표 · TOC(이름) / ITOC(번호) · CRILAYLA 풀기
  python tools/cpk.py list  <cpk>
  python tools/cpk.py x     <cpk> <출력 폴더> [이름 일부 ...]
형식 메모
  'CPK ' + 0x10 머리 → @UTF(CpkHeader: TocOffset·ContentOffset·EtocOffset·ItocOffset·Align·…)
  @UTF = '@UTF' u32 크기 | (0x08 기준) u32 행 위치 · u32 문자열 위치 · u32 데이터 위치 · u32 표 이름 · u16 열 수 · u16 행 길이 · u32 행 수 | 열 정의
    열 = u8 플래그(상위 4비트 저장: 0x10 0 · 0x30 상수 · 0x50 행마다, 하위 4비트 형: 0 u8 1 s8 2 u16 3 s16 4 u32 5 s32 6 u64 7 s64 8 f32 0xA 문자열 0xB 데이터) + u32 이름
  암호 표(@UTF 가 안 보임)는 XOR(m=0x655F, ×0x4115)
  파일 위치 = FileOffset + min(TocOffset, ContentOffset) (TOC 행 기준)
"""
import struct, sys, os


def _dec_utf(b):
    if b[:4] == b'@UTF':
        return b
    out = bytearray(len(b)); m = 0x655F
    for i, c in enumerate(b):
        out[i] = c ^ (m & 0xFF); m = (m * 0x4115) & 0xFFFFFFFF
    return bytes(out)


def utf_table(b):
    """@UTF 표 → (이름, [dict 행])"""
    b = _dec_utf(b)
    assert b[:4] == b'@UTF', b[:4]
    size = struct.unpack_from('>I', b, 4)[0]
    t = b[8:8 + size]
    rows_o, str_o, data_o, name_o = struct.unpack_from('>IIII', t, 0)
    ncol, rowlen, nrow = struct.unpack_from('>HHI', t, 16)

    def cstr(o):
        p = str_o + o
        return t[p:t.index(b'\0', p)].decode('utf-8', 'replace')

    FMT = {0: '>B', 1: '>b', 2: '>H', 3: '>h', 4: '>I', 5: '>i', 6: '>Q', 7: '>q', 8: '>f'}

    def read(typ, buf, p):
        if typ in FMT:
            v = struct.unpack_from(FMT[typ], buf, p)[0]; return v, struct.calcsize(FMT[typ])
        if typ == 0xA:
            return cstr(struct.unpack_from('>I', buf, p)[0]), 4
        if typ == 0xB:
            o, n = struct.unpack_from('>II', buf, p)
            return t[data_o + o:data_o + o + n], 8
        raise ValueError('형 %x' % typ)

    cols = []; p = 24
    for _ in range(ncol):
        fl = t[p]; nm = cstr(struct.unpack_from('>I', t, p + 1)[0]); p += 5
        st, typ = fl & 0xF0, fl & 0x0F
        const = None
        if st == 0x30:
            const, n = read(typ, t, p); p += n
        cols.append((nm, st, typ, const))
    rows = []
    for r in range(nrow):
        q = rows_o + r * rowlen; row = {}
        for nm, st, typ, const in cols:
            if st == 0x50:
                row[nm], n = read(typ, t, q); q += n
            elif st == 0x30:
                row[nm] = const
            else:
                row[nm] = None
        rows.append(row)
    return cstr(name_o), rows


def crilayla(b):
    """CRILAYLA 풀기 → 바이트"""
    assert b[:8] == b'CRILAYLA', b[:8]
    usize, hdr_off = struct.unpack_from('<II', b, 8)
    prefix = b[0x10 + hdr_off:0x10 + hdr_off + 0x100]
    out = bytearray(usize + 0x100)
    src = b[:0x10 + hdr_off]
    bits = 0; nbits = 0; pos = len(src) - 1           # 뒤에서 앞으로 읽는 비트열

    def get(n):
        nonlocal bits, nbits, pos
        v = 0
        while n:
            if nbits == 0:
                bits = src[pos]; pos -= 1; nbits = 8
            take = min(n, nbits)
            v = (v << take) | ((bits >> (nbits - take)) & ((1 << take) - 1))
            nbits -= take; n -= take
        return v
    w = usize + 0x100 - 1; end = 0x100
    while w >= end:
        if get(1):
            off = get(13) + 3
            ln = 3; lv = [2, 3, 5, 8]; i = 0
            while True:
                v = get(lv[min(i, 3)]); ln += v
                if v != (1 << lv[min(i, 3)]) - 1:
                    break
                i += 1
            for _ in range(ln):
                out[w] = out[w + off]; w -= 1
        else:
            out[w] = get(8); w -= 1
    out[:0x100] = prefix
    return bytes(out)


class Cpk:
    def __init__(self, path):
        self.path = path
        self.f = open(path, 'rb')
        h = self.f.read(0x10)
        assert h[:4] == b'CPK ', h[:4]
        n = struct.unpack_from('<I', h, 8)[0]
        _, rows = utf_table(self.f.read(n))
        self.hdr = rows[0]
        self.files = []
        toc = self.hdr.get('TocOffset') or 0; content = self.hdr.get('ContentOffset') or 0
        if toc:
            base = min(toc, content) if content else toc
            self.f.seek(toc); h = self.f.read(0x10); assert h[:4] == b'TOC ', h[:4]
            n = struct.unpack_from('<I', h, 8)[0]
            _, trows = utf_table(self.f.read(n))
            for r in trows:
                name = ((r.get('DirName') or '') + '/' + r['FileName']).lstrip('/')
                self.files.append(dict(name=name, off=r['FileOffset'] + base, size=r['FileSize'], usize=r['ExtractSize'], id=r.get('ID')))
        elif self.hdr.get('ItocOffset'):
            self.f.seek(self.hdr['ItocOffset']); h = self.f.read(0x10)
            n = struct.unpack_from('<I', h, 8)[0]
            _, irows = utf_table(self.f.read(n))
            align = self.hdr.get('Align') or 0x800
            ent = {}
            for key in ('DataL', 'DataH'):
                if irows[0].get(key):
                    for r in utf_table(irows[0][key])[1]:
                        ent[r['ID']] = r
            off = content
            for i in sorted(ent):
                r = ent[i]; sz = r['FileSize']
                self.files.append(dict(name='%05d' % i, off=off, size=sz, usize=r.get('ExtractSize') or sz, id=i))
                off += (sz + align - 1) // align * align

    def read(self, e):
        self.f.seek(e['off']); b = self.f.read(e['size'])
        if b[:8] == b'CRILAYLA':
            b = crilayla(b)
        return b


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    cmd, path = sys.argv[1], sys.argv[2]
    c = Cpk(path)
    if cmd == 'list':
        print('머리', {k: v for k, v in c.hdr.items() if not isinstance(v, bytes)})
        for e in c.files:
            print('%-50s %10d %10d @%x' % (e['name'], e['size'], e['usize'], e['off']))
        print(len(c.files), '개')
    elif cmd == 'x':
        out = sys.argv[3]; pats = sys.argv[4:]
        for e in c.files:
            if pats and not any(p in e['name'] for p in pats):
                continue
            b = c.read(e)
            p = os.path.join(out, *e['name'].split('/')); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'wb').write(b)
        print('풀었음')


if __name__ == '__main__':
    main()
