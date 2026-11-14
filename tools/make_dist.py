# -*- coding: utf-8 -*-
r"""배포 묶음 (2026-11-15) — 소울칼리버 V (PS3 북미판 BLUS30736) 한글 패치
  dist/SoulCalibur5_PS3_KR_<버전>/ = patch\*.xdelta + xdelta.exe + readme.txt + 한글패치_적용.bat + 되돌리기.bat (+ zip)
  디스크 쪽 = PS3_GAME/USRDIR/text.cpk · cdata.cpk  /  업데이트 쪽(선택) = dev_hdd0/game/BLUS30736/USRDIR/patch.cpk
  원본 = work/orig_install (게임 폴더는 안 믿음), 새것 = work/build/{disc,update}/USRDIR. 만들고 나서 «원본에 적용 → 새것과 같음» 되짚기.
  규칙: MD5 대문자 · 한국어 문서·bat CP949(CRLF) · 버전 v0.9 꼴 · bat if 블록 안 echo 괄호 금지 · 경로 «&» 대응(set·echo 따옴표 안)
  (틀 = soulcalibur4-kr-patch / mystara-kr-patch make_dist)
  python tools/make_dist.py   →  python tools/dist_battest.py SoulCalibur5_PS3_KR_v0.9"""
import hashlib, os, shutil, subprocess, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
R = lambda *p: os.path.join(ROOT, *p)
VER = 'v0.9'
XDELTA = r'C:\claude\utils\xdelta.exe'
TID = 'BLUS30736'
ITEMS = [('disk', 'text.cpk'), ('disk', 'cdata.cpk'), ('upd', 'patch.cpk')] + \
        [('dlc', 'DLC%02d/dat.cpk' % n) for n in range(6, 14)]           # USRDIR 아래 · DLC = 업데이트 쪽, 있으면 패치(2026-11-15 하스피)
PROBE = 'cdata.cpk'


def orig_of(k, f): return R('work', 'orig_install', f.replace('/', '_'))
def new_of(k, f): return R('work', 'build', 'disc' if k == 'disk' else 'update', 'USRDIR', *f.split('/'))


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest().upper()


README = """소울칼리버 V (SOULCALIBUR V, PS3) 한글 패치 {ver}
================================================================

북미판 디스크 (BLUS30736) 용입니다. ★RPCS3 에서 확인했습니다.
게임 실행 파일(EBOOT)은 건드리지 않고 글·글꼴 데이터 파일만 바꿉니다.
(폴더로 풀어 둔 게임에 적용합니다. 디스크 원본 그대로는 바꿀 수 없습니다)

바꾸는 파일
  디스크 쪽(게임 폴더)          : text.cpk · cdata.cpk
  업데이트 쪽(1.03 업데이트, 선택) : patch.cpk  (RPCS3 의 dev_hdd0\\game\\{tid}\\USRDIR)
                                 온라인 메시지. 업데이트가 없으면 건너뜁니다.
  DLC (선택)                     : DLC06~DLC13 의 dat.cpk  (같은 USRDIR 아래, DLC 파츠 이름·설명)
                                 깔린 DLC 만 패치하고 없는 것은 건너뜁니다.


[ 적용 방법 ]

0. ★원본 게임 파일에 적용합니다.
1. 이 묶음을 아무 폴더에나 풉니다.
2. 「한글패치_적용.bat」 을 실행하고
   ① 게임 폴더를 끌어다 놓거나 경로를 적고 Enter (게임 최상위 폴더, PS3_GAME, USRDIR 어느 것이든)
   ② 이어서 RPCS3 폴더(rpcs3.exe 가 있는 곳)를 끌어다 놓거나 경로를 적고 Enter
      (dev_hdd0\\game\\{tid} 폴더를 줘도 됩니다. 업데이트를 안 깔았으면 그냥 Enter)
3. 배치가 파일마다
     원본 MD5 확인 → 원본을 이 묶음의 「원본백업」 폴더에 복사 → 패치 → 결과 MD5 확인
   을 하고 덮어씁니다. 이미 한글판인 파일은 건너뜁니다.
4. ★게임 언어는 PS3 시스템 언어를 따릅니다. RPCS3 의 시스템 언어를 「한국어」 나 「영어」 로 두세요.
   (이 게임은 한국어·영어 모두 영어 자리 글을 읽고, 그 자리에 한글이 들어갑니다)
5. 패치 전에 만든 스테이트(상태 저장)는 쓰지 마세요. 새로 부팅해서 확인하세요.

되돌리기 : 「되돌리기.bat」 → 같은 폴더들을 주면 「원본백업」 의 파일로 되돌립니다.
          (「원본백업」 폴더를 지우지 마세요)


[ 바뀌는 것 ]

■ 메뉴·옵션·도움말, 시스템 메시지(저장·로드·설치 안내는 PS3 시스템 창도 한글)
■ 스토리 대사와 자막, 승리·도발 대사
■ 캐릭터 크리에이션(파츠·장비 이름), 칭호, 플레이어 라이선스
■ 모든 캐릭터의 기술표(기술 이름·커맨드 설명)
■ 온라인 메시지·DLC 파츠 이름(1.03 업데이트 쪽)
■ 고해상도 한글 글꼴

[ 알려진 사항 ]

■ 메뉴 큰 제목(Story·Offline Play 등 장식 글꼴)은 원문 그대로입니다.
■ 일본판에도 영문으로 나오는 곡명·저작권 표기 등은 영문 그대로입니다.
■ 이름 입력 글자판은 영문 그대로입니다.


[ 원본 → 한글판 MD5 ]

{table}
"""

