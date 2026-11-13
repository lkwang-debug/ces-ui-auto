from urllib.parse import quote
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread

import pytest
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import JavascriptException

from conftest import chrome_options, resolve_chromedriver_path
from common.Base import Base
from common.semantic_controls import action_locator, cancel_transient_layers,set_date_field
from common.ui_state import strict_wait,wait_page_layout,wait_query_finished,wait_control_unobscured
from pages.Index_Page.index import LoginPage
from pages.ContactList_Page.UserPage import UserManagerPage
from pages.ContactList_Page.OrganizePage import OrganizeManagerPage
from pages.ContactList_Page.TerminalPage import TerminalManagerPage
from pages.Meeting_Page.MeetingInfoPage import MeetingInfoPage
from pages.Server_Page.ServerListPage import ServerListPage


@pytest.fixture(scope='module')
def browser():
    path=resolve_chromedriver_path()
    browser=webdriver.Chrome(service=Service(path),options=chrome_options(headless=True))
    yield browser
    browser.quit()


def test_extra_columns_and_nested_buttons_cannot_redirect_modify(browser):
    page=Base(driver=browser)
    browser.get('data:text/html;charset=utf-8,'+quote('''<main><table><thead><tr><th>新增列</th><th>会议室名称</th><th>操作</th></tr></thead><tbody>
      <tr><td>x</td><td>uiauto_case</td><td>
      <span><button title="管理" onclick="window.clicked='authorize'">管理</button></span>
      <span><button title="编辑" onclick="window.clicked='modify'">编辑</button></span>
      <span><button title="删除" onclick="window.clicked='delete'">删除</button></span>
      </td></tr></tbody></table></main>'''))
    locator=action_locator(page,'会议室名称','uiauto_case','修改')
    browser.find_element(*locator).click()
    assert browser.execute_script('return window.clicked')=='modify'


def test_labelled_image_actions_are_resolved_by_meaning_instead_of_position(browser):
    browser.get('about:blank')
    browser.execute_script('''document.body.innerHTML=`<main><table><thead><tr><th>部门名称</th><th>操作</th></tr></thead><tbody>
      <tr><td>unit_org</td><td><img title="删除" style="width:20px;height:20px" onclick="window.clicked='delete'">
      <img title="编辑" style="width:20px;height:20px" onclick="window.clicked='modify'"></td></tr></tbody></table></main>`;''')
    page=Base(driver=browser)
    browser.find_element(*action_locator(page,'部门名称','unit_org','修改')).click()
    assert browser.execute_script('return window.clicked')=='modify'
    browser.find_element(*action_locator(page,'部门名称','unit_org','删除')).click()
    assert browser.execute_script('return window.clicked')=='delete'


def test_unlabelled_organization_buttons_require_the_inspected_two_button_structure(browser):
    browser.get('about:blank')
    browser.execute_script('''document.body.innerHTML=`<main><table><thead><tr><th>部门名称</th><th>操作</th></tr></thead><tbody>
      <tr><td>unit_org</td><td><div class="dept-oper"><button onclick="window.clicked='edit'"><img width="16" height="16"></button>
      <button onclick="window.clicked='delete'"><img width="16" height="16"></button></div></td></tr></tbody></table></main>`;''')
    page=OrganizeManagerPage(driver=browser)
    browser.find_element(*page._exact_organize_modify_button_locator('unit_org')).click()
    assert browser.execute_script('return window.clicked')=='edit'
    browser.find_element(*page._exact_organize_delete_button_locator('unit_org')).click()
    assert browser.execute_script('return window.clicked')=='delete'
    browser.execute_script("document.querySelector('.dept-oper').insertAdjacentHTML('afterbegin','<button>新增动作</button>')")
    with pytest.raises(AssertionError,match='缺少明确的修改控件'):
        page._exact_organize_modify_button_locator('unit_org')


