import json
from types import SimpleNamespace

from conf.conf import ConfigManager
from common.privacy import redact_report_files
from conftest import _redact_case_failure
from common.stability import source_manifest


def test_plugin_trace_credentials_are_masked_without_rewriting_failure(tmp_path,monkeypatch):
    secret='synthetic-secret-for-unit-only'
    monkeypatch.setattr(ConfigManager,'AI_CR_API_KEY',secret)
    report=tmp_path/'result.json'
    report.write_text(json.dumps({'status':'failed','statusDetails':{'trace':f'configured api_key={secret}'},
        'labels':[{'name':'failure_origin','value':'external_service'}]}),encoding='utf-8')
    assert redact_report_files(tmp_path)==1
    saved=json.loads(report.read_text(encoding='utf-8'))
    assert saved['status']=='failed'
    assert saved['labels']==[{'name':'failure_origin','value':'external_service'}]
    assert secret not in saved['statusDetails']['trace']
    assert 'configured api_key=' in saved['statusDetails']['trace']


def test_password_case_failure_masks_temporary_and_invalid_inputs():
    module=SimpleNamespace(PASSWORD_DATA={'normal_default':{'dollar':{'password':'Temp123$'}},'invalid':{'short':{'password':'Ab1$xxx'}}},
        NORMAL_PASSWORD='unit-original',_invalid_values=lambda case,original:(original,case['password'],case['password']))
    item=SimpleNamespace(fspath='test_030_personal_profile.py',module=module)
    safe=_redact_case_failure(item,'account=unit-user original=unit-original new=Temp123$ rejected=Ab1$xxx')
    assert 'unit-user' in safe
    assert all(value not in safe for value in ('unit-original','Temp123$','Ab1$xxx'))


def test_manifest_masks_assertion_credentials_but_fingerprints_original_source(tmp_path,monkeypatch):
    first='SyntheticCredential1$'
    second='SyntheticCredential2$'
    (tmp_path/'testcases').mkdir()
    source=tmp_path/'testcases'/'test_manifest.py'
    for name in ('conftest.py','run.py','pytest.ini','requirements.txt'):
        (tmp_path/name).write_text('',encoding='utf-8')
    def capture(secret):
        monkeypatch.setattr(ConfigManager,'PASSWORD',secret)
        source.write_text(f'def test_login(page):\n    assert page.login({secret!r}) is True\n',encoding='utf-8')
        result=source_manifest(tmp_path)
        assert secret not in json.dumps(result)
        assert '[已脱敏]' in json.dumps(result,ensure_ascii=False)
        return result
    before=capture(first)
    after=capture(second)
    assert before['functions']==after['functions']
    assert before['code_sha256']!=after['code_sha256']