BAT = r"""@echo off
setlocal
chcp 949 >nul
cd /d "%~dp0"
set "XD=%~dp0xdelta.exe"
set "BK=%~dp0원본백업"

echo.
echo  ================================================================
echo    SOULCALIBUR V PS3 Korean Patch {ver}   [{tid}]
echo  ================================================================
echo.

if not exist "%XD%" goto NOXD

set "TARGET=%~1"
if not defined TARGET set /p "TARGET=  게임 폴더를 끌어다 놓거나 경로를 적고 Enter: "
set "TARGET=%TARGET:"=%"
if "%TARGET:~-1%"=="\" set "TARGET=%TARGET:~0,-1%"
set "DISK="
if exist "%TARGET%\{probe}" set "DISK=%TARGET%"
if exist "%TARGET%\USRDIR\{probe}" set "DISK=%TARGET%\USRDIR"
if exist "%TARGET%\PS3_GAME\USRDIR\{probe}" set "DISK=%TARGET%\PS3_GAME\USRDIR"
if not defined DISK goto NODEST
echo  게임 폴더 : "%DISK%"

set "T2=%~2"
if not defined T2 set /p "T2=  RPCS3 폴더를 끌어다 놓거나 경로를 적고 Enter - 업데이트가 없으면 그냥 Enter: "
set "UPD="
if not defined T2 goto UPDNO
set "T2=%T2:"=%"
if "%T2:~-1%"=="\" set "T2=%T2:~0,-1%"
if exist "%T2%\dev_hdd0\game\{tid}\USRDIR\patch.cpk" set "UPD=%T2%\dev_hdd0\game\{tid}\USRDIR"
if exist "%T2%\game\{tid}\USRDIR\patch.cpk" set "UPD=%T2%\game\{tid}\USRDIR"
if exist "%T2%\{tid}\USRDIR\patch.cpk" set "UPD=%T2%\{tid}\USRDIR"
if exist "%T2%\USRDIR\patch.cpk" set "UPD=%T2%\USRDIR"
if exist "%T2%\patch.cpk" set "UPD=%T2%"
:UPDNO
if defined UPD echo  업데이트  : "%UPD%"
if not defined UPD echo  업데이트  : 없음 - patch.cpk 는 건너뜁니다
echo.
if not exist "%BK%" mkdir "%BK%"
set /a DONE=0
set /a SKIP=0
{calls}
echo.
echo  [OK] 끝났습니다. 새로 패치 %DONE%개 · 이미 한글판 %SKIP%개
echo       원본은 "원본백업" 폴더에 있습니다.
echo.
echo  ★ RPCS3 시스템 언어를 한국어나 영어로 두세요. 일본어면 일본어가 나옵니다.
goto END

:DO
set "DEST=%~1"
set "NAME=%~2"
set "PN=%~3"
set "SRCMD5=%~4"
set "DSTMD5=%~5"
set "XP=patch\%PN%.xdelta"
if not exist "%DEST%\%NAME%" goto MISSING
call :HASH "%DEST%\%NAME%"
if /I "%H%"=="%DSTMD5%" set /a SKIP+=1
if /I "%H%"=="%DSTMD5%" exit /b 0
if /I not "%H%"=="%SRCMD5%" goto WRONG
copy /y "%DEST%\%NAME%" "%BK%\%PN%" >nul
"%XD%" -d -f -s "%DEST%\%NAME%" "%XP%" "%BK%\%PN%.new"
if errorlevel 1 goto XFAIL
call :HASH "%BK%\%PN%.new"
if /I not "%H%"=="%DSTMD5%" goto XFAIL
move /y "%BK%\%PN%.new" "%DEST%\%NAME%" >nul
set /a DONE+=1
echo      %NAME%
exit /b 0

:HASH
set "H="
for /f "skip=1 tokens=* delims=" %%A in ('certutil -hashfile "%~1" MD5') do if not defined H set "H=%%A"
set "H=%H: =%"
exit /b 0

:MISSING
echo  [!] %NAME% 이 대상 폴더에 없습니다. 판이 맞는지 확인하세요 - 이 묶음은 {tid} 용입니다.
goto FAIL
:WRONG
echo  [!] %NAME% 이 원본과 다릅니다. 다른 판이거나 이미 다른 패치가 들어가 있습니다.
echo      예전 한글 패치를 깔았다면 그 묶음의 되돌리기.bat 로 원본으로 돌린 뒤 다시 적용하세요.
echo      원본 MD5 %SRCMD5%
goto FAIL
:XFAIL
echo  [!] %NAME% 패치에 실패했습니다. 원본은 원본백업 폴더에 있습니다.
if exist "%BK%\%PN%.new" del "%BK%\%PN%.new"
goto FAIL
:NOXD
echo  [!] xdelta.exe 가 이 폴더에 없습니다. 묶음을 통째로 푸세요.
goto FAIL
:NODEST
echo  [!] 게임 폴더를 찾지 못했습니다. PS3_GAME 이 있는 폴더를 주세요.
goto FAIL
:FAIL
echo.
pause
exit /b 1
:END
echo.
pause
exit /b 0
"""
UNDO = r"""@echo off
setlocal
chcp 949 >nul
cd /d "%~dp0"
set "BK=%~dp0원본백업"
set "TARGET=%~1"
if not defined TARGET set /p "TARGET=  게임 폴더를 끌어다 놓거나 경로를 적고 Enter: "
set "TARGET=%TARGET:"=%"
if "%TARGET:~-1%"=="\" set "TARGET=%TARGET:~0,-1%"
set "DISK="
if exist "%TARGET%\{probe}" set "DISK=%TARGET%"
if exist "%TARGET%\USRDIR\{probe}" set "DISK=%TARGET%\USRDIR"
if exist "%TARGET%\PS3_GAME\USRDIR\{probe}" set "DISK=%TARGET%\PS3_GAME\USRDIR"
if not defined DISK goto NODEST
set "T2=%~2"
if not defined T2 set /p "T2=  RPCS3 폴더 - 업데이트가 없으면 그냥 Enter: "
set "UPD="
if not defined T2 goto UPDNO
set "T2=%T2:"=%"
if "%T2:~-1%"=="\" set "T2=%T2:~0,-1%"
if exist "%T2%\dev_hdd0\game\{tid}\USRDIR\patch.cpk" set "UPD=%T2%\dev_hdd0\game\{tid}\USRDIR"
if exist "%T2%\game\{tid}\USRDIR\patch.cpk" set "UPD=%T2%\game\{tid}\USRDIR"
if exist "%T2%\{tid}\USRDIR\patch.cpk" set "UPD=%T2%\{tid}\USRDIR"
if exist "%T2%\USRDIR\patch.cpk" set "UPD=%T2%\USRDIR"
if exist "%T2%\patch.cpk" set "UPD=%T2%"
:UPDNO
{calls}
echo.
echo  [OK] 원본으로 되돌렸습니다.
goto END
:NODEST
echo  [!] 게임 폴더를 찾지 못했습니다.
:END
echo.
pause
"""