def test_failed_case_cancels_layer_and_next_action_remains_usable(browser):
    browser.get('data:text/html;charset=utf-8,'+quote('''<main><button id="next" onclick="window.nextRan=true">下一用例</button></main>
      <div class="ant-modal-content"><div class="ant-modal-title">新增</div>
      <button onclick="window.saved=true">保存</button>
      <button class="ant-modal-close" onclick="this.parentElement.style.display='none'">关闭</button></div>'''))
    with pytest.raises(RuntimeError):
        try:
            raise RuntimeError('simulate assertion failure after opening form')
        finally:
            assert cancel_transient_layers(browser)==['新增']
    browser.find_element('id','next').click()
    assert browser.execute_script('return !!window.nextRan && !window.saved')


def test_programming_error_is_not_swallowed_as_timeout(browser):
    with pytest.raises(JavascriptException):
        strict_wait(lambda: browser.execute_script('throw new Error("broken selector script")'),timeout=5)


def test_login_refills_after_render_without_submitting_authentication(browser):
    browser.get('about:blank#/ui/login')
    browser.execute_script('''document.body.innerHTML='<form><input placeholder="用户名"><input type="password"><button type="button" onclick="window.submitted=true">登录</button></form>';
      window.erased=false;const input=document.querySelector('input');input.addEventListener('input',()=>{
      if(!window.erased){window.erased=true;setTimeout(()=>input.value='',0)}});''')
    page=LoginPage(driver=browser)
    page.send_users_name('uiauto_recovery')
    assert browser.find_element(*page.login_name).get_attribute('value')=='uiauto_recovery'
    assert not browser.execute_script('return !!window.submitted')


def test_logged_in_identity_is_read_from_page_even_if_expected_name_differs(browser):
    browser.get('about:blank#/ui/home')
    browser.execute_script("document.body.innerHTML='<header><span class=\"hst-user-name\">actual_account</span></header><main></main>'")
    page=LoginPage(driver=browser)
    page.last_authenticated_username='expected_account'
    assert page.get_index_user_name_text()=='actual_account'
    browser.execute_script("document.querySelector('.hst-user-name').remove()")
    assert page.get_index_user_name_text()==''


def _layout_fixture(browser):
    browser.get('about:blank#/ui/unit-layout')
    browser.execute_script('''document.body.innerHTML='<main><span class="ant-tree-title">根组织</span><div class="ant-table-wrapper"><table><thead><tr><th>用户名</th><th>昵称</th></tr></thead><tbody><tr><td>existing</td><td>原值</td></tr></tbody></table></div></main>';''')
    return Base(driver=browser)


def test_layout_cache_cannot_substitute_for_a_new_query_completion(browser):
    page=_layout_fixture(browser)
    assert wait_page_layout(page,'#/ui/unit-layout',[['用户名'],['昵称']],'.ant-tree-title',allow_cached=True)
    browser.execute_script("document.querySelector('tbody').innerHTML=''")
    assert wait_page_layout(page,'#/ui/unit-layout',[['用户名'],['昵称']],'.ant-tree-title',allow_cached=True)
    started=browser.execute_script('return performance.now()')
    assert not wait_query_finished(page,started,timeout=0.2,request_path='/unit-query')


def test_recreated_component_with_same_headers_must_finish_rendering(browser):
    page=_layout_fixture(browser)
    assert wait_page_layout(page,'#/ui/unit-layout',[['用户名'],['昵称']],'.ant-tree-title',allow_cached=True)
    browser.execute_script('''const original=document.querySelector('.ant-table-wrapper'),replacement=original.cloneNode(true);
      replacement.querySelector('td').innerText='pending';original.replaceWith(replacement);
      setTimeout(()=>replacement.querySelector('td').innerText='ready',100);''')
    assert wait_page_layout(page,'#/ui/unit-layout',[['用户名'],['昵称']],'.ant-tree-title',allow_cached=True)
    assert browser.execute_script("return document.querySelector('td').innerText")=='ready'


@pytest.fixture
def query_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ('/basis/v1/userInfo/userEdit','/basis/v1/departInfo/departEdit'):time.sleep(0.4)
            self.send_response(500 if self.path=='/failed-query' else 200)
            self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers()
            self.wfile.write(b'<main><table><thead><tr><th>name</th></tr></thead><tbody></tbody></table></main>')
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown();server.server_close();thread.join(timeout=2)


