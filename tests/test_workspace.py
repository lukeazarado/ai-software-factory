import pytest
from factory.workspace import Workspace, slugify


def test_slugify():
    assert slugify('Meu Portal Financeiro') == 'meu-portal-financeiro'


def test_empty_slug_rejected():
    with pytest.raises(ValueError):
        slugify('!!!')


def test_write_and_read(tmp_path):
    w = Workspace(tmp_path / 'project')
    assert 'salvo' in w.write('assets/app.js', 'console.log(1);')
    assert w.read('assets/app.js') == 'console.log(1);'
    assert 'assets/app.js' in w.list_files()


@pytest.mark.parametrize('path', ['../secret.txt', '/tmp/secret.txt', 'a/../../secret.txt', 'private.env', 'C:\\private\\file.js'])
def test_path_rejected(tmp_path, path):
    w = Workspace(tmp_path / 'project')
    with pytest.raises(ValueError):
        w.write(path, 'x')


def test_symlink_escape_rejected(tmp_path):
    w = Workspace(tmp_path / 'project')
    outside = tmp_path / 'outside'
    outside.mkdir()
    (w.root / 'escape').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        w.write('escape/file.js', 'x')


def test_validation(tmp_path):
    w = Workspace(tmp_path / 'project')
    assert w.validate_site().startswith('FALHOU')
    w.write('index.html', '<!doctype html><html><head><title>X</title><meta name="viewport" content="width=device-width"></head><body></body></html>')
    assert w.validate_site().startswith('PASSOU')
