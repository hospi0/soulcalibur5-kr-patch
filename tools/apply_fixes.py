# -*- coding: utf-8 -*-
r"""하스피 번역(my files/번역, 읽기만) → 전편 통일·규칙 → work/text/fixed/ + 기록 work/text/fixes_log.tsv
(2026-11-15 하스피 «일치하는건 전부 퓌라 콜로세움 3번은 규칙대로 20줄은 알아서»)

차례(줄마다)
  1 전편 통일: 일본어 원문이 SC4 번역표(soulcalibur4-kr-patch/work/text/fixed)와 «똑같으면» SC4 번역을 그대로
  2 용어 규칙: SC4 apply_fixes.RULES(하스피가 정한 이름·UI 용어: 소울엣지·키릭·탈림·캐릭터 선택·재시도·자동 저장…)
     + SC5 규칙(ピュラ = 퓌라 · グローバルコロッセオ = 콜로세움) — 원문 조건이 있는 줄만, 뒤 조사는 받침에 맞춤
  3 거센소리: 원문이 가나뿐인 읽는 법 줄(기술 이름 등) → kana_kr(か행 ㅋ·た행 ㅌ·つ 츠·장음 안 적음)
  4 낱말 퍼뜨리기: 1·3 에서 바뀐 짧은 낱말(원문 2자 이상)의 옛 표기를, 그 원문 낱말이 든 다른 줄 번역에서 새 표기로
  5 한자 병기 삭제 · 한국식 부호 · 괄호 원문 유지(SC4 와 같음)
  6 손질: work/text/manual.tsv (번호 · 찾기 · 바꾸기 · 이유) — 장음 기호·줄 넘침 등
  python tools/apply_fixes.py
"""
import os, re, sys, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SC4T = os.path.join(os.path.dirname(ROOT), 'soulcalibur4-kr-patch', 'tools')
sys.path.insert(0, SC4T)
import apply_fixes as A4, kana_kr                     # SC4 규칙·함수(읽기만 씀)

SRC = os.path.join(ROOT, 'my files', '번역')
SC4FIX = os.path.join(os.path.dirname(ROOT), 'soulcalibur4-kr-patch', 'work', 'text', 'fixed')
OUT = os.path.join(ROOT, 'work', 'text', 'fixed')
LOG = os.path.join(ROOT, 'work', 'text', 'fixes_log.tsv')
NH = A4.NH
RULES5 = [
    (r'ピュラ', NH + r'(?:퓨라|피라|퓌라)', '퓌라', '퓌라(하스피 2026-11-15)'),
    (r'グローバルコロッセオ|コロッセオ', r'콜로세오', '콜로세움', '콜로세움(하스피 2026-11-15)'),
    (r'プレデーション', r'프레데이션', '프리데이션', '프리데이션(하스피)'),
    (r'ラスターベイバロン', r'러스터 ?베이버론', '래스터 베이바론', '래스터 베이바론(하스피)'),
    (r'ポーズメニュー', r'포즈 ?메뉴', '일시정지 메뉴', '일시정지 메뉴(하스피 — 캐릭터 포즈는 그대로)'),
    (r'フレンドランキング', r'프렌드 ?랭킹', '친구 랭킹', '친구 랭킹(하스피)'),
    (r'デフォルト', r'디폴트', '기본', '기본(하스피)'),
    (r'カスミ', NH + r'가스미', '카스미', '거센소리(가타카나 이름)'),
    (r'クサカゲ', NH + r'구사카게', '쿠사카게', '거센소리(가타카나 이름)'),
    (r'クサカリ', NH + r'구사카리', '쿠사카리', '거센소리(가타카나 이름)'),
    (r'クレナイ', NH + r'구레나이', '쿠레나이', '거센소리(가타카나 이름)'),
    (r'ツクヨミ', NH + r'쓰쿠요미', '츠쿠요미', '거센소리(가타카나 이름)'),
    (r'トリノ', NH + r'도리노', '토리노', '거센소리(가타카나 이름)'),
    (r'カヤハラ', NH + r'가야하라', '카야하라', '거센소리(가타카나 이름)'),
    (r'カワセミ', NH + r'가와세미', '카와세미', '거센소리(가타카나 이름)'),
    (r'アカツキ', NH + r'아카쓰키', '아카츠키', '거센소리(가타카나 이름)'),
    (r'カゲツキ', NH + r'가게쓰키', '카게츠키', '거센소리(가타카나 이름)'),
    (r'カイクウフンヌコン', NH + r'가이쿠푼누콘', '카이쿠푼누콘', '거센소리(가타카나 이름)'),
]
TOKS = re.compile(r'\$z[0-9.]+/[0-9.]+/|\$[A-Z][0-9]+/|<s\$Q[0-9]+/s>|\$[a-y]/?|%[-+0-9.]*[a-zA-Z]|<[A-Z_ 0-9]+>')
READ = re.compile('^[ぁ-ゖァ-ヺ・\\s　]+$')    # 가나뿐(ー 없는) = 읽는 법·기술 이름
TERMJ = re.compile('^[ぁ-ヿ㐀-鿿・ー＝]+$')
HAN = re.compile('[㐀-鿿豈-﫿]')


