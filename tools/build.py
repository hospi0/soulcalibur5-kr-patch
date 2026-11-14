# -*- coding: utf-8 -*-
r"""소울칼리버 V 한글 빌드 (2026-11-15, 틀 = soulcalibur4-kr-patch/tools/build.py)

입력
  work/extract/all.tsv                 id(text/<묶음>#항목 · patch/<묶음>#항목) · 일본어 · 영어 · 표시   (tools/extract.py)
  번역(먼저 있는 쪽): work/text/fixed/sc5_*.tsv(용어 통일 뒤) → 없으면 my files/번역/*.tsv(읽기만)
                      + work/text/ko_extra.tsv(있으면, 시험·손질용 — 앞의 것보다 우선)
                      열 = 번호 · 위치 · 겹침 · JP · KO  (my files/tsv/sc5_*.tsv 와 같은 꼴)
  원본: work/orig_install/text.cpk · cdata.cpk · patch.cpk (게임 폴더엔 시험판이 깔려 있을 수 있음)
방식(PoC 2026-11-15 실기 확인: 무압축 CPK·대역 한자·64px 글꼴)
  · 번역은 «일본어 문장»으로 찾아 같은 문장 전부에 — 영어 자리(묶음 첫 번호 + 0)에 넣음(시스템 언어 한국어 → 영어 자리)
  · 상주 묶음(text 00424 = 영어 자리)의 표는 개별 묶음 사본 → 바이트 대조로 짝을 찾아 같이 고침
  · 한글은 «대역 한자»(JIS 1·2수준 한자 칸 차례, 많이 쓰는 음절부터) UTF-8 — 글꼴(cdata 00122 nut · 00123 fnt) 그 칸에 64px 한글
  · 영어 자리에만 있는 글자 크기 머리($z0.875/0.875/ · $m$z…/)는 붙여 넣음(일본판엔 없음, 31줄)
  · 적재 검사(어기면 그 줄은 넣지 않고 보고): 토큰 순서·개수 = 원문, 줄바꿈 수 = 원문, 한자·가나 금지, 글꼴(JIS)에 없는 글자 금지
  · 문장부호 뒤 공백 지움 · «……»/«...» → «…» 한 칸(바닥 점 셋으로 다시 그림)
출력
  work/build/disc/USRDIR/text.cpk · cdata.cpk      (디스크 PS3_GAME/USRDIR 에 덮어씀)
  work/build/update/USRDIR/patch.cpk               (dev_hdd0/game/BLUS30736/USRDIR, 바뀐 게 있을 때만)
  work/build/report.txt · charmap.tsv · 미리보기_글자판_자주쓰는음절.png
  python tools/build.py
"""
import os, sys, re, glob, struct, hashlib, collections
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import cpk, cpkw, mstext, font_kr, font_hires, nut

R = lambda *p: os.path.join(ROOT, *p)
ORIG = R('work', 'orig_install')
BUILD = R('work', 'build')
EN = 0
RESIDENT = 424                      # text.cpk 상주 묶음(영어 자리)
TOK = re.compile(r'\$z[0-9.]+/[0-9.]+/|\$[A-Z][0-9]+/|<s\$Q[0-9]+/s>|\$[a-y]/?|%[-+0-9.]*[a-zA-Z]|<[A-Z_ 0-9]+>|\\n')
PREFIX = re.compile(r'^(?:\$z[0-9.]+/[0-9.]+/|\$[a-y]/?)*')
PUNCT_SP = re.compile(r'([,.!?…‼⁉、。，．！？：；:;～~])[ 　]+')
KANA = re.compile('[ぁ-ヿｦ-ﾟ]')
JPCHR = re.compile('[぀-ヿ㐀-鿿ｦ-ﾟ]')
HAN = re.compile('[㐀-鿿豈-﫿]')        # 이스케이프로(글자로 쓰면 豈 U+8C48/U+F900 이 섞여 한글까지 덮음, 2026-11-15)
ELLIPSIS_CELL = (0x2144 >> 8) - 0x21, (0x2144 & 0xFF) - 0x21      # JIS 1-4 «…»


