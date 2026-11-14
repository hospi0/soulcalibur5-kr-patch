# -*- coding: utf-8 -*-
"""번역용 TSV 를 18KB 단위로 my files/tsv/ 에 나눠 쓴다.

입력 work/extract/all.tsv (tools/extract.py). 번역 대상(표시 빈 것)만, 같은 일본어 문장은 처음 것 하나만.
열: 번호 · 위치(처음 나온 id) · 겹침(같은 문장 수) · JP · KO(빈칸)
순서: text(디스크 text.cpk, 묶음 차례 — 216~ 는 기술표) -> patch(업데이트 patch.cpk). (틀 = soulcalibur4-kr-patch). 줄바꿈은 «\\n».

python tools/export_tsv.py
"""
import os, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'work', 'extract', 'all.tsv')
OUT = os.path.join(ROOT, 'my files', 'tsv')
LIMIT = 18 * 1024
HEAD = '번호\t위치\t겹침\tJP\tKO\n'
ORDER = {"text": 0, "patch": 1}


def main():
    rows = []
    with open(SRC, encoding='utf-8') as f:
        next(f)
        for ln in f:
            i, jp, en, flag = ln.rstrip('\n').split('\t')
            if not flag:
                rows.append((i, jp))
    # 묶음 순서로(안정 정렬 — 묶음 안 차례는 그대로)
    rows.sort(key=lambda r: ORDER[r[0].split('/')[0]])
    first, count = {}, {}
    for i, jp in rows:
        if jp not in first:
            first[jp] = i
        count[jp] = count.get(jp, 0) + 1
    lines = ['%05d\t%s\t%d\t%s\t\n' % (n + 1, i, count[jp], jp) for n, (jp, i) in enumerate(first.items())]
    # 18KB 넘기 전에 끊기
    chunks, cur, size = [], [], len(HEAD.encode('utf-8'))
    for ln in lines:
        b = len(ln.encode('utf-8'))
        if cur and size + b > LIMIT:
            chunks.append(cur); cur, size = [], len(HEAD.encode('utf-8'))
        cur.append(ln); size += b
    if cur:
        chunks.append(cur)
    # 자투리: 마지막 묶음이 앞 묶음에 들어가면 합침(pop 먼저)
    if len(chunks) >= 2:
        last = chunks.pop()
        if len((HEAD + ''.join(chunks[-1]) + ''.join(last)).encode('utf-8')) <= LIMIT:
            chunks[-1] = chunks[-1] + last
        else:
            chunks.append(last)
    os.makedirs(OUT, exist_ok=True)
    assert not glob.glob(os.path.join(OUT, 'sc5_*.tsv')), '이미 있음 — 덮어쓰지 않음'
    tot = 0
    for k, c in enumerate(chunks):
        data = (HEAD + ''.join(c)).encode('utf-8')
        assert len(data) <= LIMIT or len(c) == 1
        open(os.path.join(OUT, 'sc5_%03d.tsv' % (k + 1)), 'wb').write(data)
        tot += len(c)
    # 검산: 번호 연속·누락 0
    seen = []
    for p in sorted(glob.glob(os.path.join(OUT, 'sc5_*.tsv'))):
        with open(p, encoding='utf-8') as f:
            next(f)
            seen += [int(ln.split('\t')[0]) for ln in f]
    assert seen == list(range(1, len(lines) + 1)), '번호 불연속'
    grp = {}
    for jp, i in first.items():
        g = i.split('/')[0]; grp[g] = grp.get(g, 0) + 1
    print('번역 대상 %d 항목 -> 고유 %d 줄 %s, 파일 %d 개 (번호 연속 확인)' % (len(rows), len(lines), grp, len(chunks)))
    print('->', OUT)


if __name__ == '__main__':
    main()
