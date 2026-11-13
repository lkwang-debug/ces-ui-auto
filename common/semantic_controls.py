"""Small UI-only helpers: table identity, action meaning and active layers."""
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from datetime import datetime
from common.ui_state import strict_wait


def exact_table_row(driver, header, value):
    return driver.execute_script(
        """
        const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
        const main=document.querySelector('main');if(!main)return null;
        const headers=[...main.querySelectorAll('thead tr')].find(e=>visible(e)&&e.querySelectorAll('th').length>1);
        const labels=[...(headers?.querySelectorAll('th')||[])].map(e=>(e.innerText||'').trim());
        const index=labels.indexOf(arguments[0]);if(index<0)return null;
        return [...main.querySelectorAll('tbody tr')].find(row=>visible(row)&&
          !row.classList.contains('ant-table-measure-row')&&
          (row.querySelectorAll('td')[index]?.innerText||'').trim()===arguments[1])||null;
        """, header, str(value),
    )


def action_locator(page, header, value, action):
    """Resolve only a labelled control or an icon with its real visible tooltip."""
    row = exact_table_row(page.driver, header, value)
    if row is None:
        raise AssertionError(f"操作前未找到目标行: {header}={value}")
    aliases = {'修改': {'修改', '编辑'}, '删除': {'删除'}, '排序': {'排序'}, '授权': {'管理', '授权', '授权用户'}}[action]
    known_actions={'修改','编辑','删除','排序','管理','授权','授权用户'}
    for control in row.find_elements(By.CSS_SELECTOR, 'button,a,img[title]'):
        if not control.is_displayed() or not control.is_enabled():
            continue
        texts = {(control.text or '').strip(), control.get_attribute('title') or '', control.get_attribute('aria-label') or ''}
        texts.update(e.get_attribute('title') or '' for e in control.find_elements(By.CSS_SELECTOR, '[title]'))
        matched = bool(texts & aliases)
        if not matched and texts & known_actions:
            continue
        if not matched and not (control.text or '').strip():
            ActionChains(page.driver).move_to_element(control).perform()
            matched = page.wait_until(lambda: any(
                e.is_displayed() and (e.text or '').strip() in aliases
                for e in page.driver.find_elements(By.CSS_SELECTOR, '.ant-tooltip-inner,[role=tooltip]')
            ), timeout=0.8, poll_frequency=0.1) is not False
        if matched:
            token = f"action_{time.time_ns()}"
            page.driver.execute_script("arguments[0].setAttribute('data-ces-action',arguments[1])", control, token)
            return By.CSS_SELECTOR, f'[data-ces-action="{token}"]'
    raise AssertionError(f"目标行缺少明确的{action}控件: {value}")


def cancel_transient_layers(browser):
    """Cancel UI layers only; never select a save/confirm/destructive action."""
    closed=[]
    for _ in range(6):
        state=browser.execute_script(
            """
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            const blocking=e=>{
              if(!visible(e)||getComputedStyle(e).pointerEvents==='none'||getComputedStyle(e).visibility==='hidden')return false;
              const r=e.getBoundingClientRect(),left=Math.max(0,r.left),right=Math.min(innerWidth,r.right),top=Math.max(0,r.top),bottom=Math.min(innerHeight,r.bottom);
              if(left>=right||top>=bottom)return false;
              const hit=document.elementFromPoint((left+right)/2,(top+bottom)/2);return hit===e||e.contains(hit);
            };
            const layers=[...document.querySelectorAll('.ant-modal-content,.ant-drawer-content,.layer_body')].filter(visible);
            const layer=layers.at(-1);if(!layer)return {open:false,blocking:
              [...document.querySelectorAll('.ant-modal-wrap,.ant-modal-mask,.ant-drawer-mask')].some(blocking)};
            const title=(layer.querySelector('.ant-modal-title')?.innerText||'未命名');
            const close=[...layer.querySelectorAll('button,.layer_close')].find(e=>visible(e)&&
              (e.matches('.ant-modal-close,.ant-drawer-close,.layer_close')||
               ['关闭','取消'].includes((e.innerText||'').replace(/\s/g,''))||
               ((e.innerText||'').replace(/\s/g,'')==='知道了'&&!layer.querySelector('input,select,textarea'))));
            if(!close)return {open:true,title};close.click();return {open:true,closing:true,title};
            """
        )
        if not state['open']:
            if state.get('blocking') and not strict_wait(lambda: browser.execute_script("""
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                return ![...document.querySelectorAll('.ant-modal-wrap,.ant-modal-mask,.ant-drawer-mask')].some(e=>{
                  if(!visible(e)||getComputedStyle(e).pointerEvents==='none'||getComputedStyle(e).visibility==='hidden')return false;
                  const r=e.getBoundingClientRect(),left=Math.max(0,r.left),right=Math.min(innerWidth,r.right),top=Math.max(0,r.top),bottom=Math.min(innerHeight,r.bottom);
                  if(left>=right||top>=bottom)return false;
                  const hit=document.elementFromPoint((left+right)/2,(top+bottom)/2);return hit===e||e.contains(hit);
                });
            """), timeout=5):
                raise AssertionError('弹窗内容已关闭，但遮罩仍阻挡后续用例')
            return closed
        if not state.get('closing'):
            raise AssertionError(f"用例结束后活动弹窗无法取消: {state['title']}")
        closed.append(state['title'])
        time.sleep(0.15)
    raise AssertionError('用例结束后仍有残留弹窗')


