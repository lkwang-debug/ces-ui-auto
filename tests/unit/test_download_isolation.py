"""Regression checks for failure branches that previously poisoned later tests."""
from pathlib import Path

import pytest

from common.runtime_artifacts import prepare_download, wait_for_download
from common.runtime_artifacts import _collect_download_events
from conf.conf import ConfigManager
from pages.Server_Page.DataManagePage import DataManagePage


class Browser:
    def __init__(self):
        self.destination = None

    def execute_cdp_cmd(self, method, params):
        self.destination = params['downloadPath']

    def get_log(self, kind):
        return []

    def find_elements(self, *locator):
        return []


@pytest.mark.parametrize('raises', [False, True])
def test_backup_precondition_failure_restores_browser_destination(tmp_path, monkeypatch, raises):
    monkeypatch.setattr(ConfigManager, 'DOWNLOAD_DIR', str(tmp_path))
    browser = Browser()
    page = object.__new__(DataManagePage)
    page.driver = browser

    def ready():
        if raises:
            raise RuntimeError('simulated page initialization failure')

    page._ensure_page_ready = ready
    # Start with a previous module's directory to make restoration observable.
    prepare_download(browser, tmp_path / 'previous_module')
    if raises:
        with pytest.raises(RuntimeError):
            page.download_existing_backup()
    else:
        assert page.download_existing_backup() is None
    assert browser.destination == str(tmp_path.resolve())
    next_directory = prepare_download(browser)
    assert Path(browser.destination) == next_directory
    assert next_directory.parent == tmp_path


def test_download_from_previous_case_cannot_satisfy_current_case(tmp_path):
    browser = Browser()
    previous = prepare_download(browser, tmp_path)
    (previous / 'old.log').write_bytes(b'previous successful download')
    current = prepare_download(browser, tmp_path)
    assert current != previous
    assert wait_for_download(current, extensions={'.log'}, timeout=0.1, driver=browser) is None


def test_nonempty_error_page_is_not_an_excel_download(tmp_path):
    browser = Browser()
    current = prepare_download(browser, tmp_path)
    (current / 'export.xlsx').write_bytes(b'<html>upstream unavailable</html>')
    assert wait_for_download(current, extensions={'.xlsx'}, timeout=0.6, driver=browser) is None


def test_download_diagnostics_do_not_keep_query_tokens():
    import json
    browser=Browser()
    browser.get_log=lambda kind:[{'message':json.dumps({'message':{'method':'Network.responseReceived','params':{
        'type':'XHR','response':{'url':'http://test.invalid/export?token=secret-value','status':500,'mimeType':'application/json'}}}})}]
    evidence={'请求':[],'下载事件':[]}
    _collect_download_events(browser,evidence)
    assert evidence['请求'][0]['路径']=='/export'
    assert 'secret-value' not in json.dumps(evidence)
