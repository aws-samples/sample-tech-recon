"""
Tests for the download endpoints and default bind address of web_app.py (P547412588).

Run from the tech-recon directory:
    uv run --with pytest pytest tests -q
"""
import io
import runpy
import sys
import types
import zipfile
from pathlib import Path

import dotenv
import flask_socketio
import pytest

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

# web_app imports the agent graph (strands, Bedrock) at load time. The endpoints under
# test do not use it, so stub those modules to keep the tests offline and fast.
_main_stub = types.ModuleType('main')


async def _no_graph_execution(payload):
    return
    yield  # pragma: no cover


_main_stub.graph_streaming_execution = _no_graph_execution
_strands_stub = types.ModuleType('src.utils.strands_sdk_utils')
_strands_stub.strands_utils = None
sys.modules.setdefault('main', _main_stub)
sys.modules.setdefault('src.utils.strands_sdk_utils', _strands_stub)

import web_app  # noqa: E402

SECRET = 'TAVILY_API_KEY=should-never-be-served'


@pytest.fixture
def project(tmp_path, monkeypatch):
    """Build <tmp>/.env and <tmp>/artifacts/{other.txt, part1/..., part2/...}."""
    (tmp_path / '.env').write_text(SECRET + '\n')
    artifacts = tmp_path / 'artifacts'
    (artifacts / 'part1' / 'sub').mkdir(parents=True)
    (artifacts / 'part2').mkdir()
    (artifacts / 'part1' / 'report.md').write_text('# report\n')
    (artifacts / 'part1' / 'sub' / 'nested.md').write_text('nested\n')
    (artifacts / 'part2' / 'paper.md').write_text('# paper\n')
    (artifacts / 'other.txt').write_text('not downloadable\n')

    monkeypatch.chdir(tmp_path)  # /api/files still lists ./artifacts relative to CWD
    monkeypatch.setattr(web_app, 'ARTIFACTS_DIR', artifacts.resolve())
    return tmp_path


@pytest.fixture
def client(project):
    return web_app.app.test_client()


def _add_env_symlink(project):
    link = project / 'artifacts' / 'part1' / 'env_link'
    link.symlink_to(project / '.env')
    return link


# /api/download: allowed files

def test_download_part1_file(client):
    resp = client.get('/api/download/part1/report.md')
    assert resp.status_code == 200
    assert resp.data == b'# report\n'
    assert 'attachment' in resp.headers['Content-Disposition']
    assert 'report.md' in resp.headers['Content-Disposition']


def test_download_nested_and_part2_files(client):
    assert client.get('/api/download/part1/sub/nested.md').status_code == 200
    assert client.get('/api/download/part2/paper.md').status_code == 200


# /api/download: blocked paths

@pytest.mark.parametrize('path', [
    '../.env',
    'part1/../../.env',
    'part2/../../.env',
    'other.txt',
    'part1/../other.txt',
])
def test_download_traversal_is_forbidden(client, path):
    resp = client.get('/api/download/' + path)
    assert resp.status_code == 403
    assert SECRET.encode() not in resp.data


@pytest.mark.parametrize('url', [
    '/api/download/%2e%2e/.env',
    '/api/download/%2e%2e%2f.env',
    '/api/download/part1/%2e%2e/%2e%2e/.env',
])
def test_download_url_encoded_traversal_is_blocked(client, url):
    resp = client.get(url, follow_redirects=True)
    assert resp.status_code in (403, 404)
    assert SECRET.encode() not in resp.data


def test_download_absolute_path_url_is_blocked(client):
    resp = client.get('/api/download//etc/passwd', follow_redirects=True)
    assert resp.status_code in (403, 404)
    assert b'root:' not in resp.data


@pytest.mark.parametrize('absolute', ['/etc/passwd', 'ENV_FILE'])
def test_download_absolute_path_argument_is_forbidden(project, absolute):
    # Call the view directly so an absolute file_path reaches the handler unchanged
    file_path = str(project / '.env') if absolute == 'ENV_FILE' else absolute
    with web_app.app.test_request_context():
        resp = web_app.download_file(file_path)
    assert resp[1] == 403


