# -*- coding: utf-8 -*-
"""소울칼리버 IV 글 표(평문) 풀기·짜기 + regtext 묶음(.dtp) 풀기·짜기.

표 = u32 언어 · u32 항목 수 · u32 오프셋 × 항목 수(문자열 구역 기준) · UTF-8 문자열(NUL 끝)
묶음 = u32 표 수 · u32 오프셋 × (표 수 + 1, 마지막 = 전체 크기) · 0x80 정렬

python tools/mstext.py test     -> 원본 전부 «풀기 → 짜기» 바이트 일치 검산
"""
import os, sys, glob, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mscrypt

ROOT = mscrypt.ROOT
GAME = r'D:\hospi\rpcs3\games\Soulcalibur IV (Asia)\PS3_GAME\USRDIR'


def parse(pt):
    lang, cnt = struct.unpack('>II', pt[:8])
    base = 8 + 4 * cnt
    offs = struct.unpack('>%dI' % cnt, pt[8:base])
    strs = []
    for o in offs:
        e = pt.index(b'\0', base + o)
        strs.append(pt[base + o:e])
    return lang, strs


def build(lang, strs):
    """원본과 같은 꼴: 문자열을 차례로, 공유 없음"""
    offs = []
    body = bytearray()
    for s in strs:
        if b'\0' in s:
            raise ValueError('문자열 안 NUL')
        offs.append(len(body))
        body += s + b'\0'
    return struct.pack('>II', lang, len(strs)) + struct.pack('>%dI' % len(strs), *offs) + bytes(body)


def read_table(b, plain=False):
    return parse(b if plain else mscrypt.dec(b)[0])


def write_table(lang, strs, plain=False):
    pt = build(lang, strs)
    return pt if plain else mscrypt.enc(pt)


# ---- regtext 묶음
def pack_split(b):
    n = struct.unpack('>I', b[:4])[0]
    offs = struct.unpack('>%dI' % (n + 1), b[4:8 + 4 * n])
    return [b[offs[i]:offs[i + 1]] for i in range(n)]


def chunk_trim(c, plain):
    """정렬 채움을 뗀 실제 표 바이트"""
    if plain:
        lang, strs = parse(c)
        return c[:len(build(lang, strs))]
    e = c.find(mscrypt.END)
    return c[:e + 4]


def pack_join(chunks, align=0x80):
    n = len(chunks)
    head = 8 + 4 * n
    pos = (head + align - 1) // align * align
    offs = []
    out = bytearray()
    for c in chunks:
        offs.append(pos)
        pad = (-len(c)) % align
        out += c + b'\0' * pad
        pos += len(c) + pad
    offs.append(pos)
    hd = struct.pack('>I', n) + struct.pack('>%dI' % (n + 1), *offs)
    return hd + b'\0' * (offs[0] - len(hd)) + bytes(out)


def test():
    n = bad = 0
    for sub in ('cdata/text', 'cpudata/tectext'):
        for p in sorted(glob.glob(os.path.join(GAME, sub, '*.ms?'))):
            b = open(p, 'rb').read()
            plain = p.endswith('.msk')
            lang, strs = read_table(b, plain)
            out = write_table(lang, strs, plain)
            n += 1
            if out != b:
                bad += 1
                print('  다름', os.path.basename(p), len(b), len(out))
    print('표 왕복 %d 개, 다름 %d' % (n, bad))
    for p in sorted(glob.glob(os.path.join(GAME, 'cdata/text', 'regtext_?.dtp'))):
        b = open(p, 'rb').read()
        plain = p.endswith('_k.dtp')
        chunks = pack_split(b)
        new = []
        for c in chunks:
            t = chunk_trim(c, plain)
            lang, strs = read_table(t, plain)
            new.append(write_table(lang, strs, plain))
        out = pack_join(new)
        print('  %s 표 %d 왕복 %s  (%d / %d B)' % (os.path.basename(p), len(chunks), out == b, len(out), len(b)))


if __name__ == '__main__':
    if sys.argv[1] == 'test':
        test()
