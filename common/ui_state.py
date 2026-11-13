"""DOM state and completed-query waits for non-server page objects."""

import time
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException


def strict_wait(condition, timeout=10, poll_frequency=0.1):
    """Retry render transients only; programming/selector errors fail immediately."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            value = condition()
            if value:
                return value
        except (NoSuchElementException, StaleElementReferenceException):
            pass
        if time.monotonic() >= deadline:
            return False
        time.sleep(min(poll_frequency, max(0, deadline-time.monotonic())))


def wait_control_unobscured(page, target, timeout=5, poll_frequency=0.1):
    """Wait for a fresh enabled control to receive a real pointer click.

    A visible input can still sit behind a closing modal wrapper. Do not
    bypass that wrapper with a JavaScript click or shorten the operation.
    """
    def ready():
        field = target() if callable(target) else page.find_visible_now(target)
        if field is None or field is False or not field.is_displayed() or not field.is_enabled():
            return False
        hit = page.driver.execute_script("""
            const field=arguments[0];let r=field.getBoundingClientRect();
            if(r.x+r.width/2<0 || r.x+r.width/2>innerWidth || r.y+r.height/2<0 || r.y+r.height/2>innerHeight){
                field.scrollIntoView({block:'center',inline:'nearest'});r=field.getBoundingClientRect();
            }
            const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
            return hit===field || field.contains(hit);
        """, field)
        return field if hit else False
    return strict_wait(ready, timeout=timeout, poll_frequency=poll_frequency)


def wait_stable_state(page, snapshot, timeout=10, stable_for=0.3):
    """Require a valid state to remain stable through a render transition."""
    previous = None
    since = None

    def ready():
        nonlocal previous, since
        current = snapshot()
        if not current:
            previous, since = None, None
            return False
        if current != previous:
            previous, since = current, time.monotonic()
            return False
        return current if time.monotonic() - since >= stable_for else False

    return strict_wait(ready, timeout=timeout, poll_frequency=0.1)


def click_toolbar_search(driver, input_element):
    """Locate the search action beside its input, including legacy toolbars."""
    return bool(driver.execute_script(
        r"""
        const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
        let scope = arguments[0];
        for (let depth = 0; depth < 6 && scope; depth += 1) {
          scope = scope.parentElement;
          const buttons = [...(scope?.querySelectorAll('button') || [])].filter(visible);
          const search = buttons.find(button =>
            button.matches('.ant-input-search-button') ||
            button.querySelector('.anticon-search,[data-icon="search"],[aria-label="search"]'));
          if (search) { search.click(); return true; }
          if (buttons.length === 1 && !buttons[0].innerText.trim()) {
            buttons[0].click(); return true;
          }
          if (scope?.matches('main')) break;
        }
        return false;
        """,
        input_element,
    ))


def wait_query_finished(page, started, timeout=10, request_path=None):
    """Wait for a newly triggered request and a stable completed table render.

    A pre-existing empty state or unchanged table alone cannot satisfy this
    wait, which protects negative query and cleanup assertions.
    """
    def snapshot():
        response = page.driver.execute_script(
            """
            const entry=performance.getEntriesByType('resource').filter(item =>
              item.startTime >= arguments[0] && item.responseEnd > 0 &&
              (!arguments[1] || new URL(item.name,location.href).pathname === arguments[1]) &&
              ['fetch','xmlhttprequest'].includes(item.initiatorType)).at(-1);
            const route=location.hash.split('?')[0].replace(/\/$/,'');
            return {completed:!!entry,status:entry?.responseStatus??null,
              path:entry?new URL(entry.name,location.href).pathname:'',
              logged_out:['#/ui/login','#/login'].includes(route),main:!!document.querySelector('main')};
            """,
            started,
            request_path,
        )
        if isinstance(response,dict) and response.get('logged_out'):
            raise AssertionError('查询期间返回登录页，禁止据此判定数据不存在')
        if isinstance(response,dict) and (response.get('status') or 0)>=400:
            raise AssertionError(f"查询接口HTTP {response['status']}: {response['path']}，禁止使用旧表格判定结果")
        if not isinstance(response,dict) or not response.get('completed') or not response.get('main') or not page.wait_loading_finished(timeout=0.2):
            return False
        return page.table_snapshot()

    return wait_stable_state(page, snapshot, timeout=timeout) is not False


def wait_page_layout(page,route,header_groups,tree_selector,timeout=12,allow_cached=False):
    """Reuse structural readiness only, never rows, query results or mutations.

    The cache expires on a new document/component or changed headers/tree.
    Every query and save keeps its own operation-completion waits.
    """
    def snapshot():
        return page.driver.execute_script(
            r"""
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            const main=document.querySelector('main');
            if(!main||!location.href.includes(arguments[0]))return null;
            const headers=[...main.querySelectorAll('th')].filter(visible).map(e=>(e.innerText||'').trim());
            if(!arguments[1].every(group=>group.some(label=>headers.some(text=>text.includes(label)))))return null;
            const nodes=[...main.querySelectorAll(arguments[2])].filter(visible).map(e=>(e.innerText||'').trim()).filter(Boolean);
            if(!nodes.length)return null;
            if([...document.querySelectorAll('.ant-spin-spinning,.ant-table-loading,.ant-skeleton-active,.ant-modal-confirm-loading,[aria-busy="true"]')].some(visible))return null;
            const component=main.querySelector('.ant-table-wrapper')||main.querySelector('table');
            if(!component)return null;
            window.__cesLayoutIds ||= new WeakMap();window.__cesLayoutSequence ||= 0;
            if(!window.__cesLayoutIds.has(component))window.__cesLayoutIds.set(component,++window.__cesLayoutSequence);
            return {identity:[performance.timeOrigin,location.href,window.__cesLayoutIds.get(component)],
              layout:JSON.stringify({headers,nodes}),
              table:JSON.stringify([...main.querySelectorAll('tbody tr')].filter(visible).map(e=>(e.innerText||'').trim()))};
            """,route,header_groups,tree_selector,
        )
    state=snapshot()
    def identity(value):return (value['identity'],value['layout'])
    if allow_cached and state and getattr(page,'_verified_layout',None)==identity(state):
        return True
    state=wait_stable_state(page,snapshot,timeout=timeout)
    if state is False:return False
    page._verified_layout=identity(state)
    return True