def set_date_field(page, placeholder, value):
    field=page.wait_visible((By.CSS_SELECTOR,f'main input[placeholder="{placeholder}"]'),timeout=5)
    if field is False:
        raise AssertionError(f'日期字段不存在: {placeholder}')
    field.click()
    if not field.get_property('readOnly'):
        entered=value+(' 23:59:59' if '结束' in placeholder else ' 00:00:00') if '时间' in placeholder else value
        field.send_keys(Keys.CONTROL,'a');field.send_keys(Keys.DELETE);field.send_keys(entered);field.send_keys(Keys.ENTER)
    else:
        stamp=datetime.strptime(value,'%Y-%m-%d')
        title=f'{stamp.year}年{stamp.month}月{stamp.day}日'
        day=page.wait_until(lambda: page.driver.execute_script(
            """
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            return [...document.querySelectorAll('.ant-picker-dropdown td[title],.ant-calendar-picker-container td[title]')]
              .find(e=>visible(e)&&[arguments[0],arguments[1]].includes(e.title))||null;
            """,value,title),timeout=3)
        if day is False:
            raise AssertionError(f'日期弹层未提供目标日期: {placeholder} / {value}')
        day.click()
    confirm=page.wait_until(lambda: page.driver.execute_script(
        """
        const panels=[...document.querySelectorAll('.ant-picker-dropdown,.ant-calendar-picker-container')]
          .filter(e=>e.offsetParent!==null&&!e.classList.contains('ant-picker-dropdown-hidden'));
        if(!panels.length)return {closed:true};
        return [...document.querySelectorAll('.ant-picker-dropdown button,.ant-calendar-picker-container button,.ant-calendar-picker-container a,.ant-calendar-picker-container [role=button]')]
          .find(e=>{if(e.offsetParent===null||e.disabled||e.getAttribute('aria-disabled')==='true'||e.classList.contains('ant-calendar-ok-btn-disabled')||(e.innerText||'').replace(/\s/g,'')!=='确定')return false;
            const r=e.getBoundingClientRect(),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
            return hit&&(e===hit||e.contains(hit));})||null;
        """),timeout=3)
    if confirm is False:
        raise AssertionError(f'日期确认控件未就绪: {placeholder}')
    if not isinstance(confirm,dict):
        confirm.click()
    assert page.wait_until(lambda: page.driver.execute_script(
        "return ![...document.querySelectorAll('.ant-picker-dropdown,.ant-calendar-picker-container')].some(e=>e.offsetParent!==null)"
    ),timeout=3), f'日期选择尚未提交: {placeholder}'
    def committed():
        current=page.find_visible_now((By.CSS_SELECTOR,f'main input[placeholder="{placeholder}"]'))
        return current is not False and (current.get_attribute('value') or '').startswith(value)
    assert page.wait_until(committed,timeout=3), f'日期未写入: {placeholder}'
