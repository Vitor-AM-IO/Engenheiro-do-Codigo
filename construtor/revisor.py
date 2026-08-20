"""Revisor de código embutido — passa uma checagem nos arquivos gerados.

É uma versão enxuta do "Dr. Código" trazida para dentro do Construtor: revisa
cada arquivo criado e aponta problemas (foco em erros que quebram e segurança).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .providers import Usage, ProviderError

_EXT_LANG = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".java": "Java",
    ".php": "PHP", ".rb": "Ruby", ".go": "Go", ".rs": "Rust", ".c": "C",
    ".cpp": "C++", ".cs": "C#", ".html": "HTML", ".css": "CSS", ".sql": "SQL",
    ".sh": "Shell", ".kt": "Kotlin", ".swift": "Swift",
}

_SYSTEM = (
    "Você é um revisor de código sênior. Analise o arquivo e aponte problemas "
    "REAIS, priorizando: erros que quebram a execução, bugs de lógica, falhas de "
    "segurança e inconsistências (ex.: chamar função/nome que não existe). Ignore "
    "puro estilo. Responda SOMENTE com JSON válido, sem cercas de código, no "
    "formato: {\"summary\":\"uma frase\",\"issues\":[{\"line\":N,"
    "\"severity\":\"critical|high|medium|low\",\"title\":\"...\","
    "\"description\":\"...\",\"suggestion\":\"...\"}]}. Se estiver tudo certo, "
    "retorne issues vazio."
)


@dataclass
class Issue:
    line: int
    severity: str
    title: str
    description: str
    suggestion: str = ""


@dataclass
class Review:
    path: str
    summary: str = ""
    issues: list[Issue] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def _lang(path: str) -> str:
    return _EXT_LANG.get(Path(path).suffix.lower(), "código")


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1] if "\n" in t else t
        if t.endswith("```"):
            t = t[:-3]
    return t.strip()


def revisar_arquivo(path: str, code: str, provider,
                    max_tokens: int = 1500) -> Review:
    user = (f"Arquivo: {path}\nLinguagem: {_lang(path)}\n\n"
            f"Código:\n{code}")
    try:
        raw, usage = provider.complete(_SYSTEM, user, max_tokens)
    except ProviderError as exc:
        return Review(path=path, error=str(exc))
    try:
        data = json.loads(_strip_fences(raw))
    except json.JSONDecodeError:
        return Review(path=path, usage=usage, summary="(revisão sem formato válido)")
    issues = []
    for i in data.get("issues", []):
        try:
            issues.append(Issue(
                line=int(i.get("line", 0) or 0),
                severity=str(i.get("severity", "medium")).lower(),
                title=str(i.get("title", "")).strip(),
                description=str(i.get("description", "")).strip(),
                suggestion=str(i.get("suggestion", "")).strip(),
            ))
        except (ValueError, TypeError):
            continue
    return Review(path=path, summary=str(data.get("summary", "")).strip(),
                  issues=issues, usage=usage)


def revisar_arquivos(files: list[tuple[str, str]], provider,
                     on_progress=None) -> tuple[list[Review], Usage]:
    """Revisa vários arquivos. Retorna as revisões e o total de tokens."""
    total = Usage()
    reviews = []
    for idx, (path, code) in enumerate(files, 1):
        if on_progress:
            on_progress(idx, len(files), path)
        r = revisar_arquivo(path, code, provider)
        total.add(r.usage)
        reviews.append(r)
    return reviews, total