def test_http_error_cannot_make_an_empty_table_a_successful_query(browser,query_server):
    browser.get(query_server)
    page=Base(driver=browser)
    started=browser.execute_script("const started=performance.now();fetch('/failed-query');return started")
    with pytest.raises(AssertionError,match='HTTP 500'):
        wait_query_finished(page,started,timeout=3,request_path='/failed-query')


def test_session_redirect_cannot_prove_a_record_is_absent(browser,query_server):
    browser.get(query_server)
    page=Base(driver=browser)
    started=browser.execute_script("const started=performance.now();fetch('/ok').then(()=>location.hash='/ui/login');return started")
    with pytest.raises(AssertionError,match='返回登录页'):
        wait_query_finished(page,started,timeout=3,request_path='/ok')


def test_legacy_date_confirm_anchor_commits_the_selected_value(browser):
    browser.get('about:blank')
    browser.execute_script('''document.body.innerHTML='<main><input placeholder="开始时间"></main><div class="ant-calendar-picker-container"><a role="button" class="ant-calendar-ok-btn" href="#">确定</a></div>';
      document.querySelector('a').onclick=e=>{e.preventDefault();e.target.parentElement.style.display='none'};''')
    page=Base(driver=browser)
    set_date_field(page,'开始时间','2026-11-05')
    assert browser.find_element('css selector','main input').get_attribute('value')=='2026-11-05 00:00:00'


def test_edit_waits_for_requested_user_data_before_allowing_field_changes(browser,query_server,monkeypatch):
    browser.get(query_server)
    page=UserManagerPage(driver=browser)
    monkeypatch.setattr(page,'_ensure_user_page_ready',lambda:True)
    monkeypatch.setattr(page,'_find_exact_user_row_by_search',lambda *args,**kwargs:True)
    def open_editor(*args,**kwargs):
        browser.execute_script('''document.body.insertAdjacentHTML('beforeend',`<div class="ant-modal-content"><div class="ant-modal-title">修改</div>
          <div class="ant-form-item"><label>用户姓名</label><input id="form_item_username" value="unit_target" readonly></div>
          <div class="ant-form-item"><label>用户昵称</label><input id="form_item_nickname" value="old_value"></div>
          <div class="ant-form-item"><label>手机号码</label><input id="form_item_phone" value=""></div></div>`);
          fetch('/basis/v1/userInfo/userEdit').then(()=>document.querySelector('#form_item_nickname').value='loaded_value');''')
        return True
    monkeypatch.setattr(page,'_click_user_row_action',open_editor)
    assert page._open_modify_user_dialog('unit_target')
    assert browser.find_element('id','form_item_nickname').get_attribute('value')=='loaded_value'


def test_password_input_survives_repaint_and_ignores_extra_fields(browser):
    browser.get('about:blank')
    browser.execute_script('''document.body.innerHTML=`<div class="ant-modal-content"><div class="ant-form-item"><label>额外字段</label><input id="decoy"></div>
      <div class="ant-form-item"><label>密码</label><input type="password" id="form_item_password"></div></div>`;
      window.erased=false;document.querySelector('#form_item_password').addEventListener('input',()=>{
        if(window.erased)return;window.erased=true;setTimeout(()=>{const old=document.querySelector('#form_item_password'),replacement=old.cloneNode(true);
        replacement.value='';old.replaceWith(replacement)},60)});''')
    page=UserManagerPage(driver=browser)
    page.send_password('Synthetic123!')
    assert browser.find_element('id','form_item_password').get_attribute('value')=='Synthetic123!'
    assert browser.find_element('id','decoy').get_attribute('value')==''


def test_organization_edit_waits_for_original_value_and_uses_labelled_control(browser,query_server,monkeypatch):
    browser.get(query_server)
    page=OrganizeManagerPage(driver=browser)
    monkeypatch.setattr(page,'_find_exact_organize_row_with_search_priority',lambda *args,**kwargs:True)
    browser.execute_script('''document.querySelector('main').innerHTML=`<table><thead><tr><th>额外列</th><th>部门名称</th><th>操作</th></tr></thead>
      <tbody><tr><td>decoy</td><td>unit_org</td><td><span><button title="修改" id="edit">修改</button></span><span><button title="删除">删除</button></span></td></tr></tbody></table>`;
      document.querySelector('#edit').onclick=()=>{
        document.body.insertAdjacentHTML('beforeend',`<div class="ant-modal-content"><div class="ant-modal-title">修改</div>
          <div class="ant-form-item"><label>额外字段</label><input id="decoy"></div>
          <div class="ant-form-item"><label>部门名称：</label><input id="department"></div></div>`);
        fetch('/basis/v1/departInfo/departEdit').then(()=>document.querySelector('#department').value='unit_org');};''')
    assert page._open_organize_editor('unit_org')
    assert browser.find_element('id','department').get_attribute('value')=='unit_org'
    assert page._replace_visible_modal_input('部门名称','unit_org_changed')
    assert browser.find_element('id','department').get_attribute('value')=='unit_org_changed'
    assert browser.find_element('id','decoy').get_attribute('value')==''


