# -*- coding: utf-8 -*-
"""본문 글꼴(gt_KanjiTexturePs3.nut, 32x32 칸)의 한자 칸에 한글을 그려 넣는다.

- 칸 번호(EBOOT 0x584470): 1수준 한자 JIS 0x3021~ -> 960 + (구-16)*94 + (점-1) (2,965칸)
                            2수준 한자 JIS 0x5021~ -> 3986 + (구-48)*94 + (점-1) (3,390칸)
- 화소: DXT1 3색 모드. 끝점 0841/ffff: 0=테두리(불투명 어두움) 1=흰색 2=중간 3=투명. 획 없는 블록은 0841/0842.
- 테두리 = 획을 십자 모양으로 2번 팽창(원본 300칸 실측).
- fntdata.fnt: 칸마다 1 B, 위 니블 = 왼쪽 빈 화소-2, 아래 니블 = 오른쪽 빈 화소-2 (0~15).

쓰는 법(다른 도구에서):
    import font_kr
    cmap = font_kr.assign(음절 목록)                      # 음절 -> 대역 한자
    font_kr.build(cmap, 출력 폴더)                         # nut·fnt·charmap.tsv·미리보기
"""
import os, sys, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nut

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'work', 'orig_font')   # SC5: cdata.cpk 00122(nut)·00123(fnt) 풀어 둔 것 (SC4 font_kr.py 복사, 2026-11-15)
TTF = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
SS = 4                 # 덧샘플 배율
SIZE = 25              # 글자 크기(px)
X0, X1 = 4, 27         # 한글 획이 들어갈 가로 범위(한자 대부분 폭 니블 22 = 빈 화소 4)
Y0, Y1 = 3, 27         # 세로 범위(원본 한자 잉크 y 3~27)
WIDTH_BYTE = 0x22


def cells():
    """한자 칸 차례: (칸 번호, 대역 한자)"""
    out = []
    for base, ku0, n in ((960, 16, 2965), (3986, 48, 3390)):
        for k in range(n):
            ku, ten = ku0 + k // 94, 1 + k % 94
            ch = bytes([0xA0 + ku, 0xA0 + ten]).decode('euc_jp')
            # 왕복 확인(UTF-8 -> SJIS -> JIS 가 같은 칸으로 돌아오는지)
            sj = ch.encode('cp932')
            assert ch.encode('euc_jp') == bytes([0xA0 + ku, 0xA0 + ten]) and len(sj) == 2
            out.append((base + k, ch))
    return out


def assign(syllables):
    """음절(차례 유지, 중복 제거) -> 대역 한자"""
    cs = cells()
    seen = []
    for s in syllables:
        if s not in seen:
            seen.append(s)
    if len(seen) > len(cs):
        raise ValueError('음절 %d > 한자 칸 %d' % (len(seen), len(cs)))
    return {s: (cs[i][0], cs[i][1]) for i, s in enumerate(seen)}


_font = None
_org = None


def _setup():
    """모든 완성형 음절의 잉크 범위로 공통 원점(기준선)을 한 번 정한다"""
    global _font, _org
    if _font:
        return
    _font = ImageFont.truetype(TTF, SIZE * SS)
    l = t = 10 ** 9; r = b = -10 ** 9
    for ch in '가힣뷁쀍꿿쁑흫각낢닭떫뿔쐈쬈':
        bb = _font.getbbox(ch)
        l = min(l, bb[0]); t = min(t, bb[1]); r = max(r, bb[2]); b = max(b, bb[3])
    # 기준 묶음의 잉크 상자를 [X0..X1] x [Y0..Y1] 가운데에
    ox = ((X0 + X1 + 1) * SS - (l + r)) / 2
    oy = ((Y0 + Y1 + 1) * SS - (t + b)) / 2
    _org = (ox, oy)


def _dil(m):
    o = m.copy()
    o[1:] |= m[:-1]; o[:-1] |= m[1:]; o[:, 1:] |= m[:, :-1]; o[:, :-1] |= m[:, 1:]
    return o


