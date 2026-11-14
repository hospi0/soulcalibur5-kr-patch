# -*- coding: utf-8 -*-
r"""번역 대상 전수 추출 (소울칼리버 V) -> work/extract/all.tsv  (id · 일본어 · 영어 · 표시)

원본: 디스크 text.cpk(424 = 8언어 × 53묶음, 마지막 묶음 00424~00431 = 상주 묶음 = 개별 표 사본이라 뺌)
      + 업데이트 patch.cpk(00000~00015 = 글 표 2묶음; 00016·00024·00032 는 다른 형식)
자리: 0 영어 · 6 일본어 (7 = 일본어 사본)
id = text/<묶음 첫 번호>#<항목> · patch/<묶음 첫 번호>#<항목>
표시: keep = 일본어에 가나·한자 없음(영문 메뉴·dummy·커맨드 기호) -> 영어 원문 유지 / empty = 빈 항목
줄바꿈은 «\n» 으로 적는다.  (틀 = soulcalibur4-kr-patch/tools/extract.py)

python tools/extract.py
"""
import os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpk, mstext, mscrypt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISC = r'D:\hospi\rpcs3\games\Soulcalibur V (USA)\PS3_GAME\USRDIR'
UPD = r'D:\hospi\rpcs3\dev_hdd0\game\BLUS30736\USRDIR'
OUT = os.path.join(ROOT, 'work', 'extract')
EN, JP = 0, 6
JPC = re.compile('[ぁ-ヿ㐀-鿿]')     # 가나·한자 없는 항목(영문 메뉴·dummy·커맨드 기호·®·～20) = 영어 원문 유지(SC4 와 같음)


def groups():
    """-> [(id 머리, 일본어 문자열들, 영어 문자열들)]"""
    out = []
    for tag, path, first, last in (('text', os.path.join(DISC, 'text.cpk'), 8, 424), ('patch', os.path.join(UPD, 'patch.cpk'), 0, 16)):
        c = cpk.Cpk(path)
        byid = {e['id']: e for e in c.files}
        for g in range(first, last, 8):
            tab = {}
            for slot in (EN, JP):
                pt, sig = mscrypt.dec(c.read(byid[g + slot]))
                tab[slot] = mstext.parse(pt)[1]
            out.append(('%s/%05d' % (tag, g), tab[JP], tab[EN]))
    return out


def esc(s):
    return s.decode('utf-8').replace('\\', '\\\\').replace('\n', '\\n').replace('\t', '\\t')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(OUT, exist_ok=True)
    stat = collections.defaultdict(lambda: [0, 0, 0])
    with open(os.path.join(OUT, 'all.tsv'), 'w', encoding='utf-8', newline='\n') as o:
        o.write('id\t일본어\t영어\t표시\n')
        for name, js, es in groups():
            assert len(js) == len(es), name
            grp = name.split('/')[0]
            for i, (j, e) in enumerate(zip(js, es)):
                flag = 'empty' if not j and not e else ('keep' if not JPC.search(j.decode('utf-8')) else '')
                o.write('%s#%d\t%s\t%s\t%s\n' % (name, i, esc(j), esc(e), flag))
                st = stat[grp]; st[0] += 1
                if not flag:
                    st[1] += 1; st[2] += len(j.decode('utf-8'))
    for g, (n, t, ch) in stat.items():
        print('%-6s 항목 %6d · 번역 대상 %6d · 일본어 %7d자' % (g, n, t, ch))
    print('->', os.path.join(OUT, 'all.tsv'))


if __name__ == '__main__':
    main()
