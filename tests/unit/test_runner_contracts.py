import os
import subprocess
import sys

import pytest

from common.run_lock import RunLock
from common.ui_state import wait_query_finished
from common.stability import classify
from pages.Server_Page.ServerListPage import ServerListPage


def test_only_observed_online_zero_persistence_is_marked_as_a_pending_business_rule():
    node='testcases/test_023_server_list.py::test_server_invalid_value_validation[zero]'
    message='业务规则待确认：最大在线用户数0已保存并回读，测试记录已清理'
    assert classify(node,message)==('pending','server-online-zero-rule')
    assert classify(node,'无法选择服务器类型')[0]=='unclassified'


def test_server_module_cleanup_reports_failure_and_still_attempts_other_registered_data():
    class Registry:
        _pending_server_cleanup={'failed_id','other_id'}
        _server_name_history={'failed_id':['uiauto_failed'],'other_id':['uiauto_other']}
        attempted=[]
        def ensure_server_absent(self,identifier):
            self.attempted.append(identifier)
            if identifier=='failed_id':raise RuntimeError('simulated cleanup failure')
            return True
    page=Registry()
    with pytest.raises(AssertionError,match='兜底清理失败'):
        ServerListPage.cleanup_registered_servers(page)
    assert set(page.attempted)=={'failed_id','other_id'}


def test_completed_empty_table_without_new_request_cannot_prove_absence():
    class Driver:
        def execute_script(self,*args):return False
    class Page:
        driver=Driver()
        def wait_loading_finished(self,**kwargs):return True
        def table_snapshot(self):return '{"rows":[]}'
    assert wait_query_finished(Page(),0,timeout=0.1) is False


@pytest.mark.skipif(os.name!='nt',reason='Windows runner contract')
def test_same_target_cannot_run_in_second_process_and_lock_recovers_after_exception():
    code="from common.run_lock import RunLock\nwith RunLock('unit-test-target','unit-user'): print('acquired')"
    env={**os.environ,'PYTHONIOENCODING':'utf-8'}
    with pytest.raises(RuntimeError):
        with RunLock('unit-test-target','unit-user'):
            child=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,encoding='utf-8',env=env)
            assert child.returncode != 0
            raise RuntimeError('simulate interrupted runner')
    child=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,encoding='utf-8',env=env)
    assert child.returncode==0 and 'acquired' in child.stdout
