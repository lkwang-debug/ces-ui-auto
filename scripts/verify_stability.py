"""Compare immutable full runs; never synthesizes a green Allure result."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from common.stability import coverage_keys


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('runs',nargs='+',type=Path)
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--coverage-reference',type=Path,default=ROOT/'.stability'/'baseline-20261106'/'allure-results')
    args=parser.parse_args()
    records=[]
    for folder in args.runs:
        manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        summary=json.loads((folder/'allure-results'/'stability-summary.json').read_text(encoding='utf-8'))
        performance=json.loads((folder/'runtime'/'performance-summary.json').read_text(encoding='utf-8'))
        records.append({'folder':folder,'manifest':manifest,'summary':summary,'seconds':performance['pytest_wall_seconds'],
            'outcomes':coverage_keys(folder/'allure-results',manifest)})
    first=records[0]
    same_source=all(r['manifest']['code_sha256']==first['manifest']['code_sha256'] and not r['manifest']['code_changed_during_run'] for r in records)
    same_configuration=bool(first['manifest'].get('configuration_sha256')) and all(
        r['manifest'].get('configuration_sha256')==first['manifest']['configuration_sha256']
        and r['manifest'].get('browser_settings')==first['manifest'].get('browser_settings') for r in records)
    same_outcomes=all(r['outcomes']==first['outcomes'] for r in records)
    full_runs=all(r['manifest']['full'] and not r['manifest'].get('selection') and not r['manifest'].get('auth_baseline') for r in records)
    stable=len(records)>=3 and full_runs and same_source and same_configuration and same_outcomes and all(r['summary']['stability_pass'] and not r['summary'].get('cleanup_failure_count') for r in records)
    old=args.coverage_reference
    if not old.exists():parser.error('缺少覆盖参考报告，请通过 --coverage-reference 指定修改前原始 Allure 结果目录')
    original=coverage_keys(old,first['manifest'])
    removed=sorted(set(original)-set(first['outcomes']))
    new_skips=sorted(key for key,status in first['outcomes'].items() if status=='skipped' and original.get(key)!='skipped')
    complete=all(r['summary'].get('collected_nodes')==r['summary'].get('result_nodes')==len(r['outcomes']) and not r['summary']['statuses'].get('unknown') for r in records)
    evidence={'稳定性验收':stable and not removed and not new_skips and complete,'功能全部通过':all(r['summary'].get('functional_pass',False) for r in records),
        '必要前置齐备':all(r['summary'].get('preconditions_ready',False) for r in records),
        '最终代码三轮一致':same_source,'有效配置一致':same_configuration,'节点及结果一致':same_outcomes,
        '原有节点数':len(original),'最终节点数':len(first['outcomes']),'减少节点':removed,'新增跳过':new_skips,'收集节点全部产出结果':complete,
        '提速25%达标':None if not args.baseline else False,
        '性能验收状态':'未提供必要前置齐备的有效基线' if not args.baseline else '按完整有效基线比较',
        '每轮结果':[{'目录':str(r['folder']),'耗时秒':r['seconds'],'状态':r['summary']['statuses'],
            '清理证据数':r['summary'].get('cleanup_evidence_count',0),'主动保留记录数':r['summary'].get('intentional_retention_count',0)} for r in records]}
    if args.baseline:
        base=json.loads((args.baseline/'runtime'/'performance-summary.json').read_text(encoding='utf-8'))
        baseline_manifest=json.loads((args.baseline/'manifest.json').read_text(encoding='utf-8'))
        baseline_keys=coverage_keys(args.baseline/'allure-results',baseline_manifest)
        baseline_summary=json.loads((args.baseline/'allure-results'/'stability-summary.json').read_text(encoding='utf-8'))
        matched_observation=(set(baseline_keys)==set(first['outcomes']) and baseline_keys==first['outcomes']
            and baseline_manifest.get('full') and not baseline_manifest.get('selection')
            and not baseline_manifest.get('code_changed_during_run') and baseline_summary.get('stability_pass'))
        evidence['同节点同失败结果的观察提速（非正式验收）']=[round(1-r['seconds']/base['pytest_wall_seconds'],4) for r in records] if matched_observation else None
        comparable=(set(baseline_keys)==set(first['outcomes'])
            and not baseline_manifest.get('code_changed_during_run')
            and baseline_manifest.get('full') and not baseline_manifest.get('selection')
            and baseline_summary.get('preconditions_ready',False)
            and not any(g['kind'] in {'blocked','coverage','unclassified','automation'} for g in baseline_summary['root_causes'].values()))
        evidence['相同覆盖性能基线有效']=comparable
        evidence['性能对照方法']='必要前置齐备、相同覆盖的完整全量实测'
        evidence['提速比例']=[round(1-r['seconds']/base['pytest_wall_seconds'],4) for r in records] if comparable else None
        evidence['提速25%达标']=comparable and all(r['seconds']<=base['pytest_wall_seconds']*0.75 for r in records)
    evidence['完整验收']=evidence['稳定性验收'] and evidence['功能全部通过'] and evidence['必要前置齐备'] and evidence.get('提速25%达标',False)
    destination=ROOT/'.stability'/'acceptance.json'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    # Full assertion/operation audit remains reviewable beside the acceptance.
    audit=['# 用例、操作与断言核对','']
    for name,info in first['manifest']['functions'].items():
        audit.extend(['## '+name,'','操作：'+', '.join(info['operations']),''])
        audit.extend('- `'+x+'`' for x in info['assertions'])
        audit.append('')
    (ROOT/'.stability'/'coverage-audit.md').write_text('\n'.join(audit),encoding='utf-8')
    print(json.dumps(evidence,ensure_ascii=False,indent=2))
    return 0 if evidence['完整验收'] else 1


if __name__=='__main__':raise SystemExit(main())
