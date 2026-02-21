@echo off
:: Get raw encoded path from argument
set raw=%~1

:: Remove protocol
set raw=%raw:openfolder://=%

:: Decode URL using PowerShell
for /f "delims=" %%i in ('powershell -NoProfile -Command "[System.Uri]::UnescapeDataString(\"%raw%\")"') do set decoded=%%i

:: Replace forward slashes with backslashes
set decoded=%decoded:/=\%

echo Opening: "%decoded%"
start "" "%decoded%"
