@echo off
chcp 65001 >nul
title Criar atalho - Engenheiro do Codigo
cd /d "%~dp0"

set "ALVO=%~dp0Engenheiro-do-Codigo.bat"
set "ICONE=%SystemRoot%\System32\shell32.dll,13"

echo Criando atalho na Area de Trabalho...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$desk=[Environment]::GetFolderPath('Desktop');" ^
  "$lnk=Join-Path $desk 'Engenheiro do Codigo.lnk';" ^
  "$w=New-Object -ComObject WScript.Shell;" ^
  "$s=$w.CreateShortcut($lnk);" ^
  "$s.TargetPath='%ALVO%';" ^
  "$s.WorkingDirectory='%~dp0';" ^
  "$s.IconLocation='%ICONE%';" ^
  "$s.Save();" ^
  "if(Test-Path $lnk){Write-Host 'OK: atalho criado na Area de Trabalho.'}else{Write-Host 'Nao consegui criar o atalho.'}"

echo.
pause
exit /b
