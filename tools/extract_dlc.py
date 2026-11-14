# -*- coding: utf-8 -*-
r"""DLC 파츠 이름·설명 표 추출 (2026-11-15 하스피 «dlc 파츠들 미번역»)
  DLC = dev_hdd0/game/BLUS30736/USRDIR/DLCnn/dat.cpk (edat 아님, 평문 CPK). 그 안에 글 표 8개(언어 자리 0~7, 0 영어 · 6·7 일본어)
  = DLC 파츠 이름 표(누적 사본 — DLC 마다 그 시점까지의 표, 06·07·08·09·10~13). 빈 자리는 «arm_201» 같은 자리표.
  → work/extract/dlc.tsv (id = DLCnn#항목 · 일본어 · 영어 · 표시) · 원본 사본 work/orig_install/DLCnn_dat.cpk
  → my files/tsv/sc5_036.tsv : 본편 번역(work/text/fixed)에 같은 원문이 없는 고유 일본어만(번호 09529~)
  python tools/extract_dlc.py
"""
import os, re, sys, glob, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import cpk, mscrypt, mstext

UPD = r'D:\hospi\rpcs3\dev_hdd0\game\BLUS30736\USRDIR'
PH = re.compile(rb'^[a-z]+_\d+$')


def dlc_tables(path):
    """→ {자리: (cpk 항목 번호, [문자열])} — 글 표 8개(차례대로 자리 0~7)"""
    c = cpk.Cpk(path); t = []
    for e in c.files:
        if e['usize'] > 2_000_000: continue
        try:
            pt, _ = mscrypt.dec(c.read(e)); t.append((e['id'], mstext.parse(pt)[1]))
        except Exception:
            pass
    c.f.close()
    assert len(t) == 8 and len({len(s) for _, s in t}) == 1, (path, len(t))
    return {k: t[k] for k in range(8)}


def dlcs():
    return sorted(d for d in os.listdir(UPD) if d.startswith('DLC') and os.path.exists(os.path.join(UPD, d, 'dat.cpk')))


def esc(s): return s.decode('utf-8').replace('\\', '\\\\').replace('\n', '\\n').replace('\t', '\\t')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(os.path.join(ROOT, 'work', 'extract'), exist_ok=True)
    rows = []
    for d in dlcs():
        src = os.path.join(UPD, d, 'dat.cpk'); bk = os.path.join(ROOT, 'work', 'orig_install', d + '_dat.cpk')
        if not os.path.exists(bk): shutil.copy(src, bk)
        T = dlc_tables(bk)
        en, jp = T[0][1], T[6][1]
        for i, (e, j) in enumerate(zip(en, jp)):
            flag = 'keep' if PH.match(e) or not re.search('[ぁ-ヿ㐀-鿿]', j.decode('utf-8')) else ''
            rows.append(('%s#%d' % (d, i), esc(j), esc(e), flag))
    with open(os.path.join(ROOT, 'work', 'extract', 'dlc.tsv'), 'w', encoding='utf-8', newline='\n') as o:
        o.write('id\t일본어\t영어\t표시\n'); o.writelines('\t'.join(r) + '\n' for r in rows)
    fixed = set()
    for p in glob.glob(os.path.join(ROOT, 'work', 'text', 'fixed', '*.tsv')):
        for ln in open(p, encoding='utf-8'):
            c = ln.rstrip('\n').split('\t')
            if len(c) >= 5 and c[0][:1].isdigit(): fixed.add(c[3])
    need = {}
    for id_, j, e, f in rows:
        if not f and j not in fixed: need.setdefault(j, [id_, 0])[1] += 1
    out = os.path.join(ROOT, 'my files', 'tsv', 'sc5_036.tsv')
    with open(out, 'w', encoding='utf-8', newline='\n') as o:
        o.write('번호\t위치\t겹침\tJP\tKO\n')
        for k, (j, (id_, n)) in enumerate(need.items()):
            o.write('%05d\t%s\t%d\t%s\t\n' % (9529 + k, id_, n, j))
    print('DLC %d개 · 항목 %d · 번역 대상 고유 %d(본편에 같은 원문 있는 것 뺀 새 줄 %d) → %s'
          % (len(dlcs()), len(rows), len({r[1] for r in rows if not r[3]}), len(need), out))


if __name__ == '__main__':
    main()