def test_terminal_editor_requires_target_name_and_serial_after_delayed_render(browser,monkeypatch):
    browser.get('about:blank')
    page=TerminalManagerPage(driver=browser)
    monkeypatch.setattr(page,'_find_exact_terminal_row_via_search',lambda *args,**kwargs:True)
    browser.execute_script('''document.body.innerHTML=`<main><table><thead><tr><th>额外列</th><th>终端名称</th><th>终端序列号</th><th>操作</th></tr></thead>
      <tbody><tr><td>extra</td><td>unit_terminal</td><td>TEST001</td><td><img id="edit" title="编辑" style="width:20px;height:20px"></td></tr></tbody></table></main>`;
      document.querySelector('#edit').onclick=()=>{
        document.body.insertAdjacentHTML('beforeend',`<div class="ant-modal-content"><div class="ant-form-item"><label>额外字段</label><input id="decoy"></div>
          <div class="ant-form-item"><label>终端名称：</label><input id="terminal"></div>
          <div class="ant-form-item"><label>终端序列号：</label><input id="serial"></div></div>`);
        setTimeout(()=>{document.querySelector('#terminal').value='unit_terminal';document.querySelector('#serial').value='TEST001'},400);};''')
    assert page._open_terminal_editor('unit_terminal')
    assert page._replace_visible_modal_input(page.terminal_name_label,'changed_terminal')
    assert browser.find_element('id','terminal').get_attribute('value')=='changed_terminal'
    assert browser.find_element('id','serial').get_attribute('value')=='TEST001'
    assert browser.find_element('id','decoy').get_attribute('value')==''


def test_authorization_close_waits_for_remaining_wrapper_before_search(browser,monkeypatch):
    browser.get('about:blank')
    browser.execute_script('''document.body.innerHTML=`<main><input placeholder="请输入搜索内容"></main>
      <div class="ant-modal-wrap" style="position:fixed;inset:0;z-index:1000;background:#eee"><div class="ant-modal-content">
      <button id="close">关闭</button></div></div>`;
      document.querySelector('#close').onclick=()=>{document.querySelector('.ant-modal-content').remove();
        setTimeout(()=>document.querySelector('.ant-modal-wrap').remove(),400)};''')
    page=MeetingInfoPage(driver=browser)
    monkeypatch.setattr(page,'_modal_action_button_locator',lambda *args:('id','close'))
    monkeypatch.setattr(page,'submit_search',lambda:True)
    assert page._close_authorize_modal()
    assert not browser.find_elements('css selector','.ant-modal-wrap')
    assert page._search_keyword('unit_meeting')
    assert browser.find_element('css selector','main input').get_attribute('value')=='unit_meeting'


def test_meeting_search_does_not_click_through_an_unclosed_modal(browser,monkeypatch):
    browser.get('about:blank')
    browser.execute_script('''document.body.innerHTML=`<main><input placeholder="请输入搜索内容" value="unchanged"></main>
      <div class="ant-modal-wrap" style="position:fixed;inset:0;z-index:1000;background:#eee">仍未关闭</div>`;''')
    page=MeetingInfoPage(driver=browser)
    monkeypatch.setattr(page,'submit_search',lambda:pytest.fail('被遮挡时不得提交查询'))
    with pytest.raises(AssertionError,match='弹窗遮罩阻挡'):
        page._search_keyword('must_not_query')
    assert browser.find_element('css selector','main input').get_attribute('value')=='unchanged'


