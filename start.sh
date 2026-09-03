#!/usr/bin/env bash
# Lançador do Engenheiro do Código para Linux e Mac.
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
    exec python3 start.py
fi
echo "O Python 3 nao esta instalado (o programa precisa dele)."
if command -v apt >/dev/null 2>&1; then
    echo "Instale com:  sudo apt update && sudo apt install -y python3 python3-venv"
elif command -v brew >/dev/null 2>&1; then
    echo "Instale com:  brew install python"
else
    echo "Instale o Python 3 pelo gerenciador do seu sistema."
fi
read -r -p "Pressione Enter para sair..."
