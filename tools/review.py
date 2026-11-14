# -*- coding: utf-8 -*-
r"""SC5 번역 검토 (2026-11-15 하스피 «용어 인물 토큰 줄넘침 지명 전편과의 통일성»)
  입력: my files/번역/*.tsv (읽기만) · SC4 work/text/fixed/*.tsv · work/extract/all.tsv
  출력: work/review/*.tsv + 요약(화면)
   1 토큰.tsv            build.check 걸린 줄(토큰·줄 수·한자·가나·글꼴 밖 글자)
   2 전편_같은원문.tsv    SC4 와 일본어가 똑같은데 번역이 다른 줄
   3 용어_전편다름.tsv    짧은 낱말(이름·지명·기술·메뉴)의 SC5 표기 ≠ SC4 표기
   4 용어_흔들림.tsv      짧은 낱말 표기(SC5 단독 줄)가 그 낱말이 든 긴 문장 번역에 안 나오는 경우(표기 흔들림 후보)
   5 거센소리.tsv         가타카나 か·た행 첫소리 → 한글이 ㄱ·ㄷ 로 시작 / ツ → 쓰
   6 줄넘침.tsv           한 줄 폭(한글·전각 2, 반각 1)이 그 묶음 일본어 최대 줄 폭을 넘는 줄
  python tools/review.py
"""
import os, re, sys, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import build

OUT = os.path.join(ROOT, 'work', 'review', 'fixed') if '--fixed' in sys.argv else os.path.join(ROOT, 'work', 'review')
SC4 = os.path.join(os.path.dirname(ROOT), 'soulcalibur4-kr-patch', 'work', 'text', 'fixed')
KATA = re.compile('^[ァ-ヺー・･・＝=]+$')
TERM = re.compile('^[ぁ-ヿ㐀-鿿・ー＝]+$')       # 부호·공백 없는 짧은 낱말
NL = chr(92) + 'n'


def load(files):
    d = {}
    for p in files:
        for ln in open(p, encoding='utf-8-sig'):
            c = ln.rstrip('\n').rstrip('\r').split('\t')
            if len(c) >= 5 and c[0][:1].isdigit() and c[4].strip():
                d[c[3]] = dict(ko=c[4], pos=c[1], no=c[0], f=os.path.basename(p))
    return d


def width(s):
    s = build.TOK.sub('', s)
    return sum(1 if ord(ch) < 0x100 or 0xff61 <= ord(ch) <= 0xff9f else 2 for ch in s)


