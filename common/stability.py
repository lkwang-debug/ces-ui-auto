"""Per-run evidence and root-cause summaries; never changes a test outcome."""
from __future__ import annotations

import ast
import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path


KINDS = {'product': '已确认产品校验问题', 'automation': '脚本错误',
    'precondition': '环境或固定数据前置', 'coverage': '菜单覆盖缺口',
    'pending': '需求待确认', 'unclassified': '待定位', 'blocked': '被前置阻断',
    'external_service':'外部服务或模型配置问题'}


def classify(nodeid, message, phase='call', user_debug=None, ai_debug=None):
    if 'AI临时模型清理失败:' in message:
        return 'automation','ai-cleanup'
    if '发现未登记的新菜单' in message:
        return 'coverage', 'menu-registration'
    if phase=='call' and 'test_server_invalid_value_validation' in nodeid and '业务规则待确认：最大在线用户数0已保存并回读，测试记录已清理' in message:
        return 'pending','server-online-zero-rule'
    if 'username_case_changed' in nodeid and '用户名大小写规则待确认：变更大小写后实际登录成功' in message:
        return 'pending', 'username-case-rule'
    if phase=='call' and 'valid_lifecycle' in nodeid and ai_debug:
        upstream=ai_debug.get('upstream',{})
        if not ai_debug.get('before',{}).get('matched') and not ai_debug.get('after',{}).get('matched') and (
            upstream.get('status',0)>=400 or upstream.get('transport_error')):
            return 'external_service','ai-upstream:'+ai_debug['key']
    if any(text in message for text in ('没有可下载的', '固定会议记录缺少', '前置条件：', 'Missing required test data')):
        return 'precondition', nodeid.split('[')[0]
    if phase=='call' and 'test_modify_user_' in nodeid and user_debug and any(
        text in message for text in ('修改字段出现前端校验错误','保存后没有可靠页面证据')
    ):
        errors = {**user_debug.get('validation_errors', {}), **user_debug.get('validation_errors_after_save', {})}
        if any('请输入正确的手机号' in text for text in errors.values()):
            return 'product', 'phone-validation'
        if 'middle_dot' in nodeid and any('请输入全角字符' in text for text in errors.values()):
            return 'product', 'nickname-middle-dot'
    if phase == 'setup':
        return 'blocked', nodeid.split('::')[0] + ':setup'
    if phase == 'teardown':
        return 'automation', nodeid.split('::')[0] + ':cleanup'
    return 'unclassified', nodeid.split('[')[0]


def source_manifest(root):
    root = Path(root)
    functions, digest = {}, hashlib.sha256()
    for folder in ('common','pages','testcases','conf','data','scripts','tests'):
        for path in sorted((root/folder).rglob('*')):
            if path.suffix not in {'.py','.json'} or '__pycache__' in path.parts:
                continue
            raw = path.read_bytes()
            digest.update(str(path.relative_to(root)).encode()+raw)
            if folder != 'testcases' or path.suffix != '.py':
                continue
            tree = ast.parse(raw.decode('utf-8-sig'))
            local={n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
            def assertions(node,seen=None):
                seen=set(seen or ())
                if node.name in seen:return []
                seen.add(node.name)
                result=[ast.unparse(x.test) for x in ast.walk(node) if isinstance(x,ast.Assert)]
                for call in ast.walk(node):
                    if isinstance(call,ast.Call) and isinstance(call.func,ast.Name) and call.func.id in local:
                        result.extend(assertions(local[call.func.id],seen))
                return sorted(set(result))
            def operations(node,seen=None):
                seen=set(seen or ())
                if node.name in seen:return []
                seen.add(node.name)
                result={ast.unparse(x.func) for x in ast.walk(node) if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute)}
                for call in ast.walk(node):
                    if isinstance(call,ast.Call) and isinstance(call.func,ast.Name) and call.func.id in local:
                        result.update(operations(local[call.func.id],seen))
                return sorted(result)
            for node in ast.walk(tree):
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith('test_'):
                    key = str(path.relative_to(root)).replace('\\','/')+'::'+node.name
                    functions[key] = {'assertions': assertions(node), 'parameters':[x.arg for x in node.args.args],
                        'operations': operations(node)}
    for filename in ('conftest.py','run.py','pytest.ini','requirements.txt'):
        digest.update(filename.encode()+(root/filename).read_bytes())
    # Fingerprint the original bytes, but never export credential literals
    # copied from test assertions into manifests or the coverage checklist.
    from common.privacy import redact
    return {'code_sha256': digest.hexdigest(), 'functions': redact(functions)}