def test_case_hygiene_waits_for_closing_overlay_even_after_modal_content_is_gone(browser):
    browser.get('about:blank')
    browser.execute_script('''document.body.innerHTML=`<button id="next" onclick="window.nextRan=true">下一操作</button>
      <div class="ant-modal-wrap" style="position:fixed;inset:0;z-index:1000;background:#eee"></div>`;
      setTimeout(()=>document.querySelector('.ant-modal-wrap').remove(),400);''')
    assert cancel_transient_layers(browser)==[]
    browser.find_element('id','next').click()
    assert browser.execute_script('return window.nextRan===true')


def test_unobscured_control_wait_keeps_native_scrolling_for_offscreen_inputs(browser):
    browser.get('about:blank')
    browser.execute_script('''document.body.innerHTML='<div style="height:1800px"></div><input id="target">';''')
    page=Base(driver=browser)
    field=wait_control_unobscured(page,('id','target'),timeout=2)
    assert field is not False
    field.click()
    field.send_keys('after_scroll')
    assert browser.find_element('id','target').get_attribute('value')=='after_scroll'


def test_noninteractive_retained_drawer_mask_does_not_block_the_next_case(browser):
    browser.get('about:blank')
    browser.execute_script('''document.body.innerHTML=`<button id="next" onclick="window.nextRan=true">下一操作</button>
      <div class="ant-drawer-mask" style="position:fixed;inset:0;pointer-events:none;opacity:0"></div>`;''')
    assert cancel_transient_layers(browser)==[]
    browser.find_element('id','next').click()
    assert browser.execute_script('return window.nextRan===true')


def _delayed_server_dropdown(browser,persist=True):
    browser.get('about:blank')
    browser.execute_script('''document.body.innerHTML=`<div class="ant-modal-content"><div class="ant-form-item">
      <label>设备类型</label><div id="select" class="ant-select" style="width:240px;height:32px;border:1px solid black">
      <input role="combobox" aria-controls="owned-list" aria-expanded="false" readonly style="display:none">
      <span class="ant-select-selection-item">资源平台服务器</span></div></div></div>
      <div class="ant-select-dropdown" style="position:fixed;left:500px;top:70px;width:240px;height:32px">
      <div class="ant-select-item-option" onclick="window.wrongDropdown=true" style="height:32px">会议服务器</div></div>`;
      window.persist=arguments[0];window.attempted=0;
      document.querySelector('#select').onclick=()=>{
        const select=document.querySelector('#select'),input=select.querySelector('input');
        if(select.classList.contains('ant-select-open')){select.classList.remove('ant-select-open');input.setAttribute('aria-expanded','false');document.querySelector('#owned-popup')?.remove();return;}
        select.classList.add('ant-select-open');input.setAttribute('aria-expanded','true');
        setTimeout(()=>{if(!select.classList.contains('ant-select-open'))return;
          document.body.insertAdjacentHTML('beforeend',`<div id="owned-popup" class="ant-select-dropdown" style="position:fixed;left:8px;top:85px;width:240px;height:36px">
          <div id="owned-list" role="listbox" style="width:1px;height:1px;overflow:hidden"><div role="option" onclick="window.hiddenOption=true">会议服务器</div></div>
          <div id="real-option" class="ant-select-item-option" style="width:230px;height:32px">会议服务器</div></div>`);
          document.querySelector('#real-option').onclick=()=>{window.attempted++;
            if(window.persist)select.querySelector('.ant-select-selection-item').textContent='会议服务器';
            if(window.persist)window.afterSelect?.();
            select.classList.remove('ant-select-open');input.setAttribute('aria-expanded','false');document.querySelector('#owned-popup').remove();};
        },250);
      };''',persist)
    return ServerListPage(driver=browser),browser.find_element('css selector','.ant-modal-content')


def test_server_dropdown_waits_for_its_own_options_and_reads_selection_back(browser):
    page,modal=_delayed_server_dropdown(browser)
    assert page._choose_first_available_option(modal,'设备类型',('会议服务器',),timeout=3)
    assert browser.find_element('css selector','.ant-select-selection-item').text=='会议服务器'
    assert not browser.execute_script('return !!window.wrongDropdown||!!window.hiddenOption')
    assert browser.execute_script('return window.attempted')==1


