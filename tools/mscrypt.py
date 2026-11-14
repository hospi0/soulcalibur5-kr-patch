# -*- coding: utf-8 -*-
"""소울칼리버 IV 글 파일(.ms?) 암호 풀기·걸기.

파일 = 암호 본문 + 씨앗 2 B + 암호화된 서명 문자열 + FFFFFFFF          (EBOOT 0xA6B28 = 거는 함수)
  씨앗 s0 = (0xA21F + 15 * 평문 바이트 합) & 0xFFFF
  본문: 암호문 = 평문 ^ (s & 0xFF), s = rotr16(s, 1) * 5 + 1
  씨앗 2 B: v = rotl16(s0 ^ 0xEB7D, 3) -> [v & 0xFF, v >> 8]
  서명: t = v 에서 시작, 암호문 = 글자 ^ (t & 0xFF), t = rotr16(t, 5) * 5 + 1

python tools/mscrypt.py test                 -> 원본 전부 풀기 + 다시 걸어 바이트 일치 검산
python tools/mscrypt.py dec <입력> <출력>
python tools/mscrypt.py enc <평문> <출력> [서명]
python tools/mscrypt.py decall               -> work/plain/<이름> 으로 전부 풀기
"""
import os, sys, glob, struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT = os.path.join(ROOT, 'work', 'orig', 'text')
PLAIN = os.path.join(ROOT, 'work', 'plain')
END = b'\xff\xff\xff\xff'
M = 0xFFFF


def rotr(s, n):
    return ((s >> n) | (s << (16 - n))) & M


def stream(seed, n, rot=1):
    s = seed & M
    out = bytearray(n)
    for i in range(n):
        out[i] = s & 0xFF
        s = (rotr(s, rot) * 5 + 1) & M
    return bytes(out)


def xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def seed_of(pt):
    return (0xA21F + 15 * sum(pt)) & M


SIG = b'sc4-text'


def tail_of(seed, sig):
    v = (seed ^ 0xEB7D) & M
    v = ((v << 3) | (v >> 13)) & M
    # 서명 뒤 NUL 은 암호 없이 그대로 쓴다(0xA6C84)
    return bytes([v & 0xFF, v >> 8]) + xor(sig, stream(v, len(sig), 5)) + b'\0' + END


def enc(pt, sig=SIG):
    seed = seed_of(pt)
    out = xor(pt, stream(seed, len(pt))) + tail_of(seed, sig)
    # 게임은 처음 나오는 FFFFFFFF 를 끝으로 본다
    if out.find(END) != len(out) - 4:
        raise ValueError('암호문 안에 끝 표지가 생김 — 평문 끝에 NUL 하나 덧붙여 다시')
    return out


def dec(b):
    """-> (평문, 서명)"""
    if b[-4:] != END:
        raise ValueError('끝 표지 없음')
    n = len(b) - 4 - 1 - len(SIG) - 2
    v = b[n] | (b[n + 1] << 8)
    seed = rotr(v, 3) ^ 0xEB7D
    pt = xor(b[:n], stream(seed, n))
    sig = xor(b[n + 2:n + 2 + len(SIG)], stream(v, len(SIG), 5))
    if seed_of(pt) != seed or enc(pt, sig) != b:
        raise ValueError('풀기 실패')
    return pt, sig


def info(pt):
    lang, cnt = struct.unpack('>II', pt[:8])
    base = 8 + 4 * cnt
    offs = struct.unpack('>%dI' % cnt, pt[8:base])
    strs = []
    for o in offs:
        e = pt.index(b'\0', base + o)
        strs.append(pt[base + o:e])
    return lang, cnt, strs


def test():
    ok = 0
    for p in sorted(glob.glob(os.path.join(TEXT, '*.ms?'))):
        if p.endswith('.msk'):
            continue
        b = open(p, 'rb').read()
        pt, sig = dec(b)
        lang, cnt, strs = info(pt)
        ok += 1
        if p.endswith(('.msu', '.msj')):
            s = next((x for x in strs if x), b'')
            print('%-22s %6d B 언어 %2d 항목 %4d 서명 %r  %s' % (
                os.path.basename(p), len(b), lang, cnt, sig, s[:36].decode('utf-8', 'replace')))
    print('풀기 + 다시 걸기 바이트 일치:', ok, '개')


def decall():
    os.makedirs(PLAIN, exist_ok=True)
    for p in sorted(glob.glob(os.path.join(TEXT, '*.ms?'))):
        b = open(p, 'rb').read()
        pt = b if p.endswith('.msk') else dec(b)[0]
        open(os.path.join(PLAIN, os.path.basename(p)), 'wb').write(pt)
    print('풀림 ->', PLAIN)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'test':
        test()
    elif cmd == 'decall':
        decall()
    elif cmd == 'dec':
        pt, sig = dec(open(sys.argv[2], 'rb').read())
        open(sys.argv[3], 'wb').write(pt)
        print('서명', sig)
    elif cmd == 'enc':
        sig = sys.argv[4].encode() if len(sys.argv) > 4 else b''
        open(sys.argv[3], 'wb').write(enc(open(sys.argv[2], 'rb').read(), sig))
