# -*- coding: utf-8 -*-
import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
ALLURE_RESULTS = PROJECT_ROOT / "allure-results"
ALLURE_REPORT = PROJECT_ROOT / "allure-report"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the CES UI test suite and open the Allure report."
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run Chrome with a visible window (default).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chrome without opening a visible window.",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Generate the Allure report without opening it.",
    )
    parser.add_argument(
        "--include-destructive",
        action="store_true",
        help="Include high-risk recovery and service lifecycle tests.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Include extended boundary matrices and long-running regression checks.",
    )
    parser.add_argument('--shuffle-seed', type=int, help='Run the same collected nodes in a reproducible shuffled order.')
    args, pytest_args = parser.parse_known_args()
    args.pytest_args = pytest_args
    return args


def find_allure():
    allure = shutil.which("allure")
    if allure:
        return allure
    raise FileNotFoundError(
        "Allure Commandline was not found. Install it and add its bin directory to PATH."
    )


def reset_allure_results():
    """Ensure the generated report contains results from this run only."""
    if ALLURE_RESULTS.exists():
        shutil.rmtree(ALLURE_RESULTS)
    ALLURE_RESULTS.mkdir(parents=True, exist_ok=True)


def _execute(args):
    from conf.conf import ConfigManager
    from common.stability import source_manifest, summarize
    from common.privacy import redact,redact_report_files
    allure = find_allure()
    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]
    run_root = PROJECT_ROOT/'reports'/'runs'/run_id
    run_results, run_report = run_root/'allure-results', run_root/'allure-report'
    run_results.mkdir(parents=True)
    manifest = source_manifest(PROJECT_ROOT)
    import hashlib
    effective={key:value for key,value in vars(ConfigManager).items() if key.isupper()}
    manifest['configuration_sha256']=hashlib.sha256(json.dumps(effective,sort_keys=True,default=lambda v:sorted(v) if isinstance(v,set) else str(v)).encode()).hexdigest()
    manifest.update({'run_id':run_id,'target':ConfigManager.HST_URL,'full':args.full,'shuffle_seed':args.shuffle_seed,
        'browser_settings':{'headless':args.headless,'window_size':os.getenv('UIAUTO_WINDOW_SIZE','1920,1080')},
        'selection':args.pytest_args})
    (run_root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'RUN_ID: {run_id}', flush=True)
    from common.product_profile import detect_build_profile, ProfileDetectionError
    try:
        profile = detect_build_profile(ConfigManager.HST_URL)
    except ProfileDetectionError as exc:
        failure = {'status':'blocked','stage':'前端版本识别','message':redact(str(exc)),
                   'tests_started':False,'target':ConfigManager.HST_URL}
        (run_root/'preflight-error.json').write_text(json.dumps(failure,ensure_ascii=False,indent=2),encoding='utf-8')
        print(failure['message'],file=sys.stderr,flush=True)
        return 2
    (run_root/'preflight.json').write_text(json.dumps({'profile':profile,
        'https_verify_certificate':ConfigManager.HTTPS_VERIFY_CERTIFICATE},ensure_ascii=False,indent=2),encoding='utf-8')
    env = os.environ.copy()
    env.update({'UIAUTO_HEADLESS':'1' if args.headless else '0', 'PYTHONIOENCODING':'utf-8',
        'UIAUTO_RUN_ID':run_id, 'UIAUTO_RUNTIME_DIR':str(run_root/'runtime'),
        'UIAUTO_SCREENSHOT_DIR':str(run_root/'screenshots'), 'UIAUTO_DOWNLOAD_DIR':str(run_root/'downloads'),
        'UIAUTO_IMPORT_TEMPLATE_DIR':str(run_root/'imports')})
    if args.shuffle_seed is not None:
        env['UIAUTO_SHUFFLE_SEED'] = str(args.shuffle_seed)
    env.setdefault('UIAUTO_WINDOW_SIZE','1920,1080')
    command = [sys.executable,'-m','pytest']
    if not args.include_destructive:
        command += ['-m','not destructive' if args.full else 'not destructive and not extended']
    command += args.pytest_args or ['-q','--disable-warnings']
    command += ['--alluredir='+str(run_results)]
    print(f'前端版本类型: {profile}\nRunning tests with: {sys.executable}',flush=True)
    with (run_root/'pytest-output.log').open('w',encoding='utf-8') as log:
        process = subprocess.Popen(command,cwd=PROJECT_ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
        for line in process.stdout:
            line=redact(line)
            log.write(line);log.flush()
            print(line,end='',flush=True)
        code = process.wait()
    masked=redact_report_files(run_results)
    print(f'报告脱敏完成：{masked} 个文本文件，测试状态保留。',flush=True)
    performance = run_root/'runtime'/'performance-summary.json'
    if performance.exists():
        elapsed=json.loads(performance.read_text(encoding='utf-8'))['pytest_wall_seconds']
        scope='全量' if args.full and not args.pytest_args else '默认回归' if not args.pytest_args else '专项'
        print(f'PYTEST耗时（{scope}）: {elapsed:.1f}s'+('；超过全量告警线' if scope=='全量' and elapsed>ConfigManager.FULL_PERFORMANCE_BUDGET_SECONDS else ''),flush=True)
        (PROJECT_ROOT/'.runtime').mkdir(exist_ok=True)
        shutil.copy2(performance,PROJECT_ROOT/'.runtime'/'performance-summary.json')
    summary=summarize(run_results)
    manifest['end_code_sha256']=source_manifest(PROJECT_ROOT)['code_sha256']
    manifest['code_changed_during_run']=manifest['end_code_sha256']!=manifest['code_sha256']
    (run_root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('STABILITY_SUMMARY: '+json.dumps(summary['statuses'],ensure_ascii=False),flush=True)
    (run_results/'executor.json').write_text(json.dumps({'name':'CES UI','type':'pytest','buildName':run_id,'buildUrl':'stability-summary.html'},ensure_ascii=False),encoding='utf-8')
    generated=subprocess.run([allure,'generate',str(run_results),'-o',str(run_report),'--clean'],cwd=PROJECT_ROOT,env=env)
    if generated.returncode:
        return generated.returncode
    summarize(run_results,run_report)
    # Latest paths stay compatible; immutable run folders retain each complete
    # run instead of merging successful reruns into an earlier failed report.
    for source,target in ((run_results,ALLURE_RESULTS),(run_report,ALLURE_REPORT)):
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source,target)
    (PROJECT_ROOT/'reports'/'latest.json').write_text(json.dumps({'run_id':run_id,'path':str(run_root)},ensure_ascii=False),encoding='utf-8')
    print(f'Allure report generated: {run_report}',flush=True)
    if not args.no_open:
        subprocess.Popen([allure,'open',str(run_report)],cwd=PROJECT_ROOT,env=env)
    return code


def main():
    args = parse_args()
    # Allow `python run.py` from any Python installation. Re-enter with the
    # project environment so Selenium and pytest use the pinned dependencies.
    local_python = PROJECT_ROOT / ".venv-local" / "Scripts" / "python.exe"
    if (
        local_python.exists()
        and not os.environ.get("UIAUTO_RUNNER_REENTERED")
        and Path(sys.executable).resolve() != local_python.resolve()
    ):
        child_env = os.environ.copy()
        child_env["UIAUTO_RUNNER_REENTERED"] = "1"
        return subprocess.run(
            [str(local_python), str(PROJECT_ROOT / "run.py"), *sys.argv[1:]],
            cwd=PROJECT_ROOT,
            env=child_env,
        ).returncode
    from conf.conf import ConfigManager
    from common.run_lock import RunLock
    try:
        with RunLock(ConfigManager.HST_URL,ConfigManager.USERNAME):
            return _execute(args)
    except (RuntimeError,FileNotFoundError) as exc:
        print(str(exc),file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
