"""Camada de provedores: permite usar Anthropic OU qualquer API compatível
com OpenAI (OpenAI, OpenRouter, Groq, Together, DeepSeek, Mistral, Ollama/LM
Studio locais...). Assim, quem não quer usar a Anthropic pode trocar só por
variáveis de ambiente.

O back-end "openai-compatível" usa apenas a biblioteca padrão (urllib), sem
dependências novas.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0

    def add(self, other: "Usage") -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_read_tokens += other.cache_read_tokens


class ProviderError(Exception):
    """Erro ao falar com o provedor (rede, autenticação, resposta inválida)."""

def _segundos_para_esperar(exc, detail: str, padrao: float = 5.0) -> float:
    """Descobre quantos segundos esperar após um erro 429 (limite de uso)."""
    try:
        ra = exc.headers.get("Retry-After") if exc.headers else None
        if ra:
            return min(float(ra) + 1, 60)
    except (ValueError, AttributeError):
        pass
    m = re.search(r"in ([0-9.]+)s", detail or "")
    if m:
        try:
            return min(float(m.group(1)) + 1, 60)
        except ValueError:
            pass
    return padrao





# Presets de provedores compatíveis com OpenAI: (base_url, variável da chave).
# CONSTRUTOR_BASE_URL sempre pode sobrescrever a base.
_OPENAI_PRESETS = {
    "openai":     ("https://api.openai.com/v1", "OPENAI_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "groq":       ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "together":   ("https://api.together.xyz/v1", "TOGETHER_API_KEY"),
    "deepseek":   ("https://api.deepseek.com/v1", "DEEPSEEK_API_KEY"),
    "mistral":    ("https://api.mistral.ai/v1", "MISTRAL_API_KEY"),
    "ollama":     ("http://localhost:11434/v1", None),      # local, sem chave
    "lmstudio":   ("http://localhost:1234/v1", None),       # local, sem chave
    "custom":     (None, "CONSTRUTOR_API_KEY"),            # tudo via env
}

KNOWN_PROVIDERS = ["anthropic", *_OPENAI_PRESETS.keys()]


class AnthropicProvider:
    """Back-end oficial da Anthropic (com prompt caching)."""

    def __init__(self, api_key: str, model: str):
        import anthropic  # importado só quando usado
        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.name = "anthropic"

    def complete(self, system: str, user: str, max_tokens: int,
                 cache_system: bool = True) -> tuple[str, Usage]:
        sys_block = [{"type": "text", "text": system}]
        if cache_system:
            sys_block[0]["cache_control"] = {"type": "ephemeral"}
        try:
            msg = self.client.messages.create(
                model=self.model, max_tokens=max_tokens,
                system=sys_block,
                messages=[{"role": "user", "content": user}],
            )
        except self._anthropic.APIError as exc:
            raise ProviderError(str(exc)) from exc

        text = "".join(b.text for b in msg.content
                       if getattr(b, "type", "") == "text")
        u = getattr(msg, "usage", None)
        usage = Usage(
            input_tokens=getattr(u, "input_tokens", 0) or 0,
            output_tokens=getattr(u, "output_tokens", 0) or 0,
            cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
        )
        return text, usage


class OpenAICompatProvider:
    """Qualquer API no formato OpenAI /chat/completions (urllib, sem deps)."""

    def __init__(self, base_url: str, api_key: str, model: str, name: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.name = name

    def complete(self, system: str, user: str, max_tokens: int,
                 cache_system: bool = True) -> tuple[str, Usage]:
        payload = json.dumps({
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }).encode("utf-8")

        # O "User-Agent" evita que provedores atrás do Cloudflare (ex.: Groq)
        # bloqueiem a requisição como se fosse um robô (erro 403 code 1010).
        headers = {"Content-Type": "application/json",
                   "User-Agent": "EngenheiroDoCodigo/1.0 (+https://github.com/Vitor-AM-IO)"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=payload, headers=headers,
        )
        # Tenta algumas vezes: se bater no limite de uso (429), espera e repete.
        max_tentativas = 4
        for tentativa in range(1, max_tentativas + 1):
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "ignore")[:300]
                if exc.code == 429 and tentativa < max_tentativas:
                    time.sleep(_segundos_para_esperar(exc, detail))
                    continue
                raise ProviderError(f"HTTP {exc.code}: {detail}") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                raise ProviderError(f"falha de conexão: {exc}") from exc
            except json.JSONDecodeError as exc:
                raise ProviderError("resposta não-JSON do provedor") from exc

        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"formato de resposta inesperado: {data}") from exc

        u = data.get("usage", {}) or {}
        cached = 0
        details = u.get("prompt_tokens_details") or {}
        if isinstance(details, dict):
            cached = details.get("cached_tokens", 0) or 0
        usage = Usage(
            input_tokens=u.get("prompt_tokens", 0) or 0,
            output_tokens=u.get("completion_tokens", 0) or 0,
            cache_read_tokens=cached,
        )
        return text, usage



def _env(nome: str, padrao: str = "") -> str:
    """Lê CONSTRUTOR_<nome> primeiro; cai para CODE_DOCTOR_<nome> por compatibilidade."""
    v = os.environ.get(f"CONSTRUTOR_{nome}", "").strip()
    if v:
        return v
    return os.environ.get(f"CODE_DOCTOR_{nome}", padrao).strip()


def get_provider(name: str | None = None, model: str | None = None):
    """Monta o provedor a partir das variáveis de ambiente / flags.

    Seleção: --provider  >  CONSTRUTOR_PROVIDER  >  'anthropic'.
    """
    name = (name or _env("PROVIDER", "anthropic")).lower().strip()
    model = model or _env("MODEL", "")

    if name == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not key:
            raise ProviderError(
                "provedor 'anthropic' selecionado, mas ANTHROPIC_API_KEY não está "
                "definida. Defina a chave ou escolha outro provedor com "
                "CONSTRUTOR_PROVIDER (ex.: openai, openrouter, groq, ollama)."
            )
        return AnthropicProvider(api_key=key, model=model or "claude-sonnet-5")

    if name not in _OPENAI_PRESETS:
        raise ProviderError(
            f"provedor '{name}' desconhecido. Opções: {', '.join(KNOWN_PROVIDERS)}. "
            "Para um endpoint próprio use CONSTRUTOR_PROVIDER=custom e "
            "CONSTRUTOR_BASE_URL=..."
        )

    preset_base, key_var = _OPENAI_PRESETS[name]
    base_url = _env("BASE_URL") or preset_base
    if not base_url:
        raise ProviderError(
            f"provedor '{name}' precisa de CONSTRUTOR_BASE_URL definido."
        )

    # chave: variável específica do preset, ou a genérica CONSTRUTOR_API_KEY.
    key = ""
    if key_var:
        key = os.environ.get(key_var, "").strip()
    key = key or _env("API_KEY")

    # locais (ollama/lmstudio) não exigem chave.
    if not key and name not in ("ollama", "lmstudio"):
        raise ProviderError(
            f"provedor '{name}' precisa de uma chave de API. Defina "
            f"{key_var or 'CONSTRUTOR_API_KEY'}."
        )

    if not model:
        raise ProviderError(
            f"defina o modelo com CONSTRUTOR_MODEL (ou --model) para o provedor "
            f"'{name}'. Ex.: gpt-4o-mini, llama3.1, deepseek-chat, etc."
        )

    return OpenAICompatProvider(base_url=base_url, api_key=key or "local",
                                model=model, name=name)
