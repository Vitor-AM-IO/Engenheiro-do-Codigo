@echo off
chcp 65001 >nul
title Engenheiro do Codigo
cd /d "%~dp0"

REM --- Procura o Python instalado ---
set "PYCMD="
where python >nul 2>nul && set "PYCMD=python"
if not defined PYCMD ( where py >nul 2>nul && set "PYCMD=py" )

if not defined PYCMD goto SEM_PYTHON

REM --- Python encontrado: abre o programa ---
"%PYCMD%" start.py
pause
exit /b

:SEM_PYTHON
echo ============================================================
echo   O Python nao esta instalado (o programa precisa dele).
echo ============================================================
echo.
where winget >nul 2>nul
if %errorlevel%==0 (
  echo Vou tentar instalar o Python automaticamente. Aguarde...
  echo.
  winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
  echo.
  echo ------------------------------------------------------------
  echo   Pronto! Agora FECHE esta janela e abra novamente
  echo   o Engenheiro-do-Codigo.bat ^(o Windows precisa reconhecer o Python^).
  echo ------------------------------------------------------------
) else (
  echo Nao encontrei o instalador automatico ^(winget^).
  echo.
  echo Baixe o Python em:  https://www.python.org/downloads/
  echo   IMPORTANTE: marque a caixinha "Add python.exe to PATH".
  start "" "https://www.python.org/downloads/"
)
echo.
pause
exit /b
