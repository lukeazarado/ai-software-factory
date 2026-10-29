from pathlib import Path


def test_template_has_basic_files():
    root = Path(__file__).resolve().parents[1] / 'template-web'
    for name in ('index.html', 'styles.css', 'app.js'):
        assert (root / name).is_file()
    html = (root / 'index.html').read_text(encoding='utf-8')
    assert '<html' in html and 'viewport' in html and '<title' in html
