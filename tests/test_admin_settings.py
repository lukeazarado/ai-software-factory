"""Regression: admin-only generic settings, single SQLite, privacy revision and audit."""
import base64
from hashlib import sha256
import hmac
import os
import sqlite3
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from apps.agenda_atleta.app import create_app
from apps.agenda_atleta.admin_settings import ALL_DEFINITIONS, validate_value

ID = 'google-client-test'
URI = 'http://127.0.0.1:8000/auth/google/callback'

@pytest.fixture
def instance(tmp_path, monkeypatch):
    key_bytes = os.urandom(32)
    encryption_key = base64.urlsafe_b64encode(key_bytes).decode()
    db = tmp_path / 'athletes-secure.sqlite3'
    claims = {'sub':'admin-google-user','nonce':''}
    admin_id = hmac.new(key_bytes,b'google-sub:admin-google-user',sha256).hexdigest()
    monkeypatch.setenv('APP_ADMIN_OWNER_IDS',admin_id)
    app = create_app(db, encryption_key=encryption_key,client_id=ID,client_secret='test-secret',
                     redirect_uri=URI, token_exchange=lambda *args:{'id_token':'test-token'},
                     token_verifier=lambda *args:claims.copy())
    return app,db,claims,admin_id,encryption_key


def login(client,db,claims,identity):
    claims['sub']=identity
    r=client.get('/auth/google/start',follow_redirects=False)
    assert r.status_code==302
    state=parse_qs(urlparse(r.headers['location']).query)['state'][0]
    with sqlite3.connect(db) as conn:
        claims['nonce']=conn.execute('SELECT nonce FROM login_flows ORDER BY rowid DESC LIMIT 1').fetchone()[0]
    r=client.get('/auth/google/callback',params={'code':'test-code','state':state},follow_redirects=False)
    assert r.status_code==303,r.text
    return client.get('/api/auth/me').json()


def test_unified_database_and_default_parameter_catalog(instance):
    _,db,_,_,_=instance
    with sqlite3.connect(db) as conn:
        tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {'athletes','app_settings','app_settings_audit','items','sessions','privacy_ack'}.issubset(tables)
        assert conn.execute('SELECT COUNT(*) FROM app_settings').fetchone()[0] == len(ALL_DEFINITIONS)
        assert conn.execute("SELECT revision FROM app_settings WHERE key='legal.privacy_notice'").fetchone()[0] == 0


def test_admin_route_requires_server_env_allowlist(instance):
    app,db,claims,owner_id,_=instance
    with TestClient(app) as admin:
        auth=login(admin,db,claims,'admin-google-user')
        assert auth['ownerId']==owner_id and auth['isAdmin']
        assert admin.get('/admin').status_code==200
        assert admin.get('/static/admin.js').status_code==200
        assert admin.get('/static/admin.css').status_code==200
        with TestClient(app) as user:
            userauth=login(user,db,claims,'other-user')
            assert not userauth['isAdmin']
            for path in ['/admin','/static/admin.js','/static/admin.css','/api/admin/settings']:
                assert user.get(path).status_code==403
            assert user.put('/api/admin/settings/brand.product_name',headers={'X-CSRF-Token':userauth['csrfToken']},
                            json={'revision':0,'value':'Outra empresa'}).status_code==403


def test_parameter_write_requires_csrf_and_revision_and_audits(instance):
    app,db,claims,_,_=instance
    with TestClient(app) as client:
        auth=login(client,db,claims,'admin-google-user')
        key='brand.product_name'
        base='/api/admin/settings/'+key
        assert client.put(base,json={'revision':0,'value':'Agenda Brasil'}).status_code==403
        headers={'X-CSRF-Token':auth['csrfToken']}
        changed=client.put(base,headers=headers,json={'revision':0,'value':'Agenda Brasil'})
        assert changed.status_code==200,changed.text
        assert changed.json()['revision']==1
        assert client.put(base,headers=headers,json={'revision':0,'value':'Perdido'}).status_code==409
        assert client.put('/api/admin/settings/GOOGLE_CLIENT_SECRET',headers=headers,json={'revision':0,'value':'x'}).status_code==404
        data=client.get('/api/admin/settings').json()
        assert data['version']=='2.0.0-rc.1'
        assert data['commercialStatus']=='NAO_LIBERADO'
        assert next(x for x in data['settings'] if x['key']==key)['value']=='Agenda Brasil'
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT COUNT(*) FROM app_settings_audit WHERE key=?',(key,)).fetchone()[0]==1
        assert conn.execute('SELECT value_json FROM app_settings WHERE key=?',(key,)).fetchone()[0]=='"Agenda Brasil"'