def render(ch):
    """-> 32x32 등급 배열: 0 테두리 1 흰색 2 중간 3 투명"""
    _setup()
    im = Image.new('L', (32 * SS, 32 * SS), 0)
    ImageDraw.Draw(im).text(_org, ch, font=_font, fill=255)
    cov = np.asarray(im, np.float32).reshape(32, SS, 32, SS).mean((1, 3)) / 255.0
    white = cov >= 0.62
    mid = (cov >= 0.28) & ~white
    ink = white | mid
    ys, xs = np.where(ink)
    if len(xs) == 0:
        raise ValueError('빈 글자 %r' % ch)
    if xs.min() < 3 or xs.max() > 28 or ys.min() < 3 or ys.max() > 28:
        raise ValueError('칸 넘침 %r x %d~%d y %d~%d' % (ch, xs.min(), xs.max(), ys.min(), ys.max()))
    edge = _dil(_dil(ink)) & ~ink
    cls = np.full((32, 32), 3, np.uint8)
    cls[edge] = 0; cls[white] = 1; cls[mid] = 2
    return cls


def encode_cell(cls):
    """32x32 등급 -> 8x8 블록 x 8 B (행 우선)"""
    out = np.zeros((8, 8, 8), np.uint8)
    for by in range(8):
        for bx in range(8):
            blk = cls[by * 4:by * 4 + 4, bx * 4:bx * 4 + 4]
            has = ((blk == 1) | (blk == 2)).any()
            head = b'\x41\x08\xff\xff' if has else b'\x41\x08\x42\x08'
            rows = bytes(int(blk[y, 0]) | (int(blk[y, 1]) << 2) | (int(blk[y, 2]) << 4) | (int(blk[y, 3]) << 6) for y in range(4))
            out[by, bx] = np.frombuffer(head + rows, np.uint8)
    return out


def build(cmap, outdir, preview=True):
    os.makedirs(outdir, exist_ok=True)
    b = bytearray(open(os.path.join(SRC, 'gt_KanjiTexturePs3.nut'), 'rb').read())
    fd = bytearray(open(os.path.join(SRC, 'fntdata.fnt'), 'rb').read())
    es = nut.entries(bytes(b))
    for syl, (cell, kan) in cmap.items():
        page, r = divmod(cell, 4096)
        cy, cx = divmod(r, 64)
        enc = encode_cell(render(syl))
        e = es[page]
        for by in range(8):
            off = e['data'] + ((cy * 8 + by) * 512 + cx * 8) * 8
            b[off:off + 64] = enc[by].tobytes()
        fd[cell] = WIDTH_BYTE
    assert len(b) == os.path.getsize(os.path.join(SRC, 'gt_KanjiTexturePs3.nut'))
    open(os.path.join(outdir, 'gt_KanjiTexturePs3.nut'), 'wb').write(b)
    open(os.path.join(outdir, 'fntdata.fnt'), 'wb').write(fd)
    with open(os.path.join(outdir, 'charmap.tsv'), 'w', encoding='utf-8') as o:
        o.write('음절\t칸\t대역 한자\n')
        for syl, (cell, kan) in cmap.items():
            o.write('%s\t%d\t%s\n' % (syl, cell, kan))
    if preview:
        # 파일에 써 넣은 바이트를 다시 풀어서 만든 글자판(원본 | 한글)
        es2 = nut.entries(bytes(b))
        orig = open(os.path.join(SRC, 'gt_KanjiTexturePs3.nut'), 'rb').read()
        cellsl = [c for c, k in cmap.values()]
        page0 = [c for c in cellsl if c < 4096]
        if page0:
            r0, r1 = min(page0) // 64, max(page0) // 64 + 1
            r1 = min(r1, r0 + 12)
            new = nut.decode(bytes(b), es2[0])[r0 * 32:r1 * 32]
            old = nut.decode(orig, es2[0])[r0 * 32:r1 * 32]
            def comp(a):       # 회색 바탕 위에 합성(테두리가 보이게)
                rgb = a[:, :, :3].astype(np.float32); al = a[:, :, 3:4].astype(np.float32) / 255
                return (rgb * al + 96 * (1 - al)).astype(np.uint8)
            both = np.concatenate([comp(old), np.full((old.shape[0], 16, 3), 0, np.uint8), comp(new)], 1)
            Image.fromarray(both).save(os.path.join(outdir, '_글자판_원본_한글.png'))
    return len(cmap)


def encode_text(s, cmap):
    """한글 -> 대역 한자"""
    out = []
    for ch in s:
        if '가' <= ch <= '힣':
            if ch not in cmap:
                raise KeyError('대응표에 없는 음절 %r' % ch)
            out.append(cmap[ch][1])
        else:
            out.append(ch)
    return ''.join(out)
