"""Núcleo do agente: planeja a estrutura do projeto e gera cada arquivo.

Fluxo (agêntico, em 2 passos):
  1. plan()   -> pede ao modelo a lista de arquivos (o "esqueleto" do projeto).
  2. generate_file() -> gera o conteúdo completo de cada arquivo, coerente com
     a descrição e com os outros arquivos do plano.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import config
from .providers import Usage, ProviderError

_PLAN_SYSTEM = (
    "Você é um arquiteto de software. Dada a descrição de um projeto e a "
    "linguagem/tipo, planeje a estrutura MÍNIMA de arquivos para atender ao "
    "pedido — nada de arquivos desnecessários. Prefira algo simples, funcional e "
    "fácil de rodar. Responda SOMENTE com JSON válido, sem cercas de código, no "
    "formato: {\"project_name\":\"nome-curto-sem-espacos\","
    "\"files\":[{\"path\":\"caminho/relativo.ext\",\"purpose\":\"o que este "
    "arquivo faz\"}],\"run\":\"como rodar o projeto, em 1-2 frases\"}."
)

_GEN_SYSTEM = (
    "Você é um programador sênior. Gere o conteúdo COMPLETO e funcional do arquivo "
    "pedido, coerente com a descrição do projeto e com os outros arquivos listados. "
    "Escreva código limpo e comentado quando ajudar. Responda SOMENTE com o "
    "conteúdo do arquivo — sem explicações, sem cercas de código (```), sem texto "
    "antes ou depois."
)


@dataclass
class PlannedFile:
    path: str
    purpose: str


@dataclass
class Plan:
    project_name: str
    files: list[PlannedFile] = field(default_factory=list)
    run: str = ""
    usage: Usage = field(default_factory=Usage)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class BuildResult:
    plan: Plan
    files: list[tuple[str, str]] = field(default_factory=list)  # (path, conteúdo)
    usage: Usage = field(default_factory=Usage)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def _strip_json_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1] if "\n" in t else t
        if t.endswith("```"):
            t = t[:-3]
    return t.strip()


def _strip_code_fences(text: str) -> str:
    """Remove cercas ```linguagem ... ``` caso o modelo as inclua."""
    t = text.strip()
    if t.startswith("```"):
        nl = t.find("\n")
        if nl != -1:
            t = t[nl + 1:]
        t = t.rstrip()
        if t.endswith("```"):
            t = t[:-3]
    return t.rstrip() + "\n"


def _safe_rel(path: str) -> str | None:
    """Sanitiza um caminho relativo (evita traversal e caminhos absolutos)."""
    path = path.strip().replace("\\", "/").lstrip("/")
    if not path or ".." in path.split("/") or re.match(r"^[a-zA-Z]:", path):
        return None
    return path


def plan(description: str, language: str, provider,
         max_files: int = config.MAX_FILES, max_tokens: int = 1600) -> Plan:
    lang = config.LANGUAGES.get(language, language)
    user = (f"Linguagem/tipo do projeto: {lang}\n\n"
            f"Descrição do que o projeto deve fazer:\n{description}\n\n"
            f"Use no máximo {max_files} arquivos.")
    try:
        raw, usage = provider.complete(_PLAN_SYSTEM, user, max_tokens)
    except ProviderError as exc:
        return Plan("", error=f"erro no provedor: {exc}")
    try:
        data = json.loads(_strip_json_fences(raw))
    except json.JSONDecodeError:
        return Plan("", usage=usage, error="o plano não veio em JSON válido")

    files = []
    for f in data.get("files", []):
        rel = _safe_rel(str(f.get("path", "")))
        if rel:
            files.append(PlannedFile(rel, str(f.get("purpose", "")).strip()))
    files = files[:max_files]
    if not files:
        return Plan("", usage=usage, error="o plano não listou arquivos válidos")

    return Plan(project_name=str(data.get("project_name", "projeto")).strip() or "projeto",
                files=files, run=str(data.get("run", "")).strip(), usage=usage)


def generate_file(description: str, language: str, project_plan: Plan,
                  target: PlannedFile, provider,
                  max_tokens: int = config.MAX_FILE_TOKENS) -> tuple[str, Usage, str | None]:
    lang = config.LANGUAGES.get(language, language)
    manifest = "\n".join(f"- {f.path}: {f.purpose}" for f in project_plan.files)
    user = (f"Projeto: {project_plan.project_name}\n"
            f"Linguagem/tipo: {lang}\n\n"
            f"Descrição do projeto:\n{description}\n\n"
            f"Arquivos que compõem o projeto:\n{manifest}\n\n"
            f"Gere agora o conteúdo COMPLETO do arquivo:\n"
            f"{target.path}  ({target.purpose})")
    try:
        raw, usage = provider.complete(_GEN_SYSTEM, user, max_tokens)
    except ProviderError as exc:
        return "", Usage(), f"erro no provedor: {exc}"
    return _strip_code_fences(raw), usage, None


def build_project(description: str, language: str, provider,
                  on_progress=None) -> BuildResult:
    """Planeja e gera todos os arquivos. `on_progress(i, total, path)` é opcional."""
    p = plan(description, language, provider)
    total = Usage()
    total.add(p.usage)
    if not p.ok:
        return BuildResult(plan=p, usage=total, error=p.error)

    files: list[tuple[str, str]] = []
    for idx, pf in enumerate(p.files, 1):
        if on_progress:
            on_progress(idx, len(p.files), pf.path)
        content, usage, err = generate_file(description, language, p, pf, provider)
        total.add(usage)
        if err:
            content = f"// (não foi possível gerar este arquivo: {err})\n"
        files.append((pf.path, content))

    return BuildResult(plan=p, files=files, usage=total)


def write_to_disk(result: BuildResult, out_dir: Path) -> list[Path]:
    """Grava os arquivos gerados numa pasta, criando subpastas com segurança."""
    written = []
    for rel, content in result.files:
        safe = _safe_rel(rel)
        if not safe:
            continue
        dest = out_dir / safe
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        written.append(dest)
    return written