def strip_tok(s): return build.TOK.sub('', s)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(OUT, exist_ok=True)
    src = os.path.join(ROOT, 'work', 'text', 'fixed') if '--fixed' in sys.argv else os.path.join(ROOT, 'my files', '번역')
    s5 = load(sorted(glob.glob(os.path.join(src, '*.tsv'))))
    s4 = load(sorted(glob.glob(os.path.join(SC4, '*.tsv'))))
    rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'work', 'extract', 'all.tsv'), encoding='utf-8')][1:]
    pos_of = collections.defaultdict(list)
    for r in rows:
        if not r[3]: pos_of[r[1]].append(r[0])
    summary = []
    def w(name, head, lines):
        with open(os.path.join(OUT, name), 'w', encoding='utf-8') as o:
            o.write(head + '\n'); o.writelines(l + '\n' for l in lines)
        summary.append('%-22s %5d' % (name, len(lines)))
    # 1 토큰
    L = []
    for jp, v in sorted(s5.items(), key=lambda x: x[1]['no']):
        _, errs = build.check(jp, v['ko'])
        if errs: L.append('\t'.join([v['no'], v['f'], v['pos'], ' · '.join(errs), jp, v['ko']]))
    w('1_토큰.tsv', '번호\t파일\t위치\t문제\tJP\tKO', L)
    # 2 전편 같은 원문
    L = []
    for jp, v in sorted(s5.items(), key=lambda x: x[1]['no']):
        if jp in s4 and s4[jp]['ko'] != v['ko']:
            L.append('\t'.join([v['no'], v['f'], v['pos'], jp, v['ko'], s4[jp]['ko']]))
    w('2_전편_같은원문.tsv', '번호\t파일\t위치\tJP\tSC5\tSC4', L)
    # 3 용어(짧은 낱말) 전편 비교
    def terms(d):
        t = {}
        for jp, v in d.items():
            j = strip_tok(jp).strip()
            if 2 <= len(j) <= 14 and TERM.match(j):
                t[j] = strip_tok(v['ko']).strip()
        return t
    t5, t4 = terms(s5), terms(s4)
    L = []
    for j in sorted(t5):
        if j in t4 and t4[j] != t5[j]:
            L.append('\t'.join([j, t5[j], t4[j], s5_no(s5, j)]))
    w('3_용어_전편다름.tsv', 'JP\tSC5\tSC4\tSC5번호', L)
    # 4 용어 흔들림: 가타카나 이름(3자 이상)의 SC5 단독 표기가, 그 이름이 든 긴 문장 번역에 없는 경우
    L = []
    long5 = [(strip_tok(jp), strip_tok(v['ko']), v) for jp, v in s5.items()]
    for j, k in sorted(t5.items()):
        if not KATA.match(j) or len(j) < 3 or not re.search('[가-힣]', k): continue
        kk = k.replace(' ', '')
        miss = [(v['no'], ko) for jj, ko, v in long5 if j in jj and jj != j and kk not in ko.replace(' ', '')]
        hit = sum(1 for jj, ko, v in long5 if j in jj and jj != j) - len(miss)
        if miss:
            L.append('\t'.join([j, k, str(hit), str(len(miss)), ' / '.join('%s:%s' % (n, ko[:40]) for n, ko in miss[:4])]))
    w('4_용어_흔들림.tsv', 'JP\tSC5 단독 표기\t긴 문장에 그 표기 있음\t없음\t없는 예(번호:번역)', L)
    # 5 거센소리
    KT = {'カ': '카', 'キ': '키', 'ク': '쿠', 'ケ': '케', 'コ': '코', 'タ': '타', 'テ': '테', 'ト': '토', 'チ': '치'}
    L = []
    for j, k in sorted(t5.items()):
        if not KATA.match(j): continue
        k0 = k.lstrip()
        if j[0] in KT and k0[:1] and '가' <= k0[0] <= '힣':
            cho = (ord(k0[0]) - 0xAC00) // 588
            if cho in (0, 3):           # ㄱ ㄷ
                L.append('\t'.join([j, k, '첫소리 %s → %s 기대' % (j[0], KT[j[0]][0]), s5_no(s5, j)]))
        if 'ツ' in j and '쓰' in k:
            L.append('\t'.join([j, k, 'ツ → 츠', s5_no(s5, j)]))
    w('5_거센소리.tsv', 'JP\tSC5\t문제\tSC5번호', L)
    # 6 줄넘침: 묶음(위치 앞부분)별 일본어 최대 줄 폭 = 상자 폭 근사
    boxw = collections.defaultdict(int)
    for r in rows:
        if r[3]: continue
        b = r[0].split('#')[0]
        for ln in r[1].split(NL): boxw[b] = max(boxw[b], width(ln))
    L = []
    for jp, v in sorted(s5.items(), key=lambda x: x[1]['no']):
        bw = max(boxw[p.split('#')[0]] for p in pos_of.get(jp, [v['pos']]))
        jmax = max(width(x) for x in jp.split(NL))
        for i, ln in enumerate(v['ko'].split(NL)):
            kw = width(ln)
            if kw > bw:
                L.append('\t'.join([v['no'], v['f'], v['pos'], '%d줄' % (i + 1), '번역 %d > 묶음 최대 %d (원문 최대 %d)' % (kw, bw, jmax), jp, v['ko']]))
    w('6_줄넘침.tsv', '번호\t파일\t위치\t줄\t폭\tJP\tKO', L)
    print('검토 결과 → work/review/'); print('\n'.join(summary))


def s5_no(s5, j):
    for jp, v in s5.items():
        if strip_tok(jp).strip() == j: return v['no']
    return ''


if __name__ == '__main__':
    main()
