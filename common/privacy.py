"""Mask configured credentials without changing the values used by tests."""
from conf.conf import ConfigManager
from pathlib import Path
from contextlib import contextmanager


def redact(value):
    secrets=[]
    for name, item in vars(ConfigManager).items():
        if ('PASSWORD' in name or 'API_KEY' in name) and isinstance(item,str) and item:
            secrets.append(item)
    secrets.append(ConfigManager.EMAIL_INFO.get('password',''))
    def text(item):
        for secret in sorted(set(secrets),key=len,reverse=True):
            if secret:
                item=item.replace(secret,'[已脱敏]')
        return item
    if isinstance(value,str):
        return text(value)
    if isinstance(value,dict):
        return {k:redact(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [redact(v) for v in value]
    return value


def redact_report_files(folder):
    """Mask credentials in plugin-generated traces, preserving test outcomes."""
    changed=0
    for path in Path(folder).rglob('*'):
        if not path.is_file() or path.suffix not in {'.json','.txt','.log'}:
            continue
        original=path.read_text(encoding='utf-8',errors='replace')
        safe=redact(original)
        if safe!=original:
            path.write_text(safe,encoding='utf-8')
            changed+=1
    return changed


@contextmanager
def masked_screenshot(browser):
    """Visual masks only; never read passwords or change form values/events."""
    browser.execute_script(
        r"""
        const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
        const inputs=[...document.querySelectorAll('input,textarea')].filter(e=>visible(e)&&
          (e.type==='password'||/password|apikey|api.key|secret|token|密码|密钥/i.test([e.id,e.name,e.placeholder].join(' '))));
        const secretDialogs=[...document.querySelectorAll('.ant-modal-content,.layer_body')]
          .filter(e=>visible(e)&&/\bSecret\b/.test(e.innerText||''));
        for(const target of [...inputs,...secretDialogs]){
          const r=target.getBoundingClientRect(),mask=document.createElement('div');
          mask.setAttribute('data-ces-secret-mask','true');mask.innerText='[已脱敏]';
          Object.assign(mask.style,{position:'fixed',left:r.x+'px',top:r.y+'px',width:r.width+'px',height:r.height+'px',
            background:'#fff',color:'#777',zIndex:'2147483647',pointerEvents:'none',font:'14px sans-serif',display:'grid',placeItems:'center'});
          document.body.appendChild(mask);
        }
        """
    )
    try:
        yield
    finally:
        browser.execute_script("document.querySelectorAll('[data-ces-secret-mask]').forEach(e=>e.remove())")
