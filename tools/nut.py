# -*- coding: utf-8 -*-
"""남코 NTP3(.nut) 텍스처 묶음 풀기 — DXT1(형식 0)·DXT5(형식 2) → PNG.

python tools/nut.py info <파일>
python tools/nut.py png  <파일> <출력 폴더>     -> <이름>_<번호>.png (RGBA) + _a.png (알파만)
"""
import os, sys, struct
import numpy as np
from PIL import Image


def entries(b):
    assert b[:4] == b'NTP3', b[:4]
    cnt = struct.unpack('>H', b[6:8])[0]
    p = 0x10
    out = []
    for i in range(cnt):
        total, _, dsize, hsize = struct.unpack('>IIIH', b[p:p + 14])
        mips, fmt, w, h = struct.unpack('>HHHH', b[p + 0x10:p + 0x18])
        out.append(dict(i=i, pos=p, total=total, dsize=dsize, hsize=hsize, mips=mips, fmt=fmt, w=w, h=h,
                        data=p + hsize, head=b[p:p + hsize]))
        p += total
    return out


def _colors(blk):
    """blk: (n,8) uint8 -> (n,16,3) RGB, (n,16) 투명 여부"""
    c0 = blk[:, 0].astype(np.uint32) | (blk[:, 1].astype(np.uint32) << 8)
    c1 = blk[:, 2].astype(np.uint32) | (blk[:, 3].astype(np.uint32) << 8)
    def rgb(c):
        r = (c >> 11) & 31; g = (c >> 5) & 63; bl = c & 31
        return np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (bl << 3) | (bl >> 2)], -1).astype(np.int32)
    a, bb = rgb(c0), rgb(c1)
    four = (c0 > c1)[:, None]
    pal = np.zeros((len(blk), 4, 3), np.int32)
    pal[:, 0] = a; pal[:, 1] = bb
    pal[:, 2] = np.where(four, (2 * a + bb) // 3, (a + bb) // 2)
    pal[:, 3] = np.where(four, (a + 2 * bb) // 3, 0)
    idx = blk[:, 4:8].astype(np.uint32)
    bits = idx[:, 0] | (idx[:, 1] << 8) | (idx[:, 2] << 16) | (idx[:, 3] << 24)
    sel = np.stack([(bits >> (2 * k)) & 3 for k in range(16)], -1)
    out = np.take_along_axis(pal, sel[:, :, None].astype(np.int64), 1)
    return out.astype(np.uint8), sel, four[:, 0]


def _alpha5(blk):
    a0 = blk[:, 0].astype(np.int32); a1 = blk[:, 1].astype(np.int32)
    bits = np.zeros(len(blk), np.uint64)
    for k in range(6):
        bits |= blk[:, 2 + k].astype(np.uint64) << np.uint64(8 * k)
    sel = np.stack([((bits >> np.uint64(3 * k)) & np.uint64(7)).astype(np.int64) for k in range(16)], -1)
    pal = np.zeros((len(blk), 8), np.int32)
    pal[:, 0] = a0; pal[:, 1] = a1
    big = a0 > a1
    for k in range(1, 7):
        pal[:, k + 1] = np.where(big, ((7 - k) * a0 + k * a1) // 7, 0)
    for k in range(1, 5):
        pal[:, k + 1] = np.where(big, pal[:, k + 1], ((5 - k) * a0 + k * a1) // 5)
    pal[:, 6] = np.where(big, pal[:, 6], 0)
    pal[:, 7] = np.where(big, pal[:, 7], 255)
    return np.take_along_axis(pal, sel, 1).astype(np.uint8)


def _unblock(px, w, h):
    """(블록 수,16,채널) -> (h,w,채널)"""
    c = px.shape[-1]
    return px.reshape(h // 4, w // 4, 4, 4, c).transpose(0, 2, 1, 3, 4).reshape(h, w, c)


def decode(b, e):
    w, h = e['w'], e['h']
    n = (w // 4) * (h // 4)
    if e['fmt'] == 0:
        blk = np.frombuffer(b, np.uint8, n * 8, e['data']).reshape(n, 8)
        rgb, sel, four = _colors(blk)
        a = np.where((~four)[:, None] & (sel == 3), 0, 255).astype(np.uint8)
    elif e['fmt'] == 2:
        blk = np.frombuffer(b, np.uint8, n * 16, e['data']).reshape(n, 16)
        a = _alpha5(blk[:, :8])
        rgb, sel, four = _colors(blk[:, 8:])
    else:
        raise ValueError('모르는 형식 %d' % e['fmt'])
    return _unblock(np.concatenate([rgb, a[:, :, None]], -1), w, h)


def main():
    cmd, path = sys.argv[1], sys.argv[2]
    b = open(path, 'rb').read()
    es = entries(b)
    name = os.path.splitext(os.path.basename(path))[0]
    for e in es:
        print('%2d 위치 %07X 크기 %dx%d 형식 %d 밉 %d 데이터 %07X(%d B) 머리 %d B' % (
            e['i'], e['pos'], e['w'], e['h'], e['fmt'], e['mips'], e['data'], e['dsize'], e['hsize']))
        if cmd == 'png':
            out = sys.argv[3]
            os.makedirs(out, exist_ok=True)
            im = decode(b, e)
            Image.fromarray(im, 'RGBA').save(os.path.join(out, '%s_%02d.png' % (name, e['i'])))
            Image.fromarray(im[:, :, 3], 'L').save(os.path.join(out, '%s_%02d_a.png' % (name, e['i'])))


if __name__ == '__main__':
    main()
