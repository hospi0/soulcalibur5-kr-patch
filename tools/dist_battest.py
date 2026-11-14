# -*- coding: utf-8 -*-
r"""배포 bat 시험 (2026-11-15, 틀 = mystara dist_battest): «& ( )» 든 임시 폴더에 원본을 깔고 단계마다 MD5 대조.
  ① 업데이트·DLC 전부 있음: 적용 → 재적용(건너뜀) → 되돌리기
  ② 업데이트 있음·DLC 일부만(DLC06·DLC13): 적용 → 되돌리기 (없는 DLC 는 건너뛰어야 함)
  ③ 업데이트 없음(빈 Enter): 적용 → 되돌리기 (디스크 쪽만)
  상태 글자: 새 = 한글판 · 원 = 원본 · 없 = 파일 없음
  python tools/dist_battest.py SoulCalibur5_PS3_KR_v0.9   (임시 폴더 = %TEMP% 아래, 끝나면 지움 · 묶음 폴더의 원본백업도 지움)"""
import os, sys, shutil, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import make_dist as M


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    pkg = os.path.join(ROOT, 'dist', sys.argv[1])
    cases = [('업데이트·DLC 전부', True, None), ('DLC 일부(06·13)', True, {'DLC06/dat.cpk', 'DLC13/dat.cpk'}), ('업데이트 없음', False, set())]
    for title, with_upd, dlc_keep in cases:
        root = tempfile.mkdtemp(prefix='sc5bat_')
        try:
            game = os.path.join(root, 'Soulcalibur V (USA) & test', 'PS3_GAME')
            rp = os.path.join(root, 'rp & cs3 (x)'); upd = os.path.join(rp, 'dev_hdd0', 'game', M.TID, 'USRDIR')
            where = lambda k, f: os.path.join(upd if k in ('upd', 'dlc') else os.path.join(game, 'USRDIR'), *f.split('/'))
            for k, f in M.ITEMS:
                if k == 'dlc' and dlc_keep is not None and f not in dlc_keep: continue
                if k != 'disk' and not with_upd: continue
                d = where(k, f); os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy(M.orig_of(k, f), d)
            O = {f: M.md5(M.orig_of(k, f)) for k, f in M.ITEMS}; N = {f: M.md5(M.new_of(k, f)) for k, f in M.ITEMS}
            def state():
                out = ''
                for k, f in M.ITEMS:
                    p = where(k, f)
                    if not os.path.exists(p): out += '없'; continue
                    h = M.md5(p); out += '새' if h == N[f] else '원' if h == O[f] else '?'
                return out
            def run(bat):
                args = ['cmd', '/c', os.path.join(pkg, bat), game] + ([rp] if with_upd else [])
                r = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True)
                o = r.stdout.decode('cp949', 'replace')
                return [l.strip()[-60:] for l in o.splitlines() if 'OK' in l or '[!]' in l]
            print('== %s · 순서 %s' % (title, ' '.join(f.split('/')[0] for k, f in M.ITEMS)))
            print('적용 전  ', state())
            print(run('한글패치_적용.bat')); print('적용 뒤  ', state())
            if dlc_keep is None and with_upd:
                print(run('한글패치_적용.bat')); print('재적용 뒤', state())
            print(run('되돌리기.bat')); print('되돌린 뒤', state())
        finally:
            shutil.rmtree(root, True)
            shutil.rmtree(os.path.join(pkg, '원본백업'), True)


if __name__ == '__main__':
    main()