def _skel(s):
    """음차 비교용: 한글 음절만 · ㄱ=ㅋ ㄷ=ㅌ ㅈ=ㅊ 쓰=츠 · 장음(에 뒤 이, 오·우·요·유 뒤 우) · 받침 ㅅ/ㄴ 은 그대로"""
    syl = [kana_kr._norm(ch) for ch in s if '가' <= ch <= '힣']
    out = []
    for ch in syl:
        if out and kana_kr.split(out[-1])[2] == ' ':
            v = kana_kr.split(out[-1])[1]
            if ch == '이' and v in 'ㅔㅖ' or ch == '우' and v in 'ㅗㅜㅛㅠ':
                continue
        out.append(ch)
    return out


def is_translit(jp, ko):
    """번역 ko 가 가나 jp 의 음차인가(표기 규칙 차이만 있는가)"""
    a = _skel(ko); b = _skel(''.join(kana_kr.kana2kr(jp)))
    return bool(a) and a == b


def in_moves(pos):
    """기술표 묶음(text 00216~00423)"""
    m = re.match(r'text/(\d+)#', pos)
    return bool(m) and 216 <= int(m.group(1)) < 424


KATANAME = re.compile('^[ァ-ヺー・＝]+$')


def load4():
    d = {}
    for p in sorted(glob.glob(os.path.join(SC4FIX, '*.tsv'))):
        for ln in open(p, encoding='utf-8-sig'):
            c = ln.rstrip('\n').split('\t')
            if len(c) >= 5 and c[0][:1].isdigit() and c[4].strip(): d[c[3]] = c[4]
    return d


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sc4 = load4()
    sc4core = {}                                       # 토큰 뗀 원문 → 토큰 뗀 번역(짧은 낱말 줄)
    for j, k in sc4.items():
        jj = TOKS.sub('', j).strip()
        if TERMJ.match(jj): sc4core.setdefault(jj, TOKS.sub('', k).strip())
    manual = collections.defaultdict(list)
    mp = os.path.join(ROOT, 'work', 'text', 'manual.tsv')
    if os.path.exists(mp):
        for ln in open(mp, encoding='utf-8-sig').read().splitlines()[1:]:
            if ln.strip():
                no, a, b, why = ln.split('\t'); manual[no].append((a, b, why))
    files = sorted(glob.glob(os.path.join(SRC, '*.tsv')))
    data = []                                          # (파일, [줄 칸들])
    for f in files:
        lines = open(f, encoding='utf-8-sig').read().splitlines()
        data.append((f, lines[0], [ln.split('\t') for ln in lines[1:] if ln.strip()]))
    rows = [c for _, _, cs in data for c in cs]
    orig = {c[0]: c[4] for c in rows}
    why = collections.defaultdict(list)
    adopted = set()
    # 1·2·3
    for c in rows:
        jp = c[3]; t = c[4]
        if jp in sc4:
            if sc4[jp] != t: t = sc4[jp]; why[c[0]].append('전편 번역')
            adopted.add(c[0])
        elif TOKS.sub('', jp).strip() in sc4core and TERMJ.match(TOKS.sub('', jp).strip()):
            core4 = sc4core[TOKS.sub('', jp).strip()]
            m = re.match(r'^((?:%s)*)(.*?)((?:%s)*)$' % (TOKS.pattern, TOKS.pattern), t)
            if m and m.group(2).strip() != core4:
                t = m.group(1) + core4 + m.group(3); why[c[0]].append('전편 번역(토큰 뺀 원문 같음)')
            adopted.add(c[0])
        else:
            for jre, kre, b, r in A4.RULES + RULES5:
                if re.search(jre, jp):
                    t2 = A4.replace(t, kre, b)
                    if t2 != t: t = t2; why[c[0]].append(r)
            jplain = TOKS.sub('', jp)
            kata_ok = not re.search('[ァ-ヺ]', jplain) or in_moves(c[1])     # 가타카나 줄은 기술표 묶음만(レイシャ 같은 인물 이름은 장음 살림)
            if READ.match(jplain) and kata_ok and re.search('[가-힣]', t) and is_translit(jplain, t):
                # 번역이 그 가나의 «음차»일 때만(외래어 뜻 옮김 리플레이·랭킹, 뜻 번역 앉기 등은 건드리지 않음)
                if ' ' not in t.strip() and '　' not in t:
                    t2 = ''.join(x for x in kana_kr.kana2kr(jplain) if x.strip() or x == '・')
                    t2 = t2.replace('・', '·')
                else:
                    t2 = kana_kr.aspirate(jplain, t)
                if t2 != t: t = t2; why[c[0]].append('거센소리(읽는 법)')
        c[4] = t
    # 4 짧은 낱말 퍼뜨리기
    tmap = {}
    for c in rows:
        j = TOKS.sub('', c[3]).strip()
        o, n = TOKS.sub('', orig[c[0]]).strip(), TOKS.sub('', c[4]).strip()
        if o != n and 2 <= len(j) <= 20 and TERMJ.match(j) and len(o) >= 2 and re.search('[가-힣]', o) and '\\n' not in o:
            tmap.setdefault(j, (o, n))
    spread = 0
    for j in sorted(tmap, key=len, reverse=True):
        o, n = tmap[j]
        for c in rows:
            if c[0] in adopted or j not in c[3] or TOKS.sub('', c[3]).strip() == j: continue
            if not KATANAME.match(j) and not in_moves(c[1]): continue      # 한자·히라가나 낱말(자세 이름 등)은 기술표 안에서만
            if o in c[4]:
                t2 = A4.replace(c[4], re.escape(o), n)
                if t2 != c[4]: c[4] = t2; why[c[0]].append('낱말 통일 %s→%s' % (o, n)); spread += 1
    # 5·6
    seen = set()
    for c in rows:
        t = c[4]
        t2 = A4.HANJA_PAREN.sub('', t)
        if t2 != t: t = t2; why[c[0]].append('한자 병기 삭제')
        t2 = re.sub('：(?=　)', A4.LAYOUT_COLON, t).translate(A4.PUNCT).replace(A4.LAYOUT_COLON, '：')
        if t2 != t: t = t2; why[c[0]].append('한국식 부호')
        t2 = A4.restore_brackets(c[3], t)
        if t2 != t: t = t2; why[c[0]].append('괄호 원문 유지')
        for a, b, r in manual.get(c[0], []):
            if a not in t: raise SystemExit('manual.tsv 찾기 실패 %s: %s' % (c[0], a))
            t = t.replace(a, b); why[c[0]].append('손질: ' + r); seen.add(c[0])
        c[4] = t
    assert seen == set(manual), '손질 번호 못 찾음 %s' % (set(manual) - seen)
    os.makedirs(OUT, exist_ok=True)
    for f, head, cs in data:
        name = re.sub(r'_ko(?=\.tsv$)', '', os.path.basename(f))
        open(os.path.join(OUT, name), 'w', encoding='utf-8', newline='\n').write(head + '\n' + ''.join('\t'.join(c) + '\n' for c in cs))
    log = ['번호\t위치\tJP\t수정 전\t수정 후\t이유']
    cnt = collections.Counter()
    for c in rows:
        if c[4] != orig[c[0]]:
            log.append('\t'.join((c[0], c[1], c[3], orig[c[0]], c[4], ' / '.join(why[c[0]]))))
            for w_ in why[c[0]]: cnt[w_.split(' ')[0] if w_.startswith(('낱말', '손질')) else w_] += 1
    open(LOG, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(log) + '\n')
    print('바꾼 줄 %d / %d (전편과 원문 같은 줄 %d) → %s' % (len(log) - 1, len(rows), len(adopted), OUT))
    for k, v in cnt.most_common(): print('  %-30s %d' % (k, v))


if __name__ == '__main__':
    main()
