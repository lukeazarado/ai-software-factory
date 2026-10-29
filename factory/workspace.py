"""Restrict agent file operations to a single project directory."""
from pathlib import Path
import re

ALLOWED_EXTENSIONS = {'.html', '.css', '.js', '.json', '.md', '.svg', '.txt'}
MAX_WRITE_CHARS = 120_000
MAX_READ_CHARS = 40_000


def slugify(value: str) -> str:
    slug = re.sub(r'[^a-z0-9-]+', '-', value.lower()).strip('-')
    if not slug or len(slug) > 60:
        raise ValueError('O nome do projeto deve gerar um slug de 1 a 60 caracteres.')
    return slug


class Workspace:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative: str) -> Path:
        if not relative or '\\' in relative or '\x00' in relative:
            raise ValueError('Caminho inválido.')
        p = Path(relative)
        if p.is_absolute():
            raise ValueError('Caminho absoluto não permitido.')
        candidate = (self.root / p).resolve()
        if not candidate.is_relative_to(self.root) or candidate == self.root:
            raise ValueError('Acesso fora do diretório do projeto não permitido.')
        if candidate.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError('Extensão de arquivo não permitida.')
        return candidate

    def write(self, relative: str, content: str) -> str:
        if len(content) > MAX_WRITE_CHARS:
            raise ValueError('Arquivo excede o limite de tamanho.')
        target = self.resolve(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
        return f'Arquivo salvo: {target.relative_to(self.root)} ({len(content)} caracteres)'

    def read(self, relative: str) -> str:
        target = self.resolve(relative)
        if not target.is_file():
            return f'Arquivo inexistente: {relative}'
        return target.read_text(encoding='utf-8')[:MAX_READ_CHARS]

    def list_files(self) -> str:
        files = [str(p.relative_to(self.root)) for p in self.root.rglob('*') if p.is_file()]
        return '\n'.join(sorted(files)[:200]) or '(nenhum arquivo)'

    def validate_site(self) -> str:
        page = self.root / 'index.html'
        if not page.is_file():
            return 'FALHOU: index.html não existe na raiz do projeto.'
        content = page.read_text(encoding='utf-8').lower()
        issues = []
        if '<html' not in content or '</html>' not in content:
            issues.append('estrutura HTML incompleta')
        if '<title' not in content:
            issues.append('tag title ausente')
        if 'viewport' not in content:
            issues.append('meta viewport ausente')
        return 'FALHOU: ' + '; '.join(issues) if issues else 'PASSOU: verificações estáticas básicas (não substituem testes funcionais e de segurança).'