def test_server_dropdown_click_without_a_committed_value_is_not_success(browser):
    page,modal=_delayed_server_dropdown(browser,persist=False)
    assert not page._choose_first_available_option(modal,'设备类型',('会议服务器',),timeout=1.2)
    assert browser.execute_script('return window.attempted')>0
    assert browser.find_element('css selector','.ant-select-selection-item').text=='资源平台服务器'


def test_server_type_change_finishes_before_dependent_boundary_values_are_filled(browser):
    page,modal=_delayed_server_dropdown(browser)
    browser.execute_script('''window.afterSelect=()=>document.querySelector('.ant-modal-content').insertAdjacentHTML('beforeend',
      '<div class="ant-form-item"><label>最大网络带宽</label><input id="bandwidth" value="1000000"></div>');''')
    profile={'type_names':('会议服务器',),'selects':{'设备类型':'会议服务器'}}
    assert page.fill_server_form(modal,profile,{'最大网络带宽':'0','设备类型':'会议服务器'})
    assert browser.find_element('id','bandwidth').get_attribute('value')=='0'


def test_legacy_readonly_server_type_is_verified_without_reopening_a_dropdown(browser):
    browser.get('about:blank')
    browser.execute_script('''document.body.innerHTML=`<div class="ant-modal-content"><div class="ant-form-item"><label>设备类型</label>
      <input readonly value="资源平台服务器" onclick="window.reopened=true"></div></div>`;''')
    page=ServerListPage(driver=browser)
    modal=browser.find_element('css selector','.ant-modal-content')
    assert page._choose_first_available_option(modal,'设备类型',('资源平台服务器','录制服务器'),timeout=1)
    assert not browser.execute_script('return !!window.reopened')


def test_server_cancel_waits_for_modal_disappearance(browser):
    browser.get('about:blank')
    browser.execute_script('''document.body.innerHTML=`<div class="ant-modal-content"><button id="cancel">取消</button></div>`;
      document.querySelector('#cancel').onclick=()=>setTimeout(()=>document.querySelector('.ant-modal-content').remove(),350);''')
    assert ServerListPage(driver=browser).cancel_active_dialog()
    assert not browser.find_elements('css selector','.ant-modal-content')


@pytest.mark.parametrize('replace_node',[False,True],ids=['clear_value','replace_input'])
def test_meeting_name_survives_delayed_form_reset_and_ignores_similarly_named_wrappers(browser,replace_node):
    browser.get('about:blank')
    browser.execute_script('''document.body.innerHTML=`<div class="ant-modal-content"><div class="ant-modal-title">添加会议室</div>
      <div class="ant-form-item-group"><input id="decoy" value="keep"><div class="ant-form-item"><div class="ant-form-item-label"><label>会议室名称</label></div>
      <input id="roomName"></div></div></div>`;
      window.erased=false;document.querySelector('#roomName').oninput=()=>{
        if(window.erased)return;window.erased=true;setTimeout(()=>{const field=document.querySelector('#roomName');
          if(arguments[0]){const replacement=field.cloneNode(true);replacement.value='';field.replaceWith(replacement)}else field.value='';},60);
      };''',replace_node)
    page=MeetingInfoPage(driver=browser)
    assert page.send_meeting_name('uiauto_name_reset')
    assert browser.find_element('id','roomName').get_attribute('value')=='uiauto_name_reset'
    assert browser.find_element('id','decoy').get_attribute('value')=='keep'
    assert browser.execute_script('return window.erased===true')


def test_meeting_name_changed_after_input_cannot_be_saved(browser):
    browser.get('about:blank')
    browser.execute_script('''document.body.innerHTML=`<div class="ant-modal-content"><div class="ant-modal-title">添加会议室</div>
      <div class="ant-form-item"><label>会议室名称</label><input id="roomName"></div><button onclick="window.submitted=true">保存</button></div>`;''')
    page=MeetingInfoPage(driver=browser)
    assert page.send_meeting_name('uiauto_expected')
    browser.execute_script("document.querySelector('#roomName').value=''")
    with pytest.raises(AssertionError,match='保存前会议室名称已变化'):
        page.click_save_button()
    assert not browser.execute_script('return !!window.submitted')


