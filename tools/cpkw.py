# -*- coding: utf-8 -*-
r"""CRI CPK 쓰기 (2026-11-15, 소울칼리버 V PS3 — ITOC(번호만) 묶음 전용)
  python tools/cpkw.py selftest <cpk>                       원본을 그대로 다시 쌓아 바이트 같은지
  python tools/cpkw.py build <원본 cpk> <출력 cpk> <바꿀 폴더>  폴더 안 «00122» 같은 번호 이름 파일로 갈아 끼움(무압축으로)
방식
  · @UTF 표를 원본 열 정의(플래그·순서·상수) 그대로 다시 직렬화 — 문자열 표 순서 «<NULL>, 표 이름, 열 이름…, 값…»
  · 파일 자료는 ContentOffset 부터 번호 순, Align 0x800. 바꾼 파일은 CRILAYLA 없이 날것(FileSize = ExtractSize)
  · ITOC: 크기가 u16 에 들면 DataL, 아니면 DataH (원본 규칙). 머리 ContentSize·EnabledPackedSize·EnabledDataSize·ItocSize 갱신
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cpk

FMT = {0: '>B', 1: '>b', 2: '>H', 3: '>h', 4: '>I', 5: '>i', 6: '>Q', 7: '>q', 8: '>f'}


def parse(b):
    """@UTF → dict(name, cols=[(이름, 플래그, 상수)], rows=[dict])"""
    b = cpk._dec_utf(b)
    size = struct.unpack_from('>I', b, 4)[0]; t = b[8:8 + size]
    rows_o, str_o, data_o, name_o = struct.unpack_from('>IIII', t, 0)
    ncol, rowlen, nrow = struct.unpack_from('>HHI', t, 16)
    cs = lambda o: t[str_o + o:t.index(b'\0', str_o + o)].decode('utf-8')
    def rd(typ, buf, p):
        if typ in FMT: return struct.unpack_from(FMT[typ], buf, p)[0], struct.calcsize(FMT[typ])
        if typ == 0xA: return cs(struct.unpack_from('>I', buf, p)[0]), 4
        if typ == 0xB:
            o, n = struct.unpack_from('>II', buf, p); return bytes(t[data_o + o:data_o + o + n]), 8
        raise ValueError(typ)
    cols = []; p = 24
    for _ in range(ncol):
        fl = t[p]; nm = cs(struct.unpack_from('>I', t, p + 1)[0]); p += 5; const = None
        if fl & 0xF0 == 0x30: const, n = rd(fl & 15, t, p); p += n
        cols.append((nm, fl, const))
    rows = []
    for r in range(nrow):
        q = rows_o + r * rowlen; row = {}
        for nm, fl, const in cols:
            if fl & 0xF0 == 0x50: row[nm], n = rd(fl & 15, t, q); q += n
        rows.append(row)
    return dict(name=cs(name_o), cols=cols, rows=rows, raw=b[:8 + size], total=len(b))


def build(tab, pad_to=None):
    """dict → @UTF 바이트(원본처럼 8 바이트 머리 포함). pad_to = 원본 전체 길이(뒤 0 채움)를 맞출 때"""
    strs = ['<NULL>', tab['name']]
    def sid(s):
        if s not in strs: strs.append(s)
    for nm, fl, const in tab['cols']:
        sid(nm)
        if fl & 15 == 0xA and const is not None: sid(const)
    for r in tab['rows']:
        for nm, fl, _ in tab['cols']:
            if fl & 0xF0 == 0x50 and fl & 15 == 0xA: sid(r[nm])
    soff = {}; sb = bytearray()
    for s in strs: soff[s] = len(sb); sb += s.encode('utf-8') + b'\0'
    data = bytearray(); doff = []
    def put(typ, v):
        if typ in FMT: return struct.pack(FMT[typ], v)
        if typ == 0xA: return struct.pack('>I', soff[v])
        if typ == 0xB:
            if v is None: return struct.pack('>II', 0, 0)
            o = len(data); data.extend(v); return struct.pack('>II', o, len(v))
        raise ValueError(typ)
    colb = bytearray()
    for nm, fl, const in tab['cols']:
        colb += bytes([fl]) + struct.pack('>I', soff[nm])
        if fl & 0xF0 == 0x30: colb += put(fl & 15, const)
    rowb = bytearray(); rowlen = 0
    for r in tab['rows']:
        one = bytearray()
        for nm, fl, _ in tab['cols']:
            if fl & 0xF0 == 0x50: one += put(fl & 15, r[nm])
        rowlen = len(one); rowb += one
    head_len = 24 + len(colb)
    rows_o = head_len; str_o = rows_o + len(rowb)
    data_o = (str_o + len(sb) + 7) & ~7          # 원본 CRI: 문자열 뒤 8 바이트 정렬, 자료 없으면 그 자리 = 표 끝
    body = bytearray(struct.pack('>IIII', rows_o, str_o, data_o, soff[tab['name']]) + struct.pack('>HHI', len(tab['cols']), rowlen, len(tab['rows'])))
    body += colb + rowb + sb
    body += b'\0' * (data_o - len(body)) + data
    body += b'\0' * ((-len(body)) % 8)
    body = bytes(body)
    size = len(body)
    out = b'@UTF' + struct.pack('>I', size) + body
    if pad_to and len(out) < pad_to: out += b'\0' * (pad_to - len(out))
    return out


def chunk(path, off):
    f = open(path, 'rb'); f.seek(off); h = f.read(0x10); n = struct.unpack_from('<I', h, 8)[0]
    return h, f.read(n)


def rebuild(src, dst, repl=None, log=print):
    """repl = {번호: 새 바이트(풀린 것)}. 나머지는 원본 바이트(압축 그대로) 복사"""
    repl = repl or {}
    c = cpk.Cpk(src); f = c.f
    h0, hb = chunk(src, 0); H = parse(hb)
    hi, ib = chunk(src, c.hdr['ItocOffset']); I = parse(ib)
    L = parse(I['rows'][0]['DataL']) if I['rows'][0].get('DataL') else None
    Hh = parse(I['rows'][0]['DataH']) if I['rows'][0].get('DataH') else None
    align = c.hdr['Align']; cofs = c.hdr['ContentOffset']
    ents = []; packed = 0; ext = 0
    for e in c.files:
        if e['id'] in repl:
            b = repl[e['id']]; ents.append((e['id'], b, len(b), len(b)))
        else:
            f.seek(e['off']); b = f.read(e['size']); ents.append((e['id'], b, e['size'], e['usize']))
    lrows = []; hrows = []
    for i, b, fs, es in ents:
        (lrows if fs <= 0xFFFF and es <= 0xFFFF else hrows).append(dict(ID=i, FileSize=fs, ExtractSize=es))
        packed += fs; ext += es
    # 원본 표 열 형식(L = u16 ID·u16 크기, H = u16 ID·u32 크기) 그대로
    def sub(T, rows, orig_len):
        if T is None: return None
        T = dict(T); T['rows'] = rows; return build(T)
    nL = sub(L, lrows, None); nH = sub(Hh, hrows, None)
    I2 = dict(I); r0 = dict(I['rows'][0]); r0['FilesL'] = len(lrows); r0['FilesH'] = len(hrows)
    r0['DataL'] = nL; r0['DataH'] = nH; I2['rows'] = [r0]
    ib2 = build(I2)
    # 자료 쓰기
    body = bytearray(); offs = []
    for i, b, fs, es in ents:
        offs.append(len(body)); body += b
        if (i, b) != (ents[-1][0], ents[-1][1]):
            body += b'\0' * ((-len(body)) % align)
    content_size = len(body)
    itoc_off = c.hdr['ItocOffset']
    assert itoc_off + 0x10 + len(ib2) <= cofs, ('ITOC 이 자료 시작을 넘음', hex(itoc_off + 0x10 + len(ib2)), hex(cofs))
    H2 = dict(H); hr = dict(H['rows'][0])
    hr['ItocSize'] = 0x10 + len(ib2)
    # 원본 4개(text·cdata·cpudata·human)에서 확인한 규칙: ContentSize = 파일마다 Align 올림 합(마지막 포함)
    #   EnabledPackedSize = ExtractSize 합 · EnabledDataSize = FileSize 합(이름과 반대지만 원본이 그럼)
    hr['ContentSize'] = sum((fs + align - 1) // align * align for _, _, fs, _ in ents)
    hr['EnabledPackedSize'] = ext
    hr['EnabledDataSize'] = packed
    H2['rows'] = [hr]
    hb2 = build(H2, pad_to=len(hb))
    f.seek(0); out = bytearray(f.read(cofs))            # 머리~자료 시작 원본 그대로(머리 뒤 4 바이트 75 54 F5 DD·«(c)CRI» 보존)
    assert len(hb2) == len(hb)
    out[0:0x10 + len(hb2)] = h0[:8] + struct.pack('<I', len(hb2)) + h0[12:16] + hb2
    blk = hi[:8] + struct.pack('<I', len(ib2)) + hi[12:16] + ib2
    old_end = itoc_off + 0x10 + len(ib)
    out[itoc_off:max(old_end, itoc_off + len(blk))] = blk + b'\0' * max(0, old_end - itoc_off - len(blk))
    assert len(out) == cofs, (hex(len(out)), hex(cofs))
    out += body
    open(dst, 'wb').write(out)
    log('%s → %s · 파일 %d(바꿈 %d) · L %d H %d · 크기 %d' % (os.path.basename(src), dst, len(ents), len(repl), len(lrows), len(hrows), len(out)))
    return dst


def selftest(src):
    h0, hb = chunk(src, 0); H = parse(hb)
    ok = build(H, pad_to=len(hb)) == hb
    print('머리 표 다시 쌓기 같음:', ok)
    c = cpk.Cpk(src)
    hi, ib = chunk(src, c.hdr['ItocOffset']); I = parse(ib)
    print('ITOC 표 같음:', build(I, pad_to=len(ib)) == ib, len(build(I)), len(ib))
    for k in ('DataL', 'DataH'):
        raw = I['rows'][0].get(k)
        if raw: print(' ', k, '같음:', build(parse(raw)) == raw, len(build(parse(raw))), len(raw))
    tmp = os.path.join(os.environ.get('TEMP', '.'), 'cpkw_selftest.cpk')
    rebuild(src, tmp)
    a = open(src, 'rb').read(); b = open(tmp, 'rb').read()
    print('전체 같음:', a == b, len(a), len(b))
    if a != b:
        d = next(i for i in range(min(len(a), len(b))) if a[i] != b[i]); print('첫 다름 @%X' % d, a[d - 8:d + 8].hex(' '), '|', b[d - 8:d + 8].hex(' '))
    os.remove(tmp)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1] == 'selftest': selftest(sys.argv[2])
    elif sys.argv[1] == 'build':
        src, dst, d = sys.argv[2:5]
        repl = {int(n): open(os.path.join(d, n), 'rb').read() for n in os.listdir(d) if n.isdigit()}
        rebuild(src, dst, repl)


if __name__ == '__main__':
    main()
