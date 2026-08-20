"""Interface de linha de comando do Construtor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, config, generator, providers

_USE_COLOR = sys.stdout.isatty()


def _c(t: str, code: str) -> str:
    return f"\033[{code}m{t}\033[0m" if _USE_COLOR else t


def _read_description(arg: str | None) -> str:
    if arg:
        return arg
    print("Descreva o projeto (o que ele deve fazer). Linha vazia para terminar:\n")
    linhas = []
    try:
        while True:
            linha = input()
            if not linha.strip():
                break
            linhas.append(linha)
    except (EOFError, KeyboardInterrupt):
        pass
    return "\n".join(linhas).strip()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="construtor",
        description="Cria um projeto do zero a partir de uma descrição em texto.")
    p.add_argument("descricao", nargs="?",
                   help="o que o projeto deve fazer (se omitir, pergunta na tela)")
    p.add_argument("--lang", default="python",
                   choices=list(config.LANGUAGES.keys()),
                   help="linguagem/tipo do projeto (padrão: python)")
    p.add_argument("--out", default=None,
                   help="pasta onde salvar (padrão: ./<nome-do-projeto>)")
    p.add_argument("--provider", default=None, help="provedor de IA (ex.: ollama)")
    p.add_argument("--model", default=None, help="modelo a usar")
    p.add_argument("--version", action="version", version=f"construtor {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config._load_dotenv()

    descricao = _read_description(args.descricao)
    if not descricao:
        print("[erro] nenhuma descrição fornecida.", file=sys.stderr)
        return 2

    try:
        provider = providers.get_provider(args.provider, config.get_model(args.model))
    except providers.ProviderError as exc:
        print(f"\n[erro] {exc}\n", file=sys.stderr)
        return 2

    print(_c(f"\nConstrutor — gerando projeto em {config.LANGUAGES[args.lang]} "
             f"({provider.name}/{provider.model})\n", "1"))

    def progress(i, total, path):
        print(_c(f"  [{i}/{total}] gerando {path}…", "90"))

    result = generator.build_project(descricao, args.lang, provider,
                                     on_progress=progress)
    if not result.ok:
        print(f"\n[erro] {result.error}", file=sys.stderr)
        return 1

    out_dir = Path(args.out) if args.out else Path(result.plan.project_name)
    written = generator.write_to_disk(result, out_dir)

    print(_c(f"\n✓ Projeto '{result.plan.project_name}' criado em: {out_dir}/", "32"))
    print(_c(f"  {len(written)} arquivo(s):", "1"))
    for p in written:
        print(f"    {p.relative_to(out_dir)}")
    if result.plan.run:
        print(_c("\nComo rodar:", "1"))
        print(f"  {result.plan.run}")
    u = result.usage
    print(_c(f"\nTokens: {u.input_tokens} entrada / {u.output_tokens} saída", "90"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
