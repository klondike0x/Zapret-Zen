@echo off
chcp 65001 > nul
:: 65001 - UTF-8

cd /d "%~dp0"
call service.bat status_zapret
call service.bat check_updates
call service.bat load_game_filter
echo:

set "BIN=%~dp0bin\"
set "LISTS=%~dp0lists\"
cd /d %BIN%


start "zapret: %~n0" /min "%BIN%winws.exe" ^
  --wf-l3=ipv4,ipv6 ^
  --wf-tcp=80,443,25565 ^
  --wf-udp=443,50000-65535,25565 ^
  --filter-udp=443 ^
    --hostlist="%~dp0lists\list-general.txt" ^
    --dpi-desync=fake,tamper ^
    --dpi-desync-repeats=6 ^
    --dpi-desync-fake-quic="%BIN_PATH%quic_initial_www_google_com.bin" ^
    --new ^
  --filter-udp=50000-65535 ^
    --dpi-desync=fake ^
    --dpi-desync-any-protocol ^
    --dpi-desync-fake-stun="%BIN_PATH%stun.bin" ^
    --new ^
  --filter-tcp=80,443,25565 ^
    --hostlist="%~dp0lists\list-general.txt" ^
    --dpi-desync=fake,split2 ^
    --dpi-desync-autottl=2 ^
    --dpi-desync-repeats=6 ^
    --dpi-desync-fooling=md5sig ^
    --dpi-desync-fake-tls="%BIN_PATH%tls_clienthello_www_google_com.bin"