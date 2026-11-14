# -*- coding: utf-8 -*-
r"""SC5 한글 시험판 (2026-11-15) — 메인 메뉴 설명 11줄(text 00008 #12~22, 영어 자리) + 글꼴 한자 칸 한글.
  · 글 = 영어 자리 00008 과 상주 묶음 00424 의 표 1(같은 사본) 둘 다
  · 한글 = 대역 한자 UTF-8 (font_kr.assign — JIS 1수준 한자 칸 차례)
  · 글꼴 = cdata 00122(gt_KanjiTexturePs3 꼴 nut) · 00123(fntdata.fnt) — 64px 판(font_hires, SC4 와 같음)
  · CPK = tools/cpkw.py 로 다시 쌓음(바꾼 파일은 무압축)
  출력 work/poc/USRDIR/text.cpk · cdata.cpk · 미리보기 work/poc/font/_글자판_원본위_한글아래_64px.png
  python tools/poc.py
"""
import os, sys, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import struct
import numpy as np
import cpk, cpkw, mstext, font_kr, font_hires, nut

DISC = os.path.join(ROOT, 'work', 'orig_install')      # 원본 text.cpk·cdata.cpk 사본(게임 폴더엔 시험판이 깔려 있음)
OUT = os.path.join(ROOT, 'work', 'poc')


def font_build(cmap, outdir):
    """64px 판(4096²×2) — SC4 build.font_build 와 같은 방식(한글 칸 새로 그림, 나머지 칸은 등급 그대로 2배)"""
    src = open(os.path.join(font_kr.SRC, 'gt_KanjiTexturePs3.nut'), 'rb').read()
    es = nut.entries(src); K, C = font_hires.K, font_hires.C
    pages = [np.repeat(np.repeat(font_hires.classes(nut.decode(src, e)), K, 0), K, 1) for e in es]
    for s_, (cell, kan) in cmap.items():
        p, r = divmod(cell, 4096); cy, cx = divmod(r, 64)
        pages[p][cy * C:cy * C + C, cx * C:cx * C + C] = font_hires.render(s_)
    out = bytearray(src[:0x10])
    for e, pg in zip(es, pages):
        data = font_hires.encode_page(pg); head = bytearray(e['head'])
        struct.pack_into('>I', head, 0, len(data) + e['hsize']); struct.pack_into('>I', head, 8, len(data))
        struct.pack_into('>HH', head, 0x14, pg.shape[1], pg.shape[0])
        out += head + data
    fd = bytearray(open(os.path.join(font_kr.SRC, 'fntdata.fnt'), 'rb').read())
    for s_, (cell, kan) in cmap.items(): fd[cell] = font_kr.WIDTH_BYTE
    os.makedirs(outdir, exist_ok=True)
    open(os.path.join(outdir, 'gt_KanjiTexturePs3.nut'), 'wb').write(out)
    open(os.path.join(outdir, 'fntdata.fnt'), 'wb').write(fd)
    # 미리보기: 다시 풀어 한글 칸 줄(원본 32px 2배 | 새것)
    es2 = nut.entries(bytes(out)); cells = sorted(c for c, k in cmap.values())
    r0, r1 = cells[0] // 64, min(cells[-1] // 64 + 1, cells[0] // 64 + 4)
    new = nut.decode(bytes(out), es2[0])[r0 * C:r1 * C]
    old = np.repeat(np.repeat(nut.decode(src, es[0])[r0 * 32:r1 * 32], K, 0), K, 1)
    comp = lambda a: (a[:, :, :3].astype(np.float32) * (a[:, :, 3:4] / 255) + 96 * (1 - a[:, :, 3:4] / 255)).astype(np.uint8)
    from PIL import Image
    Image.fromarray(np.concatenate([comp(old), comp(new)], 0)[:, :2048]).save(os.path.join(outdir, '_글자판_원본위_한글아래_64px.png'))
    return bytes(out), bytes(fd)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ko = {}
    for ln in open(os.path.join(OUT, 'poc_ko.tsv'), encoding='utf-8'):
        if ln.strip():
            i, t = ln.rstrip('\n').split('\t'); ko[int(i)] = t.replace('\\n', '\n')
    syl = [ch for t in ko.values() for ch in t if '가' <= ch <= '힣']
    cmap = font_kr.assign(syl)
    print('음절 %d개 → 대역 한자 %s…' % (len(cmap), ''.join(v[1] for v in list(cmap.values())[:10])))
    c = cpk.Cpk(os.path.join(DISC, 'text.cpk')); E = {e['id']: e for e in c.files}
    lang, strs = mstext.read_table(c.read(E[8]))
    for i, t in ko.items():
        strs[i] = ('$z0.875/0.875/' + font_kr.encode_text(t, cmap)).encode('utf-8')
    t8 = mstext.write_table(lang, strs)
    assert mstext.read_table(t8) == (lang, strs)
    res = c.read(E[424]); chunks = [mstext.chunk_trim(x, False) for x in mstext.pack_split(res)]
    assert chunks[1] == c.read(E[8]), '상주 표 1 ≠ 00008'
    chunks[1] = t8
    r424 = mstext.pack_join(chunks)
    od = os.path.join(OUT, 'USRDIR'); os.makedirs(od, exist_ok=True)
    cpkw.rebuild(os.path.join(DISC, 'text.cpk'), os.path.join(od, 'text.cpk'), {8: t8, 424: r424})
    fd = os.path.join(OUT, 'font')
    nutb, fnt = font_build(cmap, fd)                  # 64px 판(하스피 2026-11-15 «sc4에 썼던 고해상도»)
    cpkw.rebuild(os.path.join(DISC, 'cdata.cpk'), os.path.join(od, 'cdata.cpk'), {122: nutb, 123: fnt})
    # 다시 읽어 검산
    for n, want in (('text', {8: t8, 424: r424}), ('cdata', {122: nutb, 123: fnt})):
        d = cpk.Cpk(os.path.join(od, n + '.cpk')); D = {e['id']: e for e in d.files}
        assert all(d.read(D[i]) == b for i, b in want.items()), n
        print('%s.cpk md5 %s' % (n, hashlib.md5(open(os.path.join(od, n + '.cpk'), 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main()
