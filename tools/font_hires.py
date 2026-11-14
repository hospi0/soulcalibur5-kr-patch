# -*- coding: utf-8 -*-
"""본문 글꼴 텍스처를 2배(4096x4096, 칸 64px)로 키운 시험판.

- 한글 칸: 64px 로 새로 그림(획 덧샘플, 테두리 = 십자 4번 팽창)
- 그 밖(영문·기호·가나): 원본 칸을 등급 그대로 2배 확대
- NTP3 머리의 크기(전체·데이터·가로·세로)만 고침. fntdata.fnt 는 font_kr 것 그대로.

python tools/font_hires.py     -> work/poc_hires/gt_KanjiTexturePs3.nut (+ 미리보기)
"""
import os, sys, struct, hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nut, font_kr

ROOT = font_kr.ROOT
OUT = os.path.join(ROOT, 'work', 'poc_hires')
K = 2                      # 배율
C = 32 * K                 # 칸 크기
SS = 4
SIZE = font_kr.SIZE * K


def classes(rgba):
    """RGBA -> 등급(0 테두리 1 흰색 2 중간 3 투명)"""
    cls = np.zeros(rgba.shape[:2], np.uint8)
    v = rgba[:, :, 0]
    cls[v >= 100] = 2
    cls[v >= 200] = 1
    cls[rgba[:, :, 3] == 0] = 3
    return cls


def encode_page(cls):
    """(H,W) 등급 -> DXT1 바이트"""
    H, W = cls.shape
    blk = cls.reshape(H // 4, 4, W // 4, 4).transpose(0, 2, 1, 3)          # (by,bx,y,x)
    has = ((blk == 1) | (blk == 2)).any((2, 3))
    empty = (blk == 3).all((2, 3))
    rows = (blk[..., 0] | (blk[..., 1] << 2) | (blk[..., 2] << 4) | (blk[..., 3] << 6)).astype(np.uint8)   # (by,bx,4)
    out = np.zeros((H // 4, W // 4, 8), np.uint8)
    out[..., 0] = 0x41; out[..., 1] = 0x08
    out[..., 2] = np.where(has, 0xFF, 0x42); out[..., 3] = np.where(has, 0xFF, 0x08)
    out[..., 4:8] = rows
    # 완전히 빈 블록은 원본처럼 0000/0001
    out[empty, 0] = 0; out[empty, 1] = 0; out[empty, 2] = 1; out[empty, 3] = 0
    return out.tobytes()


_font = None
_org = None


def render(ch):
    global _font, _org
    if _font is None:
        _font = ImageFont.truetype(font_kr.TTF, SIZE * SS)
        l = t = 10 ** 9; r = b = -10 ** 9
        for c in '가힣뷁쀍꿿쁑흫각낢닭떫뿔쐈쬈':
            bb = _font.getbbox(c)
            l = min(l, bb[0]); t = min(t, bb[1]); r = max(r, bb[2]); b = max(b, bb[3])
        _org = (((font_kr.X0 + font_kr.X1 + 1) * K * SS - (l + r)) / 2, ((font_kr.Y0 + font_kr.Y1 + 1) * K * SS - (t + b)) / 2)
    im = Image.new('L', (C * SS, C * SS), 0)
    ImageDraw.Draw(im).text(_org, ch, font=_font, fill=255)
    cov = np.asarray(im, np.float32).reshape(C, SS, C, SS).mean((1, 3)) / 255.0
    white = cov >= 0.62
    mid = (cov >= 0.28) & ~white
    ink = white | mid
    ys, xs = np.where(ink)
    assert xs.min() >= 3 * K and xs.max() <= 29 * K - 1 and ys.min() >= 3 * K and ys.max() <= 29 * K - 1, ch
    e = ink
    for _ in range(2 * K):
        e = font_kr._dil(e)
    cls = np.full((C, C), 3, np.uint8)
    cls[e & ~ink] = 0; cls[white] = 1; cls[mid] = 2
    return cls


def main():
    os.makedirs(OUT, exist_ok=True)
    cmap = {}
    with open(os.path.join(ROOT, 'work', 'poc', 'charmap.tsv'), encoding='utf-8') as f:
        next(f)
        for ln in f:
            s, cell, kan = ln.rstrip('\n').split('\t')
            cmap[s] = int(cell)
    src = open(os.path.join(font_kr.SRC, 'gt_KanjiTexturePs3.nut'), 'rb').read()
    es = nut.entries(src)
    pages = [np.repeat(np.repeat(classes(nut.decode(src, e)), K, 0), K, 1) for e in es]
    for s, cell in cmap.items():
        p, r = divmod(cell, 4096)
        cy, cx = divmod(r, 64)
        pages[p][cy * C:cy * C + C, cx * C:cx * C + C] = render(s)
    out = bytearray(src[:0x10])
    for e, pg in zip(es, pages):
        data = encode_page(pg)
        head = bytearray(e['head'])
        struct.pack_into('>I', head, 0, len(data) + e['hsize'])
        struct.pack_into('>I', head, 8, len(data))
        struct.pack_into('>HH', head, 0x14, pg.shape[1], pg.shape[0])
        out += head + data
    open(os.path.join(OUT, 'gt_KanjiTexturePs3.nut'), 'wb').write(out)
    print('gt_KanjiTexturePs3.nut %d B md5 %s' % (len(out), hashlib.md5(out).hexdigest()))
    # 검산 + 미리보기: 쓴 파일을 다시 풀어서
    chk = bytes(out)
    es2 = nut.entries(chk)
    for e in es2:
        print('  %d: %dx%d 데이터 %d B' % (e['i'], e['w'], e['h'], e['dsize']))
    im = nut.decode(chk, es2[0])
    def comp(a):
        rgb = a[:, :, :3].astype(np.float32); al = a[:, :, 3:4].astype(np.float32) / 255
        return (rgb * al + 96 * (1 - al)).astype(np.uint8)
    y0 = 15 * C
    Image.fromarray(comp(im[y0:y0 + 4 * C, :12 * C])).save(os.path.join(OUT, '_글자판_64px_한글.png'))
    Image.fromarray(comp(im[2 * C:6 * C, :16 * C])).save(os.path.join(OUT, '_글자판_64px_영숫자.png'))


if __name__ == '__main__':
    main()
