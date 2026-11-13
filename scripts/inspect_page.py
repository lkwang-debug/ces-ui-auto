# -*- coding: utf-8 -*-
"""Inspect visible controls on a CES page without changing saved data."""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

from conftest import chrome_options, resolve_chromedriver_path
from conf.conf import ConfigManager
from pages.Index_Page.index import LoginPage


SNAPSHOT_SCRIPT = """
const root = document.querySelector('main') || document.body;
const visible = element => element.offsetParent !== null;
const clean = value => String(value || '').replace(/\s+/g, ' ').trim();
return {
  url: location.href,
  text: clean(root.innerText).slice(0, 5000),
  buttons: [...root.querySelectorAll('button,a,[role=button]')].filter(visible)
    .map(element => ({text: clean(element.innerText), title: element.title || '', cls: String(element.className || '')})),
  inputs: [...root.querySelectorAll('input,textarea')].filter(visible)
    .map(element => ({type: element.type, name: element.name, placeholder: element.placeholder,
      maxlength: element.maxLength, value: element.type === 'password' ? '<masked>' : element.value,
      cls: String(element.className || '')})),
  labels: [...root.querySelectorAll('label,.ant-form-item-label')].filter(visible)
    .map(element => clean(element.innerText)).filter(Boolean),
  headers: [...root.querySelectorAll('th')].filter(visible).map(element => clean(element.innerText)),
  selects: [...root.querySelectorAll('.ant-select')].filter(visible)
    .map(element => clean(element.innerText))
};
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("route")
    parser.add_argument("--click", default="")
    parser.add_argument("--target", default="")
    parser.add_argument("--ensure-switch", default="")
    parser.add_argument("--scope", default="")
    parser.add_argument("--select-id", default="")
    parser.add_argument("--row-actions", action="store_true")
    parser.add_argument("--click-row-title", default="")
    parser.add_argument("--date-range", action="store_true")
    parser.add_argument("--meeting-settings", action="store_true")
    parser.add_argument("--row-action-index", type=int, default=-1)
    parser.add_argument("--modal-row-edit", action="store_true")
    parser.add_argument("--row-text", default="")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    browser = webdriver.Chrome(
        service=Service(resolve_chromedriver_path()),
        options=chrome_options(headless=True),
    )
    try:
        login = LoginPage(driver=browser)
        login.open_login_url()
        if not login.login_with_optional_captcha(
            ConfigManager.USERNAME, ConfigManager.PASSWORD
        ):
            raise RuntimeError(login.last_login_error or "管理员登录失败")
        browser.get(ConfigManager.HST_URL.rstrip("/") + "/" + args.route.lstrip("/"))
        time.sleep(2)
        print("PAGE=" + json.dumps(browser.execute_script(SNAPSHOT_SCRIPT), ensure_ascii=True))
        if args.select_id:
            options = browser.execute_script(
                """
                const input = document.getElementById(arguments[0]);
                const selector = input?.closest('.ant-select')?.querySelector('.ant-select-selector');
                if (!selector) return {clicked:false, options:[]};
                selector.click();
                const visible = item => item.offsetParent !== null;
                return {clicked:true, options:[...document.querySelectorAll('.ant-select-item-option')]
                  .filter(visible).map(item => ({text:(item.innerText||'').trim(), html:item.outerHTML}))};
                """,
                args.select_id,
            )
            time.sleep(0.5)
            print("SELECT=" + json.dumps(options, ensure_ascii=True))
        if args.row_actions:
            actions = browser.execute_script(
                """
                const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
                const rows = [...document.querySelectorAll('tbody tr')]
                  .filter(e => visible(e) && !e.classList.contains('ant-table-measure-row'));
                const row = rows.find(e => e.querySelector('td:last-child *')) || rows[0];
                return {lastCell:row?.querySelector('td:last-child')?.outerHTML?.slice(0,12000) || '',
                  rowTitles:rows.map(e => [...e.querySelectorAll('td:last-child [title]')].map(x => x.title)),
                  actions:[...(row?.querySelectorAll('button,a,[role=button],td:last-child svg,td:last-child i') || [])].map(e => ({
                  text:(e.innerText || '').replace(/\s+/g,' ').trim(), title:e.title || '',
                  aria:e.getAttribute('aria-label') || '', className:String(e.className || ''),
                  icons:[...e.querySelectorAll('svg,use,[aria-label]')].map(i => ({
                    tag:i.tagName, dataIcon:i.getAttribute('data-icon') || '',
                    aria:i.getAttribute('aria-label') || '',
                    href:i.getAttribute('href') || i.getAttribute('xlink:href') || ''
                  })), html:e.outerHTML.slice(0,2000)
                }))};
                """
            )
            print("ROW_ACTIONS=" + json.dumps(actions, ensure_ascii=True))
        if args.date_range:
            details = browser.execute_script(
                """
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const custom=[...document.querySelectorAll('main label,main span,main div')]
                  .find(e=>visible(e)&&(e.innerText||'').trim()==='自定义');
                if (custom) (custom.closest('label') || custom).click();
                const start=[...document.querySelectorAll("main input[placeholder='开始日期']")].find(visible);
                const icon=start?.closest('.ant-picker')?.querySelector('.ant-picker-suffix .anticon-calendar');
                if (icon) icon.click(); else if (start) start.click();
                return {custom:!!custom,start:!!start,radios:[...document.querySelectorAll('main input[type=radio]')].map(e=>({checked:e.checked,parent:e.closest('label')?.innerText||''})),startParent:start?.parentElement?.parentElement?.outerHTML?.slice(0,12000)||'',inputs:[...document.querySelectorAll('main input')]
                  .filter(visible).map(e=>({placeholder:e.placeholder,value:e.value,className:e.className})),
                  dropdowns:[...document.querySelectorAll('.ant-picker-dropdown,.ant-calendar-picker-container')]
                    .filter(visible).map(e=>({className:e.className,text:(e.innerText||'').replace(/\\s+/g,' ').trim(),
                      titles:[...e.querySelectorAll('td[title]')].map(x=>x.title).slice(0,100),
                      html:e.outerHTML.slice(0,20000)}))};
                """
            )
            time.sleep(0.5)
            print("DATE_RANGE=" + json.dumps(details, ensure_ascii=True))
        if args.meeting_settings:
            details = browser.execute_script(
                """
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const clean=v=>String(v||'').replace(/\s+/g,'').trim();
                const add=[...document.querySelectorAll('main button')].find(e=>visible(e)&&clean(e.innerText)==='新增');
                if (add) add.click();
                """
            )
            time.sleep(0.5)
            details = browser.execute_script(
                """
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const modal=[...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
                const header=modal&&[...modal.querySelectorAll('.item-header')]
                  .find(e=>(e.innerText||'').includes('会议室设置'));
                if (header) header.click();
                const form=header?.closest('form');
                return {opened:!!header,text:(form?.innerText||'').replace(/\s+/g,' ').trim(),
                  labels:[...(form?.querySelectorAll('label')||[])].map(e=>(e.innerText||'').replace(/\s+/g,' ').trim()),
                  inputs:[...(form?.querySelectorAll('input')||[])].map(e=>({placeholder:e.placeholder,type:e.type,value:e.value})),
                  switches:[...(form?.querySelectorAll('button[role=switch]')||[])].map(e=>({checked:e.getAttribute('aria-checked'),html:e.outerHTML.slice(0,500)})),
                  selects:[...(form?.querySelectorAll('.ant-select')||[])].map(e=>({text:(e.innerText||'').trim(),html:e.outerHTML.slice(0,1000)})),
                  html:form?.outerHTML.slice(0,20000)||''};
                """
            )
            time.sleep(0.5)
            print("MEETING_SETTINGS=" + json.dumps(details, ensure_ascii=True))
        if args.row_action_index >= 0:
            clicked = browser.execute_script(
                """
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const expected=arguments[1];
                const row=[...document.querySelectorAll('main tbody tr')]
                  .find(e=>visible(e)&&!e.classList.contains('ant-table-measure-row')&&
                    (!expected||(e.innerText||'').includes(expected)));
                const controls=[...(row?.querySelector('td:last-child')?.querySelectorAll('a,button')||[])].filter(visible);
                const target=controls[arguments[0]];
                if (!target) return {clicked:false,count:controls.length};
                target.click(); return {clicked:true,count:controls.length};
                """,
                args.row_action_index,
                args.row_text,
            )
            time.sleep(1)
            if args.modal_row_edit:
                browser.execute_script(
                    """
                    const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                    const modal=[...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
                    const row=modal&&[...modal.querySelectorAll('tbody tr')]
                      .find(e=>visible(e)&&!e.classList.contains('ant-table-measure-row'));
                    const button=row?.querySelector('td:last-child button'); if(button) button.click();
                    """
                )
                time.sleep(0.5)
            if args.confirm:
                browser.execute_script(
                    """
                    const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                    const button=[...document.querySelectorAll('.ant-modal-content button.ant-btn-primary')].find(visible);
                    if(button) button.click();
                    """
                )
                time.sleep(1)
            clicked["layers"] = browser.execute_script(
                """
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                return [...document.querySelectorAll('.ant-modal-content,.ant-drawer-content')].filter(visible)
                  .map(e=>({text:(e.innerText||'').replace(/\s+/g,' ').trim(),html:e.outerHTML.slice(0,16000)}));
                """
            )
            clicked["notices"] = browser.execute_script(
                """
                return [...document.querySelectorAll('.ant-message-notice-content,.ant-notification-notice')]
                  .filter(e=>e.offsetParent!==null).map(e=>(e.innerText||'').replace(/\s+/g,' ').trim());
                """
            )
            clicked["pageText"] = browser.execute_script(
                "return (document.querySelector('main')?.innerText||'').replace(/\\s+/g,' ').trim().slice(-5000)"
            )
            print("ROW_ACTION_CLICK=" + json.dumps(clicked, ensure_ascii=True))
        if args.click_row_title:
            layer = browser.execute_script(
                """
                const title=arguments[0]; const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const target=[...document.querySelectorAll(`[title="${title}"]`)].find(visible);
                if (!target) return {clicked:false}; target.click(); return {clicked:true};
                """, args.click_row_title,
            )
            time.sleep(1)
            layer["url"] = browser.current_url
            layer["handles"] = len(browser.window_handles)
            layer["bodyText"] = browser.execute_script("return (document.body.innerText || '').replace(/\\s+/g,' ').trim().slice(-5000)")
            layer["layers"] = browser.execute_script(
                """
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                return [...document.querySelectorAll('.ant-modal-content,.ant-drawer-content')].filter(visible)
                  .map(e=>({text:(e.innerText||'').replace(/\s+/g,' ').trim().slice(0,5000),html:e.outerHTML.slice(0,10000)}));
                """
            )
            print("ROW_CLICK=" + json.dumps(layer, ensure_ascii=True))
        if args.ensure_switch:
            from pages.ClientFeaturePage import ClientFeaturePage

            feature_name, index, value = args.ensure_switch.split(":", 2)
            page = ClientFeaturePage(driver=browser)
            result = page.ensure_switch(
                feature_name, int(index), value.strip().lower() in {"1", "true", "on"}
            )
            print("ENSURE_SWITCH=" + json.dumps({"success": result}, ensure_ascii=True))
        if args.scope:
            scope = browser.execute_script(
                """
                const expected=arguments[0];
                const row=[...document.querySelectorAll('main .feature-item')]
                  .find(item => (item.querySelector('.feature-title')?.innerText || '').trim() === expected);
                const button=row?.querySelector('.col-scope button');
                if (!button) return false; button.click(); return true;
                """,
                args.scope,
            )
            time.sleep(1)
            layers = browser.execute_script(
                """
                return [...document.querySelectorAll('body *')]
                  .filter(item => item.offsetParent !== null &&
                    /(modal|drawer|scope|user)/i.test(String(item.className || '')))
                  .slice(-40).map(item => ({tag:item.tagName,cls:String(item.className||''),
                    text:(item.innerText||'').replace(/\s+/g,' ').trim().slice(0,1000)}));
                """
            )
            print("SCOPE=" + json.dumps({"clicked": scope, "layers": layers}, ensure_ascii=True))
        if args.target:
            hierarchy = browser.execute_script(
                """
                const expected = arguments[0];
                const leaf = [...document.querySelectorAll('main *')]
                  .find(item => item.children.length === 0 && (item.innerText || '').trim() === expected);
                const result = [];
                let parent = leaf;
                for (let depth=0; parent && depth<10; depth++, parent=parent.parentElement) {
                  result.push({tag:parent.tagName,cls:String(parent.className||''),
                    switches:parent.querySelectorAll('.ant-switch').length,
                    buttons:parent.querySelectorAll('button').length,
                    html:depth === 4 ? parent.outerHTML.slice(0,12000) : '',
                    text:(parent.innerText||'').replace(/\s+/g,' ').trim().slice(0,500)});
                }
                return result;
                """,
                args.target,
            )
            print("TARGET=" + json.dumps(hierarchy, ensure_ascii=True))
        if args.click:
            clicked = browser.execute_script(
                """
                const expected = arguments[0];
                const clean = value => String(value || '').replace(/\s+/g, '').trim();
                const target = [...document.querySelectorAll('main button,main a,main [role=button]')]
                  .find(element => element.offsetParent !== null && clean(element.innerText).includes(clean(expected)));
                if (!target) return false;
                target.click(); return true;
                """,
                args.click,
            )
            time.sleep(1)
            modal = browser.execute_script(
                """
                const roots = [...document.querySelectorAll('.ant-modal-content,.ant-drawer-content')]
                  .filter(element => element.offsetParent !== null);
                const root = roots.at(-1);
                if (!root) return null;
                const clean = value => String(value || '').replace(/\s+/g, ' ').trim();
                return {html: root.outerHTML.slice(0, 30000), text: clean(root.innerText),
                  labels: [...root.querySelectorAll('label,.ant-form-item-label')].map(e => clean(e.innerText)),
                  inputs: [...root.querySelectorAll('input,textarea')].filter(e => e.offsetParent !== null)
                    .map(e => ({type:e.type,name:e.name,placeholder:e.placeholder,maxlength:e.maxLength,value:e.type==='password'?'<masked>':e.value})),
                  selects: [...root.querySelectorAll('.ant-select')].filter(e => e.offsetParent !== null).map(e => clean(e.innerText)),
                  buttons: [...root.querySelectorAll('button,a')].filter(e => e.offsetParent !== null).map(e => clean(e.innerText))};
                """
            )
            print(
                "CLICK="
                + json.dumps(
                    {"clicked": clicked, "page": browser.execute_script(SNAPSHOT_SCRIPT), "layer": modal},
                    ensure_ascii=True,
                )
            )
    finally:
        browser.quit()


if __name__ == "__main__":
    main()