def _server_card_editor(browser,query_server,wrong_identity=False):
    browser.get(query_server)
    browser.execute_script('''document.querySelector('main').innerHTML=`<input class="ant-input" placeholder="请输入搜索内容">
      <div class="server-item"><div class="title" title="MainDev（会议服务）">MainDev（会议服务）</div>
      <div class="item-arrow">展开</div><div id="actions" style="display:none"><button id="edit">修改<span class="icon-edit"></span></button></div></div>`;
      window.wrongIdentity=arguments[0];
      const input=document.querySelector('main input');input.onkeyup=e=>{if(e.key!=='Enter')return;
        const query=input.value;fetch('/serv/v1/conf/list').then(()=>{
          const title=document.querySelector('.title');title.textContent=(query||'MainDev')+'（会议服务）';title.title=title.textContent;
          document.querySelector('#actions').style.display='none';});};
      document.querySelector('.item-arrow').onclick=()=>document.querySelector('#actions').style.display='block';
      document.querySelector('#edit').onclick=()=>{
        window.openedFor=document.querySelector('.title').innerText;
        document.body.insertAdjacentHTML('beforeend',`<div class="ant-modal-content"><div class="ant-form-item"><label>设备名称</label><input value="uiauto_exact"></div>
          <div class="ant-form-item"><label>设备ID</label><input disabled value="${window.wrongIdentity?'other_server':'unit_id'}"></div>
          <button onclick="window.saved=true">保存</button><button onclick="this.parentElement.remove()">取消</button></div>`);};''',wrong_identity)
    page=ServerListPage(driver=browser)
    page.open_server_list=lambda:True
    page._created_server_names={'unit_id':'uiauto_exact'}
    return page


def test_server_edit_keeps_query_locked_until_the_exact_editor_is_open(browser,query_server):
    page=_server_card_editor(browser,query_server)
    assert page._open_edit_dialog('unit_id') is not None
    assert browser.find_element('css selector','main input').get_attribute('value')=='uiauto_exact'
    assert browser.execute_script('return window.openedFor')=='uiauto_exact（会议服务）'


def test_server_edit_rejects_another_device_id_before_any_write(browser,query_server):
    page=_server_card_editor(browser,query_server,wrong_identity=True)
    with pytest.raises(AssertionError,match='禁止修改'):
        page._open_edit_dialog('unit_id')
    assert not browser.execute_script('return !!window.saved')
    assert not browser.find_elements('css selector','.ant-modal-content')


def test_server_card_identity_does_not_match_a_renamed_prefix(browser):
    browser.get('about:blank')
    browser.execute_script('''document.body.innerHTML=`<main><div class="server-item"><div class="title" title="uiauto_name_updated（会议服务）">uiauto_name_updated（会议服务）</div></div></main>`;''')
    page=ServerListPage(driver=browser)
    page._created_server_names={'unit_id':'uiauto_name'}
    assert page._server_container('unit_id') is None
    page._created_server_names['unit_id']='uiauto_name_updated'
    assert page._server_container('unit_id') is not None


def test_server_negative_validation_cannot_pass_on_a_label_or_another_fields_error(browser):
    browser.get('about:blank')
    browser.execute_script('''document.body.innerHTML=`<div class="ant-modal-content">
      <div class="ant-form-item"><label>设备名称</label><input><div class="ant-form-item-explain-error">设备名称不能为空</div></div>
      <div id="bandwidth" class="ant-form-item"><label>最大网络带宽</label><input value="0"></div></div>`;''')
    page=ServerListPage(driver=browser)
    modal=browser.find_element('css selector','.ant-modal-content')
    assert not page._validation_evidence(modal,'最大网络带宽',timeout=0.3)
    browser.execute_script("setTimeout(()=>document.querySelector('#bandwidth').insertAdjacentHTML('beforeend','<div class=\"ant-form-item-explain-error\">必须大于0</div>'),200)")
    assert page._validation_evidence(modal,'最大网络带宽',timeout=1)=='必须大于0'