def summarize(results_dir, report_dir=None):
    results_dir = Path(results_dir)
    records = []
    for path in results_dir.glob('*-result.json'):
        case = json.loads(path.read_text(encoding='utf-8'))
        labels = {x['name']:x['value'] for x in case.get('labels', [])}
        records.append({'name':case['name'],'test':case.get('fullName'), 'status':case['status'],
            'kind':labels.get('failure_origin'), 'root':labels.get('root_cause'),'history':case.get('historyId'),'phase':labels.get('failure_phase')})
    groups = {}
    for case in records:
        if case['status'] not in {'failed','broken'}:
            continue
        key = case['root'] or case['test']
        group = groups.setdefault(key, {'kind':case['kind'] or 'unclassified','cases':[],'affected_nodes':[]})
        group['cases'].append(case['name'])
        group['affected_nodes'].append({'name':case['name'],'history':case['history']})
    statuses=dict(Counter(c['status'] for c in records))
    cleanup=[]
    retained=[]
    for path in list(results_dir.glob('*-result.json'))+list(results_dir.glob('*-container.json')):
        data=json.loads(path.read_text(encoding='utf-8'))
        def collect(node):
            for attachment in node.get('attachments',[]):
                if attachment['name']=='执行后保留的数据':
                    retained.append({'case':data.get('name','fixture'),'source':attachment['source']})
                if any(word in attachment['name'] for word in ('清理','恢复状态','恢复原','未清理')):
                    cleanup.append({'case':data.get('name','fixture'),'name':attachment['name'],'source':attachment['source']})
            for key in ('steps','befores','afters'):
                for child in node.get(key,[]):collect(child)
        collect(data)
    (results_dir/'cleanup-evidence.json').write_text(json.dumps(cleanup,ensure_ascii=False,indent=2),encoding='utf-8')
    (results_dir/'intentional-retained-data.json').write_text(json.dumps(retained,ensure_ascii=False,indent=2),encoding='utf-8')
    collection=results_dir.parent/'runtime'/'collection.json'
    summary = {'statuses':statuses, 'root_causes':groups,'cleanup_evidence_count':len(cleanup),
        'cleanup_failure_count':sum(c['status'] in {'failed','broken'} and (c['phase']=='teardown' or c['root']=='ai-cleanup') for c in records),
        'intentional_retention_count':len(retained),
        'collected_nodes':len(json.loads(collection.read_text(encoding='utf-8'))) if collection.exists() else None,
        'result_nodes':len(records),
        'functional_pass':bool(records) and not any(statuses.get(s,0) for s in ('failed','broken')),
        'preconditions_ready':bool(records) and not any(g['kind'] in {'precondition','blocked','external_service'} for g in groups.values()),
        'stability_pass':bool(records) and not any(g['kind'] in {'automation','unclassified','blocked','coverage'} for g in groups.values())}
    (results_dir/'stability-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    if report_dir:
        report_dir = Path(report_dir)
        links={}
        for path in (report_dir/'data'/'test-cases').glob('*.json'):
            case=json.loads(path.read_text(encoding='utf-8'))
            links[case.get('historyId')]=case['uid']
        def affected(group):
            return '；'.join(f'<a href="index.html#testresult/{links[node["history"]]}">{html.escape(node["name"])}</a>'
                if node['history'] in links else html.escape(node['name']) for node in group['affected_nodes'])
        rows = ''.join(f"<tr><td>{html.escape(KINDS.get(g['kind'],g['kind']))}</td><td>{html.escape(key)}</td><td>{len(g['cases'])}</td><td>{affected(g)}</td></tr>" for key,g in groups.items())
        page = '<!doctype html><meta charset="utf-8"><title>稳定性与根因汇总</title><style>body{font:16px sans-serif;margin:32px}td,th{padding:12px;border:1px solid #ddd}table{border-collapse:collapse}a{color:#1677ff}</style>'
        page += '<h1>稳定性与根因汇总</h1><p>原始结果未合并、未改判。产品/前置/待确认失败不等同于整体验收通过。</p>'
        page += '<p>'+html.escape(str(summary['statuses']))+'</p><p><a href="index.html">打开完整 Allure 报告</a></p><table><tr><th>分类</th><th>根因</th><th>影响节点</th><th>用例</th></tr>'+rows+'</table>'
        (report_dir/'stability-summary.html').write_text(page,encoding='utf-8')
        (report_dir/'stability-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    return summary


def coverage_keys(results_dir,manifest):
    from common.privacy import redact
    keys={}
    for path in Path(results_dir).glob('*-result.json'):
        case=json.loads(path.read_text(encoding='utf-8'))
        full=case.get('fullName','')
        if '#' not in full:continue
        module,function=full.split('#',1)
        key=module.replace('.','/')+'.py::'+function
        parameters=manifest['functions'].get(key,{}).get('parameters',[])
        values=[]
        for parameter in case.get('parameters',[]):
            if parameter['name'] not in parameters:continue
            value=parameter['value']
            try:value=ast.literal_eval(value)
            except (ValueError,SyntaxError):pass
            values.append((parameter['name'],redact(value)))
        encoded=json.dumps(sorted(values),ensure_ascii=False,sort_keys=True,default=str)
        keys[full+'|'+encoded]=case['status']
    return keys