def cp949(path, text):
    open(path, 'w', encoding='cp949', newline='\r\n').write(text)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    name = 'SoulCalibur5_PS3_KR_' + VER
    od = R('dist', name)
    if os.path.exists(od): shutil.rmtree(od)
    os.makedirs(os.path.join(od, 'patch'))
    shutil.copy(XDELTA, os.path.join(od, 'xdelta.exe'))
    rows = []; calls = []; undo = []
    for k, f in ITEMS:
        src, dst = orig_of(k, f), new_of(k, f); pn = ('upd_' if k in ('upd', 'dlc') else '') + f.replace('/', '_')
        win = f.replace('/', '\\')
        a, b = md5(src), md5(dst)
        assert a != b, ('바뀐 것 없음', f)
        xd = os.path.join(od, 'patch', pn + '.xdelta')
        subprocess.run([XDELTA, '-e', '-9', '-f', '-s', src, dst, xd], check=True)
        tmp = xd + '.chk'
        subprocess.run([XDELTA, '-d', '-f', '-s', src, xd, tmp], check=True)
        assert md5(tmp) == b, ('되짚기 실패', f); os.remove(tmp)
        tag = {'upd': '[업데이트] ', 'dlc': '[DLC] '}.get(k, '')
        rows.append('%s%s\n    %s -> %s' % (tag, win, a, b))
        var = 'UPD' if k == 'upd' else 'DISK'
        if k == 'dlc':
            calls.append('if defined UPD if exist "%%UPD%%\\%s" call :DO "%%UPD%%" "%s" "%s" %s %s\nif errorlevel 1 goto FAIL' % (win, win, pn, a, b))
            undo.append('if defined UPD if exist "%%BK%%\\%s" copy /y "%%BK%%\\%s" "%%UPD%%\\%s" >nul' % (pn, pn, win))
        elif k == 'upd':
            calls.append('if defined UPD call :DO "%%UPD%%" "%s" "%s" %s %s\nif errorlevel 1 goto FAIL' % (f, pn, a, b))
            undo.append('if defined UPD if exist "%%BK%%\\%s" copy /y "%%BK%%\\%s" "%%UPD%%\\%s" >nul' % (pn, pn, f))
        else:
            calls.append('call :DO "%%DISK%%" "%s" "%s" %s %s\nif errorlevel 1 goto FAIL' % (f, pn, a, b))
            undo.append('if exist "%%BK%%\\%s" copy /y "%%BK%%\\%s" "%%DISK%%\\%s" >nul' % (pn, pn, f))
        print('  %-10s %s -> %s  xdelta %d B' % (f, a, b, os.path.getsize(xd)))
    cp949(os.path.join(od, 'readme.txt'), README.format(ver=VER, tid=TID, table='\n'.join(rows)))
    cp949(os.path.join(od, '한글패치_적용.bat'), BAT.replace('{ver}', VER).replace('{tid}', TID).replace('{probe}', PROBE).replace('{calls}', '\n'.join(calls)))
    cp949(os.path.join(od, '되돌리기.bat'), UNDO.replace('{tid}', TID).replace('{probe}', PROBE).replace('{calls}', '\n'.join(undo)))
    zp = od + '.zip'
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, ds, fs in os.walk(od):
            for f in fs:
                p = os.path.join(root, f); z.write(p, os.path.join(name, os.path.relpath(p, od)))
    print('파일 %d개 · 되짚기 전부 일치 · %s' % (len(ITEMS), od))
    print('zip %s  %d B  md5 %s' % (zp, os.path.getsize(zp), md5(zp)))


if __name__ == '__main__':
    main()