# PS3 시스템 대화상자(cellMsgDialogOpen2 · 세이브 데이터 제목)로 뜨는 문장 = 시스템 글꼴 → 대역 한자 대신 진짜 한글 UTF-8
#   (2026-11-15) 업데이트 EBOOT 에서 cellMsgDialogOpen2 스텁(VA 0xB4CA78) 호출 14곳 + 저장 감싼 함수(0x622854) 호출 12곳을 따라감.
#   글 번호 = (표 << 24) | 번호, 번호는 1부터(0x40C530: 항목 = 번호 − 1). 표 0x10 = 묶음 00128(= 상주 표 16) · 표 0x0E = 묶음 00112(= 상주 표 14).
#   저장 쪽 번호 표 EBOOT 0xB88CD0(19개). RPCS3 로그(오토세이브 안내 · 로드 완료 · 트로피 확인)와 맞음.
SYSDLG = {                          # 추적으로 확인
    'text/00128#%d' % i for i in (0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 50, 140, 162, 169, 170, 172, 173, 178, 182, 183)
} | {'text/00112#%d' % i for i in (107, 108, 109, 110, 111, 112, 113, 114, 115, 117)}
SYSDLG_GUESS = {                    # 추정(같은 종류 문장, 호출은 못 짚음 — 실기 로그로 확인할 것)
    'text/00128#%d' % i for i in (1, 141, 142, 163, 164, 165, 171, 174, 175, 184, 185, 187, 189)
} | {'text/00112#116'}


def unesc(s):
    out = []; i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            out.append({'n': '\n', 't': '\t', '\\': '\\'}.get(s[i + 1], '\\' + s[i + 1])); i += 2
        else:
            out.append(s[i]); i += 1
    return ''.join(out)


def ko_files():
    fixed = sorted(glob.glob(R('work', 'text', 'fixed', 'sc5_*.tsv')))
    files = fixed or sorted(glob.glob(R('my files', '번역', '*.tsv')))
    if os.path.exists(R('work', 'text', 'ko_extra.tsv')): files.append(R('work', 'text', 'ko_extra.tsv'))
    return files


def load_ko():
    """JP(이스케이프 꼴) → KO(이스케이프 꼴). 뒤 파일이 우선"""
    ko = {}; src = {}
    for p in ko_files():
        with open(p, encoding='utf-8-sig') as f:
            for ln in f:
                c = ln.rstrip('\n').rstrip('\r').split('\t')
                if len(c) >= 5 and c[0][:1].isdigit() and c[4].strip():
                    ko[c[3]] = c[4]; src[c[3]] = os.path.basename(p) + ':' + c[0]
    return ko, src


def jis_ok(ch):
    try:
        b = ch.encode('cp932')
    except UnicodeEncodeError:
        return False
    return len(b) == 1 or 0x81 <= b[0] <= 0x84 or b[0] == 0x88 and b[1] < 0x9F   # 1바이트 · 비한자 기호·가나 구(1~8구)


def check(jp, ko):
    """-> (정리된 KO 이스케이프 꼴, 문제 목록)"""
    errs = []
    ko = PUNCT_SP.sub(lambda m: m.group(1), ko).replace('……', '…').replace('...', '…')
    tj = TOK.findall(jp); tk = TOK.findall(ko)
    if [t for t in tj if t != '\\n'] != [t for t in tk if t != '\\n']: errs.append('토큰 다름 %s / %s' % ([t for t in tj if t != '\\n'], [t for t in tk if t != '\\n']))
    if tj.count('\\n') != tk.count('\\n'): errs.append('줄 수 다름 %d / %d' % (tj.count('\\n') + 1, tk.count('\\n') + 1))
    plain = TOK.sub('', ko)
    if HAN.search(plain): errs.append('한자 %s' % ''.join(sorted(set(HAN.findall(plain)))))
    kana = set(KANA.findall(plain)) - {'・'}
    if kana: errs.append('가나 %s' % ''.join(sorted(kana)))
    bad = sorted({c for c in plain if not ('가' <= c <= '힣') and not HAN.match(c) and not KANA.match(c) and not jis_ok(c)
                  and c not in jp and c != '·'})
    if bad: errs.append('글꼴에 없는 글자 %s' % ''.join(bad))
    return ko, errs


