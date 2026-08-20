#!/usr/bin/env python3
"""Abre o Construtor no navegador. Na primeira vez, instala o necessário e
configura o provedor (Anthropic, Groq ou Ollama) sozinho — sem editar arquivo."""

import os
import subprocess
import sys
from pathlib import Path

PLACEHOLDER = "coloque-sua-chave-aqui"


def _pip(pkg):
    for extra in ([], ["--user", "--break-system-packages"]):
        try:
            if subprocess.run([sys.executable, "-m", "pip", "install", pkg, *extra],
                              capture_output=True, text=True).returncode == 0:
                return True
        except Exception:
            pass
    return False


def _ensure():
    try:
        import anthropic  # noqa
        return
    except ImportError:
        pass
    if os.environ.get("C_RETRY") == "1":
        print("Instale manualmente:  pip install --user --break-system-packages anthropic")
        input("Enter para sair…"); sys.exit(1)
    print("Instalando o necessário (só na 1a vez)…")
    if _pip("anthropic"):
        os.environ["C_RETRY"] = "1"
        try:
            os.execv(sys.executable, [sys.executable, *sys.argv])
        except OSError:
            pass
    print("Instale manualmente:  pip install --user --break-system-packages anthropic")
    input("Enter para sair…"); sys.exit(1)


def _has_config():
    from construtor import config
    config._load_dotenv()
    prov = os.environ.get("CONSTRUTOR_PROVIDER", "").lower()
    if prov in ("ollama", "lmstudio"):
        return True
    for v in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY",
              "CONSTRUTOR_API_KEY", "CODE_DOCTOR_API_KEY"):
        val = os.environ.get(v, "").strip()
        if val and val != PLACEHOLDER:
            return True
    return False


def _save_env(lines: list[str]) -> None:
    Path(".env").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for ln in lines:
        if "=" in ln:
            k, _, v = ln.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def _setup():
    print("=" * 60)
    print("  Bem-vindo ao Engenheiro do Código! 🏗️")
    print("  Vamos escolher de onde vem a inteligência artificial.")
    print("=" * 60)
    print()
    print("  1) Anthropic (Claude)  — melhor qualidade, custa centavos por projeto")
    print("  2) Groq                — grátis, roda na nuvem (não pesa no seu PC)")
    print("  3) Ollama              — grátis, roda no SEU PC (precisa estar instalado)")
    print()
    try:
        op = input("  Escolha 1, 2 ou 3 e aperte Enter: ").strip()
    except (EOFError, KeyboardInterrupt):
        return False

    if op == "3":  # Ollama — sem chave
        modelo = input("  Nome do modelo do Ollama [qwen2.5-coder:1.5b]: ").strip() \
            or "qwen2.5-coder:1.5b"
        _save_env(["CONSTRUTOR_PROVIDER=ollama", f"CONSTRUTOR_MODEL={modelo}"])
        print("\n  ✓ Configurado para Ollama (grátis, local). Deixe o Ollama aberto.")
        return True

    if op == "2":  # Groq
        print("\n  Pegue uma chave grátis em: https://console.groq.com  (API Keys)")
        chave = input("  Cole sua chave do Groq (começa com gsk_): ").strip()
        if not chave:
            print("  Nenhuma chave digitada."); return False
        _save_env(["CONSTRUTOR_PROVIDER=groq", f"GROQ_API_KEY={chave}",
                   "CONSTRUTOR_MODEL=openai/gpt-oss-120b"])
        print("\n  ✓ Configurado para Groq (grátis, na nuvem).")
        return True

    # padrão: Anthropic
    print("\n  Pegue sua chave em: https://platform.claude.com/settings/keys")
    chave = input("  Cole sua chave da Anthropic (começa com sk-ant-): ").strip()
    if not chave or chave == PLACEHOLDER:
        print("  Nenhuma chave digitada."); return False
    _save_env([f"ANTHROPIC_API_KEY={chave}"])
    print("\n  ✓ Configurado para Anthropic (Claude).")
    return True


def main():
    _ensure()
    if not _has_config():
        if not _setup():
            input("\nEnter para sair…"); return
    print("\nAbrindo o Engenheiro do Código no navegador… 🏗️")
    from construtor import web
    web.serve()


if __name__ == "__main__":
    main()