def test_legal_document_edit_invalidates_previous_acknowledgement(instance):
    app,db,claims,_,_=instance
    with TestClient(app) as client:
        auth=login(client,db,claims,'admin-google-user')
        headers={'X-CSRF-Token':auth['csrfToken']}
        notice=client.get('/api/privacy').json()
        assert notice['privacy_notice']==''
        assert client.post('/api/privacy/ack',headers=headers,json={'read_notice':True,'responsible_adult':True}).status_code==200
        assert client.get('/api/privacy/ack').json()['acknowledged']
        updated=client.put('/api/admin/settings/legal.privacy_notice',headers=headers,
                           json={'revision':0,'value':'Aviso de testes — dados fictícios'}).json()
        assert updated['revision']==1
        new_notice=client.get('/api/privacy').json()
        assert new_notice['privacy_notice']=='Aviso de testes — dados fictícios'
        assert new_notice['version'] != notice['version']
        assert not client.get('/api/privacy/ack').json()['acknowledged']
        assert client.post('/api/privacy/ack',headers=headers,json={'read_notice':True,'responsible_adult':True}).status_code==200
        assert client.get('/api/privacy/ack').json()['acknowledged']


def test_obligations_are_typed_and_do_not_certify_compliance(instance):
    app,db,claims,_,_=instance
    with TestClient(app) as client:
        auth=login(client,db,claims,'admin-google-user')
        headers={'X-CSRF-Token':auth['csrfToken']}
        url='/api/admin/settings/obligation.eca_digital_assessment'
        assert client.put(url,headers=headers,json={'revision':0,'value':{'status':'evidence_recorded','owner':'','evidence_reference':'','reviewed_on':''}}).status_code==422
        valid={'status':'in_review','owner':'Jurídico','evidence_reference':'REF-TESTE','reviewed_on':''}
        assert client.put(url,headers=headers,json={'revision':0,'value':valid}).status_code==200
        result=client.get('/api/admin/settings').json()
        assert result['obligations']['inReview']==1
        assert result['commercialStatus']=='NAO_LIBERADO'


def test_config_values_validated_and_cannot_embed_secrets():
    with pytest.raises(ValueError):validate_value('oauth.google_secret','secret')
    with pytest.raises(ValueError):validate_value('privacy.retention_days',0)
    with pytest.raises(ValueError):validate_value('supplier.contact_url','javascript:alert(1)')
    with pytest.raises(ValueError):validate_value('brand.product_name','X'*101)
    assert validate_value('privacy.retention_days',365)==365


def test_restart_preserves_settings_and_audit(instance):
    app,db,claims,_,key=instance
    with TestClient(app) as client:
        auth=login(client,db,claims,'admin-google-user')
        assert client.put('/api/admin/settings/brand.product_name',headers={'X-CSRF-Token':auth['csrfToken']},
                          json={'revision':0,'value':'Agenda Renovada'}).status_code==200
    app2=create_app(db,encryption_key=key,client_id=ID,client_secret='test-secret',redirect_uri=URI,
                    token_exchange=lambda *args:{'id_token':'test-token'},token_verifier=lambda *args:claims.copy())
    with TestClient(app2) as c:
        login(c,db,claims,'admin-google-user')
        values=c.get('/api/admin/settings').json()
        assert next(s for s in values['settings'] if s['key']=='brand.product_name')['value']=='Agenda Renovada'
        assert values['recentChanges'][0]['revision']==1