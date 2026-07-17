"""
conftest.py — preparação de ambiente para a suíte de testes.

Duas coisas precisam acontecer ANTES de qualquer teste importar módulos do
projeto:

1. A raiz do projeto precisa estar no sys.path (os testes ficam em tests/,
   um nível abaixo).
2. ADMIN_PASSWORD_HASH precisa estar definida, porque config.py faz
   `sys.exit(1)` na hora do import se essa variável não existir — então só
   de importar routes/crud.py (ou qualquer módulo que dependa de config.py)
   sem isso configurado, o processo inteiro do pytest morre. Usamos aqui um
   valor fake só para permitir a importação; nenhum teste precisa que esse
   hash corresponda a uma senha real.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.environ.setdefault(
    "ADMIN_PASSWORD_HASH",
    "$2b$12$test.dummy.hash.for.unit.tests.only.do.not.use.in.prod",
)