def test_server_clear_search_restores_category_mode_and_add_entry(browser,query_server):
    browser.get(query_server)
    browser.execute_script('''document.querySelector('main').innerHTML=`<div class="left-box-tree"><div class="sitem active">会议服务器</div></div>
      <input class="ant-input" placeholder="请输入搜索内容"><div class="add-server-item">+</div>
      <div class="server-item"><div class="title" title="MainDev（会议服务）">MainDev（会议服务）</div></div>`;
      const input=document.querySelector('main input');
      const render=name=>{const title=document.querySelector('.title');title.textContent=name+'（会议服务）';title.title=title.textContent};
      input.onkeyup=e=>{if(e.key!=='Enter')return;window.searchMode=true;document.querySelector('.add-server-item').style.display='none';
        const query=input.value;fetch('/serv/v1/conf/list').then(()=>render(query||'MainDev'))};
      document.querySelector('.sitem').onclick=()=>{window.searchMode=false;fetch('/serv/v1/conf/list').then(()=>{
        input.value='';render('MainDev');document.querySelector('.add-server-item').style.display='block';})};''')
    page=ServerListPage(driver=browser)
    page._query_server_cards('uiauto_exact')
    assert browser.execute_script('return window.searchMode===true')
    page._clear_search()
    assert browser.execute_script('return window.searchMode===false')
    assert browser.find_element('css selector','.add-server-item').is_displayed()
    assert browser.find_element('css selector','main input').get_attribute('value')==''


def test_server_normal_empty_category_is_ready_after_reset_without_an_empty_hint(browser,query_server):
    browser.get(query_server)
    browser.execute_script('''document.querySelector('main').innerHTML=`<div class="left-box-tree"><div class="sitem active">录制服务器</div></div>
      <input class="ant-input" placeholder="请输入搜索内容"><div class="add-server-item">+</div>`;
      document.querySelector('.sitem').onclick=()=>fetch('/serv/v1/conf/list');''')
    page=ServerListPage(driver=browser)
    page._clear_search()
    assert browser.find_element('css selector','.add-server-item').is_displayed()
    assert not browser.find_elements('css selector','.server-item')


def test_server_query_does_not_emit_an_intermediate_empty_search(browser,query_server):
    browser.get(query_server)
    browser.execute_script('''document.querySelector('main').innerHTML=`<input value="old_filter"><div class="server-item"><div class="title">MainDev（会议服务）</div></div>`;
      window.emptySearches=0;const input=document.querySelector('main input');
      const render=name=>{const title=document.querySelector('.title');title.textContent=name+'（会议服务）';title.title=title.textContent};
      input.oninput=()=>{if(input.value===''){window.emptySearches++;fetch('/serv/v1/conf/list').then(r=>r.text()).then(()=>setTimeout(()=>render('MainDev'),250))}};
      input.onkeyup=e=>{if(e.key==='Enter'){const value=input.value;fetch('/serv/v1/conf/list').then(r=>r.text()).then(()=>render(value))}};''')
    page=ServerListPage(driver=browser)
    page._query_server_cards('uiauto_exact')
    assert browser.execute_script('return window.emptySearches')==0
    assert browser.find_element('css selector','.title').text=='uiauto_exact（会议服务）'


def test_server_delete_waits_for_category_and_list_refresh_after_optimistic_removal(browser,query_server):
    browser.get(query_server)
    started=browser.execute_script('''const started=performance.now();
      fetch('/serv/v1/conf/delete').then(r=>r.text()).then(()=>{
        window.optimisticRemoval=true;
        setTimeout(()=>fetch('/serv/v1/conf/category').then(r=>r.text())
          .then(()=>fetch('/serv/v1/conf/list')).then(r=>r.text()).then(()=>window.refreshFinished=true),250);
      });return started;''')
    page=ServerListPage(driver=browser)
    assert page._wait_server_mutation_refresh(started,'/serv/v1/conf/delete',timeout=3)
    assert browser.execute_script('return window.optimisticRemoval&&window.refreshFinished')


def test_server_mutation_http_failure_is_not_retried_or_hidden(browser,query_server):
    browser.get(query_server)
    started=browser.execute_script("const start=performance.now();fetch('/failed-query');return start")
    with pytest.raises(AssertionError,match='HTTP 500'):
        ServerListPage(driver=browser)._wait_server_mutation_refresh(started,'/failed-query',timeout=2)
