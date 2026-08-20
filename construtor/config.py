"""Configuração: chave/modelo/provedor (via ambiente ou .env) e limites."""

import os
from pathlib import Path

DEFAULT_MODEL = "claude-sonnet-5"

MAX_FILES = 12          # nº máximo de arquivos gerados por projeto (controla custo)
MAX_FILE_TOKENS = 4000  # tokens máximos por arquivo gerado

# Tipos/linguagens que o MVP cria.
LANGUAGES = {
    "python": "Python",
    "java": "Java",
    "php": "PHP",
    "web": "Web (HTML, CSS e JavaScript)",
}


def _load_dotenv() -> None:
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_model(override: str | None = None) -> str:
    if override:
        return override
    return os.environ.get("CONSTRUTOR_MODEL",
                          os.environ.get("CODE_DOCTOR_MODEL", DEFAULT_MODEL))


# ---- Central de configuração (usada pela interface web) ----

# Provedores oferecidos na tela, com a variável da chave e se exige chave.
PROVEDORES_UI = {
    "anthropic": {"nome": "Anthropic (Claude)", "chave": "ANTHROPIC_API_KEY",
                  "precisa_chave": True, "modelo_padrao": "claude-sonnet-5"},
    "groq":      {"nome": "Groq (grátis, nuvem)", "chave": "GROQ_API_KEY",
                  "precisa_chave": True, "modelo_padrao": "openai/gpt-oss-120b"},
    "openai":    {"nome": "OpenAI", "chave": "OPENAI_API_KEY",
                  "precisa_chave": True, "modelo_padrao": "gpt-4o-mini"},
    "ollama":    {"nome": "Ollama (grátis, no seu PC)", "chave": None,
                  "precisa_chave": False, "modelo_padrao": "qwen2.5-coder:1.5b"},
}


def ollama_rodando() -> bool:
    """Detecta se o Ollama está ativo no PC (porta local padrão)."""
    import urllib.request
    import urllib.error
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1):
            return True
    except Exception:
        return False


def mascarar_chave(valor: str) -> str:
    """Mostra só o começo e o fim da chave (ex.: 'sk-a…wxyz')."""
    v = (valor or "").strip()
    if not v:
        return ""
    if len(v) <= 8:
        return v[0] + "…"
    return f"{v[:4]}…{v[-4:]}"


def estado_atual() -> dict:
    """Como está configurado agora (sem revelar a chave inteira)."""
    _load_dotenv()
    prov = os.environ.get("CONSTRUTOR_PROVIDER", "anthropic").lower()
    info = PROVEDORES_UI.get(prov, PROVEDORES_UI["anthropic"])
    chave = ""
    if info["chave"]:
        chave = os.environ.get(info["chave"], "").strip()
    return {
        "provider": prov,
        "model": os.environ.get("CONSTRUTOR_MODEL", info["modelo_padrao"]),
        "tem_chave": bool(chave),
        "chave_mascarada": mascarar_chave(chave),
    }


def salvar_config(provider: str, model: str, chave: str | None) -> tuple[bool, str]:
    """Grava a configuração no .env (local). Retorna (ok, mensagem)."""
    provider = (provider or "").lower().strip()
    if provider not in PROVEDORES_UI:
        return False, "provedor desconhecido"
    info = PROVEDORES_UI[provider]
    model = (model or info["modelo_padrao"]).strip()

    # lê o .env atual para preservar outras linhas
    env_path = Path.cwd() / ".env"
    linhas: dict[str, str] = {}
    if env_path.exists():
        for ln in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in ln and not ln.strip().startswith("#"):
                k, _, v = ln.partition("=")
                linhas[k.strip()] = v.strip()

    linhas["CONSTRUTOR_PROVIDER"] = provider
    linhas["CONSTRUTOR_MODEL"] = model

    if info["precisa_chave"]:
        chave = (chave or "").strip()
        # se veio vazio, mantém a chave que já existia (pessoa só trocou o modelo)
        if chave:
            linhas[info["chave"]] = chave
        elif info["chave"] not in linhas:
            return False, f"o provedor {info['nome']} precisa de uma chave"

    conteudo = "\n".join(f"{k}={v}" for k, v in linhas.items()) + "\n"
    env_path.write_text(conteudo, encoding="utf-8")

    # aplica no processo atual imediatamente
    os.environ["CONSTRUTOR_PROVIDER"] = provider
    os.environ["CONSTRUTOR_MODEL"] = model
    if info["precisa_chave"] and chave:
        os.environ[info["chave"]] = chave
    return True, "configuração salva"
