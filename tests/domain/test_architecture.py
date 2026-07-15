"""
Guarda-costas do hexagonal (SPEC RN-01): o domínio é puro.

Varre todos os módulos de `agente.domain` e falha se algum importar de camadas
externas (adapters/api/application) ou de bibliotecas de I/O. Se este teste
quebrar, a modelagem quebrou — não relaxe o teste, conserte o import.
"""

import ast
from pathlib import Path

DOMAIN_DIR = Path(__file__).resolve().parents[2] / "src" / "agente" / "domain"

# Camadas e libs que o domínio NUNCA pode conhecer.
FORBIDDEN_PREFIXES = (
    "agente.adapters",
    "agente.application",
    "agente.api",
    "httpx",
    "requests",
    "fastapi",
    "sqlalchemy",
    "asyncpg",
    "psycopg",
    "anthropic",
    "openai",
)


def _imported_modules(source: str) -> set[str]:
    tree = ast.parse(source)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _domain_files() -> list[Path]:
    return sorted(DOMAIN_DIR.glob("*.py"))


def test_domain_has_python_files() -> None:
    # Sanidade: garante que estamos de fato varrendo algo.
    assert _domain_files(), f"nenhum módulo encontrado em {DOMAIN_DIR}"


def test_domain_imports_nothing_forbidden() -> None:
    violations: list[str] = []
    for path in _domain_files():
        for module in _imported_modules(path.read_text()):
            if module.startswith(FORBIDDEN_PREFIXES):
                violations.append(f"{path.name} importa proibido: {module}")
    assert not violations, "Domínio impuro:\n" + "\n".join(violations)