def font_build(cmap):
    """64px 판 글꼴(4096²×2) + fntdata.fnt — SC4 build.font_build 와 같음"""
    src = open(os.path.join(font_kr.SRC, 'gt_KanjiTexturePs3.nut'), 'rb').read()
    es = nut.entries(src); K, C = font_hires.K, font_hires.C
    pages = [np.repeat(np.repeat(font_hires.classes(nut.decode(src, e)), K, 0), K, 1) for e in es]
    for s, (cell, kan) in cmap.items():
        p, r = divmod(cell, 4096); cy, cx = divmod(r, 64)
        pages[p][cy * C:cy * C + C, cx * C:cx * C + C] = font_hires.render(s)
    cell = ELLIPSIS_CELL[0] * 94 + ELLIPSIS_CELL[1]; cy, cx = divmod(cell, 64)       # «…» = 한국식 바닥 점 셋
    g = np.full((C, C), 3, np.uint8); ink = np.zeros((C, C), bool)
    for k in range(3):
        x = 10 * K + k * 6 * K; ink[24 * K:27 * K, x:x + 3 * K] = True
    e = ink
    for _ in range(2 * K): e = font_kr._dil(e)
    g[e & ~ink] = 0; g[ink] = 1
    pages[0][cy * C:cy * C + C, cx * C:cx * C + C] = g
    out = bytearray(src[:0x10])
    for e, pg in zip(es, pages):
        data = font_hires.encode_page(pg); head = bytearray(e['head'])
        struct.pack_into('>I', head, 0, len(data) + e['hsize']); struct.pack_into('>I', head, 8, len(data))
        struct.pack_into('>HH', head, 0x14, pg.shape[1], pg.shape[0])
        out += head + data
    fd = bytearray(open(os.path.join(font_kr.SRC, 'fntdata.fnt'), 'rb').read())
    for s, (cell, kan) in cmap.items(): fd[cell] = font_kr.WIDTH_BYTE
    return bytes(out), bytes(fd)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rep = []
    log = lambda *a: (rep.append(' '.join(str(x) for x in a)), print(*a))
    os.makedirs(BUILD, exist_ok=True)
    log('번역 파일: %s' % ', '.join(os.path.relpath(p, ROOT) for p in ko_files()) or '없음')
    ko_raw, ko_src = load_ko()
    rows = [l.rstrip('\n').split('\t') for l in open(R('work', 'extract', 'all.tsv'), encoding='utf-8')][1:]
    if os.path.exists(R('work', 'extract', 'dlc.tsv')):              # DLC 파츠 이름 표(tools/extract_dlc.py) — id dlc/DLCnn#항목
        rows += [['dlc/' + r[0]] + r[1:] for r in (l.split('\t') for l in open(R('work', 'extract', 'dlc.tsv'), encoding='utf-8').read().splitlines()[1:])]
    # 1) 적재·검사
    ok, bad = {}, []
    jp_of = {r[1] for r in rows if not r[3]}
    for jp, k in ko_raw.items():
        if jp not in jp_of: bad.append((ko_src[jp], '원문을 찾지 못함', jp[:40])); continue
        k2, errs = check(jp, k)
        if errs: bad.append((ko_src[jp], ' · '.join(errs), jp[:40]))
        else: ok[jp] = k2
    log('번역 %d줄 읽음 · 넣음 %d · 문제로 뺌 %d' % (len(ko_raw), len(ok), len(bad)))
    for b in bad[:300]: log('  ⛔', *b)
    # 2) 음절 → 대역 한자(많이 쓰는 차례)
    kp0 = R('work', 'text', 'ko_keep.tsv')
    keep_txt = [ln.split('	')[2] for ln in open(kp0, encoding='utf-8-sig').read().splitlines()[1:] if ln.count('	') >= 2] if os.path.exists(kp0) else []
    freq = collections.Counter(c for k in list(ok.values()) + keep_txt for c in unesc(k) if '가' <= c <= '힣')
    cmap = font_kr.assign([c for c, n in freq.most_common()])
    log('음절 %d개 (한자 칸 %d 중)' % (len(cmap), len(font_kr.cells())))
    # 3) 항목별 새 문자열
    new = collections.defaultdict(dict)                 # (원본 cpk, 묶음 첫 번호) → {항목: 바이트}
    hit = collections.Counter(); miss = collections.Counter(); pref = [0]; keep_ascii = [0]; sysd = [0]
    keepko = {}                                         # 일본판도 영어인 줄(keep)의 한글 — work/text/ko_keep.tsv(위치 · 영어 · KO · 비고)
    kp = R('work', 'text', 'ko_keep.tsv')
    if os.path.exists(kp):
        for ln in open(kp, encoding='utf-8-sig').read().splitlines()[1:]:
            c = ln.split('	')
            if len(c) >= 3 and c[2].strip(): keepko[c[0]] = (c[1], c[2])
    nkeep = 0
    for id_, jp, en, flag in rows:
        if flag == 'keep' and id_ in keepko:
            e0, k0 = keepko[id_]
            assert e0 == en, ('ko_keep 영어 다름', id_, e0, en)
            assert [t for t in TOK.findall(en) if not t.startswith('$m')] == [t for t in TOK.findall(k0)], ('ko_keep 토큰', id_)
            assert '$m' not in k0, ('ko_keep 에 $m(영문 글꼴) — 한글 깨짐', id_)
            grp, rest = id_.split('/', 1); g, idx = rest.split('#')
            new[(grp, int(g))][int(idx)] = font_kr.encode_text(k0, cmap).encode('utf-8'); hit[grp] += 1; nkeep += 1
            continue
        if flag: continue
        if not JPCHR.search(jp): keep_ascii[0] += 1; continue
        grp, rest = id_.split('/', 1); g, idx = rest.split('#')
        if jp not in ok: miss[grp] += 1; continue
        k = ok[jp]
        pj, pe = PREFIX.match(jp).group(0), PREFIX.match(en).group(0)
        if pj != pe and k.startswith(pj):
            # $m = 영문 전용 글꼴(대역 한자가 바이트별로 깨짐 — 퀵 배틀 상대 정보 2026-11-15) → 크기($z)만 붙임
            if '$m' not in pj: pe = re.sub(r'\$m/?', '', pe)
            k = pe + k[len(pj):]; pref[0] += 1
        if id_ in SYSDLG or id_ in SYSDLG_GUESS:
            s = unesc(k); sysd[0] += 1                               # 시스템 글꼴 = 진짜 한글
        else:
            s = font_kr.encode_text(unesc(k).replace('·', '・'), cmap)
        new[(grp, g if grp == 'dlc' else int(g))][int(idx)] = s.encode('utf-8'); hit[grp] += 1
    log('넣은 항목 %s · 번역 없어 영어 그대로 %s · 일본판도 가나·한자 없어 영어 그대로 %d · 크기 머리 붙임 %d · 시스템 대화상자(진짜 한글) %d · 영어 줄 한글(ko_keep) %d'
        % (dict(hit), dict(miss), keep_ascii[0], pref[0], sysd[0], nkeep))
    # 4) 글 묶음 다시 쌓기
    text_c = cpk.Cpk(os.path.join(ORIG, 'text.cpk')); TE = {e['id']: e for e in text_c.files}
    repl = {'text': {}, 'patch': {}}
    for (grp, g), ch in sorted((k, v) for k, v in new.items() if k[0] != 'dlc'):
        c = text_c if grp == 'text' else cpk.Cpk(os.path.join(ORIG, 'patch.cpk'))
        E = TE if grp == 'text' else {e['id']: e for e in c.files}
        lang, strs = mstext.read_table(c.read(E[g + EN]))
        for i, v in ch.items(): strs[i] = v
        b = mstext.write_table(lang, strs)
        assert mstext.read_table(b) == (lang, strs)
        repl[grp][g + EN] = b
    # 상주 묶음: 원본 표와 바이트가 같은 개별 묶음의 새 표로
    res = text_c.read(TE[RESIDENT + EN]); chunks = [mstext.chunk_trim(x, False) if x.strip(b'\0') else x for x in mstext.pack_split(res)]
    orig_tab = {text_c.read(TE[g + EN]): g for (grp, g) in new if grp == 'text'}
    nres = 0
    for i, ch in enumerate(chunks):
        g = orig_tab.get(ch)
        if g is not None: chunks[i] = repl['text'][g + EN]; nres += 1
    if nres:
        repl['text'][RESIDENT + EN] = mstext.pack_join(chunks)
    log('글 묶음 text %d개(상주 묶음 안 사본 %d표) · patch %d개' % (len(repl['text']) - (1 if nres else 0), nres, len(repl['patch'])))
    # 5) 글꼴
    nutb, fdb = font_build(cmap)
    log('글꼴 nut %d B md5 %s · fnt md5 %s' % (len(nutb), hashlib.md5(nutb).hexdigest(), hashlib.md5(fdb).hexdigest()))
    # 6) CPK
    disc = os.path.join(BUILD, 'disc', 'USRDIR'); os.makedirs(disc, exist_ok=True)
    cpkw.rebuild(os.path.join(ORIG, 'text.cpk'), os.path.join(disc, 'text.cpk'), repl['text'], log)
    cpkw.rebuild(os.path.join(ORIG, 'cdata.cpk'), os.path.join(disc, 'cdata.cpk'), {122: nutb, 123: fdb}, log)
    outs = [os.path.join(disc, 'text.cpk'), os.path.join(disc, 'cdata.cpk')]
    # DLC dat.cpk(업데이트 폴더 DLCnn) — 영어 자리 표만 바꿈
    import extract_dlc
    for (grp, d), ch in sorted((k, v) for k, v in new.items() if k[0] == 'dlc'):
        src = os.path.join(ORIG, d + '_dat.cpk'); T = extract_dlc.dlc_tables(src)
        c = cpk.Cpk(src); E = {e['id']: e for e in c.files}
        lang, strs = mstext.read_table(c.read(E[T[0][0]])); c.f.close()
        for i, v in ch.items(): strs[i] = v
        b = mstext.write_table(lang, strs); assert mstext.read_table(b) == (lang, strs)
        od = os.path.join(BUILD, 'update', 'USRDIR', d); os.makedirs(od, exist_ok=True)
        cpkw.rebuild(src, os.path.join(od, 'dat.cpk'), {T[0][0]: b}, log)
        c = cpk.Cpk(os.path.join(od, 'dat.cpk')); E = {e['id']: e for e in c.files}
        assert mstext.read_table(c.read(E[T[0][0]]))[1] == strs; c.f.close()
        outs.append(os.path.join(od, 'dat.cpk'))
    if repl['patch']:
        upd = os.path.join(BUILD, 'update', 'USRDIR'); os.makedirs(upd, exist_ok=True)
        cpkw.rebuild(os.path.join(ORIG, 'patch.cpk'), os.path.join(upd, 'patch.cpk'), repl['patch'], log)
        outs.append(os.path.join(upd, 'patch.cpk'))
    # 7) 검산: 만든 CPK 를 다시 읽어 써 넣은 항목이 그대로인지
    n = 0
    for (grp, g), ch in new.items():
        if grp == 'dlc': n += len(ch); continue                  # DLC 는 위에서 다시 읽어 검산함
        p = os.path.join(disc, 'text.cpk') if grp == 'text' else os.path.join(BUILD, 'update', 'USRDIR', 'patch.cpk')
        c = cpk.Cpk(p); E = {e['id']: e for e in c.files}
        strs = mstext.read_table(c.read(E[g + EN]))[1]
        for i, v in ch.items(): assert strs[i] == v; n += 1
        c.f.close()
    if nres:
        c = cpk.Cpk(os.path.join(disc, 'text.cpk')); E = {e['id']: e for e in c.files}
        cs = [mstext.chunk_trim(x, False) if x.strip(b'\0') else x for x in mstext.pack_split(c.read(E[RESIDENT + EN]))]
        assert sum(1 for x in cs if x in {repl['text'][g + EN] for (grp, g) in new if grp == 'text'}) == nres
        c.f.close()
    log('검산: 써 넣은 %d항목 다시 읽어 일치 · 상주 사본 %d표 일치' % (n, nres))
    for p in outs: log('  %s md5 %s' % (os.path.relpath(p, ROOT), hashlib.md5(open(p, 'rb').read()).hexdigest()))
    with open(os.path.join(BUILD, 'charmap.tsv'), 'w', encoding='utf-8') as o:
        o.write('음절\t칸\t대역 한자\t쓰인 수\n')
        for s, (cell, kan) in cmap.items(): o.write('%s\t%d\t%s\t%d\n' % (s, cell, kan, freq[s]))
    open(os.path.join(BUILD, 'report.txt'), 'w', encoding='utf-8').write('\n'.join(rep) + '\n')
    # 글자판 미리보기(빌드 파일 되읽음): 많이 쓰는 음절 앞 192개
    es = nut.entries(nutb); im = nut.decode(nutb, es[0]); C = font_hires.C
    cells_ = [cell for s, (cell, kan) in list(cmap.items())[:192] if cell < 4096]
    if cells_:
        tiles = [im[(c // 64) * C:(c // 64) * C + C, (c % 64) * C:(c % 64) * C + C] for c in cells_]
        while len(tiles) % 16: tiles.append(np.zeros_like(tiles[0]))
        grid = np.vstack([np.hstack(tiles[i:i + 16]) for i in range(0, len(tiles), 16)])
        rgb = grid[:, :, :3].astype(np.float32); al = grid[:, :, 3:4].astype(np.float32) / 255
        Image.fromarray((rgb * al + 96 * (1 - al)).astype(np.uint8)).save(os.path.join(BUILD, '미리보기_글자판_자주쓰는음절.png'))


if __name__ == '__main__':
    main()