def test_download_symlink_escape_is_forbidden(client, project):
    _add_env_symlink(project)
    resp = client.get('/api/download/part1/env_link')
    assert resp.status_code == 403
    assert SECRET.encode() not in resp.data


def test_download_missing_file_is_404(client):
    assert client.get('/api/download/part1/nope.md').status_code == 404


def test_download_directory_is_404(client):
    assert client.get('/api/download/part1').status_code == 404


# Existing UI flow: file list, individual download, ZIP download

def test_file_list_entries_are_downloadable(client):
    files = client.get('/api/files').get_json()['files']
    paths = sorted(f['path'] for f in files)
    assert paths == ['part1/report.md', 'part1/sub/nested.md', 'part2/paper.md']
    for path in paths:
        # The UI calls /api/download/${path} with the path from /api/files
        assert client.get('/api/download/' + path).status_code == 200


@pytest.mark.parametrize('part, expected', [
    ('part1', {'part1/report.md', 'part1/sub/nested.md'}),
    ('part2', {'part2/paper.md'}),
    ('all', {'part1/report.md', 'part1/sub/nested.md', 'part2/paper.md'}),
])
def test_download_all_zip(client, part, expected):
    resp = client.get('/api/download-all/' + part)
    assert resp.status_code == 200
    assert resp.mimetype == 'application/zip'
    with zipfile.ZipFile(io.BytesIO(resp.data)) as zf:
        assert set(zf.namelist()) == expected


@pytest.mark.parametrize('part', ['part3', '..', 'artifacts', '.env'])
def test_download_all_rejects_unknown_part(client, part):
    assert client.get('/api/download-all/' + part).status_code == 400


def test_download_all_skips_symlink_escape(client, project):
    _add_env_symlink(project)
    resp = client.get('/api/download-all/part1')
    assert resp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(resp.data)) as zf:
        assert set(zf.namelist()) == {'part1/report.md', 'part1/sub/nested.md'}
        for name in zf.namelist():
            assert SECRET.encode() not in zf.read(name)


# Server startup: default bind address, warning, secret key

def _run_main(monkeypatch, tmp_path, argv):
    """Run web_app.py as __main__ with socketio.run patched, so no socket is opened."""
    calls = []

    def fake_run(self, app, host=None, port=None, **kwargs):
        calls.append({'host': host, 'port': port})

    monkeypatch.setattr(flask_socketio.SocketIO, 'run', fake_run)
    monkeypatch.setattr(dotenv, 'load_dotenv', lambda *a, **k: False)  # ignore a local .env
    monkeypatch.setattr(sys, 'argv', ['web_app.py', *argv])
    monkeypatch.chdir(tmp_path)  # the main block creates ./templates
    module_globals = runpy.run_path(str(PROJECT_DIR / 'web_app.py'), run_name='__main__')
    return calls, module_globals


def test_default_bind_is_loopback(monkeypatch, tmp_path, capsys):
    calls, _ = _run_main(monkeypatch, tmp_path, [])
    assert calls == [{'host': '127.0.0.1', 'port': 8050}]
    assert 'WARNING' not in capsys.readouterr().out


def test_non_loopback_bind_prints_warning(monkeypatch, tmp_path, capsys):
    calls, _ = _run_main(monkeypatch, tmp_path, ['--host', '0.0.0.0'])
    assert calls == [{'host': '0.0.0.0', 'port': 8050}]
    assert 'WARNING: binding to a non-loopback address' in capsys.readouterr().out


def test_secret_key_is_not_hardcoded(monkeypatch, tmp_path):
    monkeypatch.delenv('FLASK_SECRET_KEY', raising=False)
    _, first = _run_main(monkeypatch, tmp_path, [])
    _, second = _run_main(monkeypatch, tmp_path, [])
    first_key = first['app'].config['SECRET_KEY']
    assert first_key != 'tech-recon-secret-key-2025'
    assert len(first_key) == 64
    assert first_key != second['app'].config['SECRET_KEY']

    monkeypatch.setenv('FLASK_SECRET_KEY', 'value-from-env')
    _, from_env = _run_main(monkeypatch, tmp_path, [])
    assert from_env['app'].config['SECRET_KEY'] == 'value-from-env'
