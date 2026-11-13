# -*- coding:utf-8 -*-
import inspect
import json
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone

import allure
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

from conf.conf import ConfigManager


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.getenv('UIAUTO_SCREENSHOT_DIR', os.path.join(PROJECT_ROOT, "screenshots"))
RUNTIME_DIR = os.getenv('UIAUTO_RUNTIME_DIR', os.path.join(PROJECT_ROOT, ".runtime"))
DEFAULT_PROFILE_ROOT = os.path.join("D:\\tmp", "uiauto_profiles")
PERFORMANCE_REPORTS = {}
PERFORMANCE_STARTED_AT = 0.0


def _is_truthy(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_filename(value, max_length=160):
    safe_value = re.sub(r'[\\\\/:*?"<>|\s]+', "_", str(value)).strip("._")
    if not safe_value:
        safe_value = "test_failure"
    return safe_value[:max_length]


def _redact_case_failure(item,message):
    from common.privacy import redact
    safe=redact(message)
    if os.path.basename(str(item.fspath))!='test_030_personal_profile.py':return safe
    module=item.module
    data=getattr(module,'PASSWORD_DATA',{})
    candidates=[]
    for section,cases in data.items():
        for case in cases.values():
            if not isinstance(case,dict):continue
            if case.get('password'):candidates.append(case['password'])
            if section=='invalid':
                try:candidates.extend(module._invalid_values(case,module.NORMAL_PASSWORD))
                except (KeyError,AttributeError,TypeError):pass
    for value in sorted({v for v in candidates if isinstance(v,str) and v},key=len,reverse=True):
        safe=safe.replace(value,'[已脱敏]')
    return safe


def _reset_screenshot_dir():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    for entry in os.scandir(SCREENSHOT_DIR):
        path = entry.path
        try:
            if entry.is_dir(follow_symlinks=False):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.remove(path)
        except FileNotFoundError:
            continue


def _reset_runtime_dir():
    os.makedirs(RUNTIME_DIR, exist_ok=True)
    # Each runner invocation owns a unique directory. Never remove live report
    # logs, other runs' downloads or browser profiles during initialization.


def _profile_root_candidates():
    candidates = []
    env_root = os.getenv("UIAUTO_PROFILE_ROOT")
    if env_root:
        candidates.append(os.path.abspath(env_root))
    candidates.extend(
        [
            DEFAULT_PROFILE_ROOT,
            os.path.join(tempfile.gettempdir(), "uiauto_profiles"),
            os.path.join(RUNTIME_DIR, "profiles"),
        ]
    )

    unique_candidates = []
    for path in candidates:
        if path and path not in unique_candidates:
            unique_candidates.append(path)
    return unique_candidates


def _save_failure_screenshot(driver, item):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{timestamp}_{_safe_filename(item.nodeid)}.png"
    file_path = os.path.join(SCREENSHOT_DIR, file_name)
    driver.save_screenshot(file_path)
    return file_path


def chrome_options(headless=True, profile_dir=None):
    options = webdriver.ChromeOptions()

    # Performance and compatibility flags.
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-browser-side-navigation")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--remote-debugging-port=0")
    options.accept_insecure_certs = not ConfigManager.HTTPS_VERIFY_CERTIFICATE
    if not ConfigManager.HTTPS_VERIFY_CERTIFICATE:
        options.add_argument("--ignore-certificate-errors")
    # Chrome blocks blob/Excel downloads from plain HTTP intranet origins.
    # Trust only the explicitly configured test origin, never all HTTP sites.
    from urllib.parse import urlsplit
    test_origin = urlsplit(ConfigManager.HST_URL)
    if test_origin.scheme == "http" and test_origin.netloc:
        options.add_argument(
            f"--unsafely-treat-insecure-origin-as-secure=http://{test_origin.netloc}"
        )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    logging_preferences = {"browser": "ALL"}
    if _is_truthy(os.getenv("UIAUTO_NETWORK_DIAGNOSTICS"), default=True):
        logging_preferences["performance"] = "ALL"
    options.set_capability("goog:loggingPrefs", logging_preferences)
    download_dir = os.getenv(
        "UIAUTO_DOWNLOAD_DIR", os.path.join(RUNTIME_DIR, "downloads")
    )
    os.makedirs(download_dir, exist_ok=True)
    options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": os.path.abspath(download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "profile.default_content_setting_values.automatic_downloads": 1,
            "safebrowsing.enabled": True,
        },
    )

    window_size = os.getenv("UIAUTO_WINDOW_SIZE", "1920,1080")
    options.add_argument(f"--window-size={window_size}")

    if profile_dir:
        options.add_argument(f"--user-data-dir={profile_dir}")

    if headless:
        options.add_argument("--headless=new")

    return options


def resolve_chromedriver_path():
    """
    Resolve chromedriver path in a deterministic order:
    1) CHROMEDRIVER_PATH env var
    2) ConfigManager.CHROMEDRIVER_PATH in conf/conf.py
    3) project-local .venv-local driver (kept with the tested Chrome version)
    4) same directory as current Python executable
    5) PATH lookup via shutil.which
    6) None (let Selenium Manager resolve)
    """
    env_path = os.getenv("CHROMEDRIVER_PATH")
    if env_path:
        env_path = os.path.abspath(env_path)
        if os.path.exists(env_path):
            return env_path

    configured_path = os.path.abspath(ConfigManager.CHROMEDRIVER_PATH)
    if os.path.exists(configured_path):
        return configured_path

    project_driver = os.path.join(
        PROJECT_ROOT, ".venv-local", "Scripts", "chromedriver.exe"
    )
    if os.path.exists(project_driver):
        return project_driver

    python_dir = os.path.dirname(sys.executable)
    local_driver = os.path.join(python_dir, "chromedriver.exe")
    if os.path.exists(local_driver):
        return local_driver

    path_driver = shutil.which("chromedriver")
    if path_driver and os.path.exists(path_driver):
        return os.path.abspath(path_driver)

    return None


def pytest_sessionstart(session):
    from common.product_profile import detect_build_profile, ProfileDetectionError
    try:
        detect_build_profile(ConfigManager.HST_URL)
    except ProfileDetectionError as exc:
        raise pytest.UsageError(str(exc)) from exc
    global PERFORMANCE_STARTED_AT
    PERFORMANCE_REPORTS.clear()
    PERFORMANCE_STARTED_AT = time.perf_counter()
    _reset_screenshot_dir()
    _reset_runtime_dir()


def pytest_collection_finish(session):
    os.makedirs(RUNTIME_DIR,exist_ok=True)
    with open(os.path.join(RUNTIME_DIR,'collection.json'),'w',encoding='utf-8') as file:
        json.dump([item.nodeid for item in session.items],file,ensure_ascii=False,indent=2)


def pytest_runtest_logreport(report):
    phases = PERFORMANCE_REPORTS.setdefault(
        report.nodeid,
        {"setup": 0.0, "call": 0.0, "teardown": 0.0, "status": "unknown"},
    )
    phases[report.when] = round(float(report.duration), 6)
    if report.failed:
        phases['status'] = 'failed'
        phases['failed_phase'] = report.when
    elif phases['status'] != 'failed' and (report.when == 'call' or report.skipped):
        phases["status"] = (
            "passed" if report.passed else "skipped" if report.skipped else "failed"
        )


def _performance_summary():
    from common.operation_metrics import OPERATIONS
    elapsed = max(0.0, time.perf_counter() - PERFORMANCE_STARTED_AT)
    cases = []
    modules = {}
    for nodeid, phases in PERFORMANCE_REPORTS.items():
        total = sum(float(phases.get(name, 0.0)) for name in ("setup", "call", "teardown"))
        case = {"nodeid": nodeid, **phases, "total": round(total, 6)}
        cases.append(case)
        module = nodeid.split("::", 1)[0]
        bucket = modules.setdefault(
            module,
            {"total": 0.0, "setup": 0.0, "call": 0.0, "teardown": 0.0, "count": 0},
        )
        bucket["count"] += 1
        bucket["total"] += total
        for phase in ("setup", "call", "teardown"):
            bucket[phase] += float(phases.get(phase, 0.0))
    for values in modules.values():
        for key in ("total", "setup", "call", "teardown"):
            values[key] = round(values[key], 6)
    statuses = {}
    for case in cases:
        statuses[case["status"]] = statuses.get(case["status"], 0) + 1
    return {
        "pytest_wall_seconds": round(elapsed, 3),
        'cases':cases,
        "statuses": statuses,
        'slowest_operations':dict(sorted(OPERATIONS.items(),key=lambda item:item[1]['seconds'],reverse=True)[:20]),
        "module_totals": dict(
            sorted(modules.items(), key=lambda item: item[1]["total"], reverse=True)
        ),
        "slowest_cases": sorted(cases, key=lambda item: item["total"], reverse=True)[:20],
    }


def _write_performance_summary():
    os.makedirs(RUNTIME_DIR, exist_ok=True)
    path = os.path.join(RUNTIME_DIR, "performance-summary.json")
    summary = _performance_summary()
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
    return path, summary


@pytest.fixture(scope="session", autouse=True)
def performance_summary_attachment():
    if ConfigManager.EXCLUDED_CAPABILITIES:
        allure.attach(
            json.dumps(ConfigManager.EXCLUDED_CAPABILITIES, ensure_ascii=False, indent=2),
            "当前环境明确排除的功能及原因", allure.attachment_type.JSON,
        )
    yield
    path, summary = _write_performance_summary()
    allure.attach.file(
        path,
        name="全量性能统计",
        attachment_type=allure.attachment_type.JSON,
    )
    print(f"PERFORMANCE_SUMMARY: {json.dumps(summary, ensure_ascii=False)}")


def pytest_collection_modifyitems(config, items):
    """Apply a baseline test taxonomy without duplicating markers in every file."""
    from common.allure_reporting import report_title_template, validate_collected_items
    from common.product_profile import detect_build_profile, supported_feature_ids

    profile = detect_build_profile(ConfigManager.HST_URL)
    config._ces_product_profile = profile
    validate_collected_items(items)
    supported = supported_feature_ids(profile)
    selected = []
    deselected = []
    for item in items:
        required_profiles = {
            str(value)
            for marker in item.iter_markers("requires_profile")
            for value in marker.args
        }
        if required_profiles and profile not in required_profiles:
            deselected.append(item)
            continue
        requirements = {
            str(value)
            for marker in item.iter_markers("requires_capability")
            for value in marker.args
        }
        feature_id = getattr(item, 'callspec', None)
        feature_id = feature_id.params.get('feature_id') if feature_id else None
        excluded = requirements.intersection(ConfigManager.EXCLUDED_CAPABILITIES)
        if feature_id in ConfigManager.EXCLUDED_CAPABILITIES:
            excluded.add(feature_id)
        if excluded:
            deselected.append(item)
            continue
        if requirements and not requirements.issubset(supported):
            deselected.append(item)
            continue
        if item.get_closest_marker("destructive") is None:
            item.add_marker(pytest.mark.regression)
        if item.name.startswith("test_enter_") or "login_smoke" in item.name:
            item.add_marker(pytest.mark.smoke)
        if any(part in item.nodeid for part in ("test_001_login.py", "test_007_back_permissons.py")):
            item.add_marker(pytest.mark.security)
        if any(name in item.name for name in (
            "server_required_field_validation",
            "server_invalid_value_validation",
            "batch_delete_only_created_users",
            "batch_delete_only_created_terminals",
            "add_duplicate_user_failed",
            "add_user_failed",
            "add_duplicate_terminal_name_allowed",
            "add_duplicate_terminal_serial_failed",
            "page_size",
            "jump_user_page",
        )):
            item.add_marker(pytest.mark.extended)
        # The Allure pytest listener reads this attribute when it creates the
        # result. It keeps pytest nodeids unchanged, so `file.py::test_name`
        # remains usable from the command line.
        item.function.__allure_display_name__ = report_title_template(item)
        selected.append(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected
    seed = os.getenv('UIAUTO_SHUFFLE_SEED')
    if seed:
        import random
        random.Random(int(seed)).shuffle(items)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if ConfigManager.EXCLUDED_CAPABILITIES:
        terminalreporter.write_sep("-", "当前环境明确排除的功能")
        for feature_id, reason in ConfigManager.EXCLUDED_CAPABILITIES.items():
            terminalreporter.write_line(f"{feature_id}: {reason}")
    rows = []
    for reports in terminalreporter.stats.values():
        for report in reports:
            if getattr(report, "when", "") == "call" and hasattr(report, "duration"):
                rows.append((report.duration, report.nodeid))
    if rows:
        terminalreporter.write_sep("-", "本次最慢用例")
        for duration, nodeid in sorted(rows, reverse=True)[:10]:
            terminalreporter.write_line(f"{duration:6.1f}s  {nodeid}")


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Apply report labels before a setup fixture can skip a test case."""
    from common.allure_reporting import case_title, module_for_item

    parent_suite, suite = module_for_item(item)
    allure.dynamic.parent_suite(parent_suite)
    allure.dynamic.suite(suite)
    allure.dynamic.sub_suite("自动化回归")
    allure.dynamic.title(case_title(item))
    allure.dynamic.description(f"{parent_suite} - {suite} 自动化验证")
    from common.privacy import redact
    for name,value in getattr(getattr(item,'callspec',None),'params',{}).items():
        safe=redact(value)
        if safe != value:
            allure.dynamic.parameter(name,safe)


@pytest.fixture(autouse=True)
def allure_chinese_metadata(request):
    """Attach Chinese parameter labels after fixtures have prepared the case."""
    item = request.node

    callspec = getattr(item, "callspec", None)
    if callspec:
        values = callspec.params
        if "group_name" in values:
            allure.dynamic.parameter("一级菜单", values["group_name"])
        if "item_name" in values:
            allure.dynamic.parameter("子菜单", values["item_name"])
        if 'model_key' in values:
            allure.dynamic.parameter('模型配置', values['model_key'])
        if isinstance(values.get("params"), dict):
            scenario = values["params"].get("scenario")
            if scenario:
                allure.dynamic.parameter("测试场景", scenario)
    yield


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_call(item):
    # Allure applies its generic template at the end of setup. Apply the
    # Chinese scenario title afterwards while retaining the real nodeid.
    from common.allure_reporting import case_title
    allure.dynamic.title(case_title(item))


@pytest.fixture(scope="session")
def driver():
    driver_path = resolve_chromedriver_path()

    # Use an isolated profile dir to reduce startup conflicts.
    headless_default = _is_truthy(os.getenv("UIAUTO_HEADLESS"), default=True)
    mode_candidates = [headless_default]
    if headless_default:
        mode_candidates.append(False)

    browser = None
    last_error = None
    created_profile_dirs = []

    for root in _profile_root_candidates():
        try:
            os.makedirs(root, exist_ok=True)
        except OSError as exc:
            last_error = exc
            continue

        for use_headless in mode_candidates:
            profile_dir = tempfile.mkdtemp(prefix="chrome_profile_", dir=root)
            created_profile_dirs.append(profile_dir)
            options = chrome_options(headless=use_headless, profile_dir=profile_dir)
            try:
                if driver_path:
                    try:
                        current_service = Service(driver_path)
                        browser = webdriver.Chrome(
                            service=current_service, options=options
                        )
                    except Exception:
                        # A packaged driver may not match Chrome after an
                        # automatic browser update. Let Selenium Manager
                        # resolve the installed browser instead of aborting
                        # the complete suite during fixture setup.
                        browser = webdriver.Chrome(options=options)
                else:
                    browser = webdriver.Chrome(options=options)
                break
            except Exception as exc:
                last_error = exc
                browser = None
        if browser is not None:
            break

    if browser is None:
        for use_headless in mode_candidates:
            options = chrome_options(headless=use_headless, profile_dir=None)
            try:
                if driver_path:
                    try:
                        current_service = Service(driver_path)
                        browser = webdriver.Chrome(
                            service=current_service, options=options
                        )
                    except Exception:
                        browser = webdriver.Chrome(options=options)
                else:
                    browser = webdriver.Chrome(options=options)
                break
            except Exception as exc:
                last_error = exc
                browser = None

    if browser is None:
        for profile_dir in created_profile_dirs:
            shutil.rmtree(profile_dir, ignore_errors=True)
        raise last_error
    # Store the live driver for setup/teardown evidence even when a dependent
    # fixture fails before the test's arguments are assembled.
    global ACTIVE_BROWSER
    ACTIVE_BROWSER = browser

    # The default resource-timing buffer fills during a serial full suite.
    # Keep read-only request completion evidence available after navigation
    # without changing application requests, responses or server waits.
    browser.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "performance.setResourceTimingBufferSize(10000);"},
    )
    browser.execute_script("performance.setResourceTimingBufferSize(10000);")

    download_dir = os.getenv(
        "UIAUTO_DOWNLOAD_DIR", os.path.join(RUNTIME_DIR, "downloads")
    )
    os.makedirs(download_dir, exist_ok=True)
    try:
        browser.execute_cdp_cmd(
            "Browser.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": os.path.abspath(download_dir)},
        )
    except Exception:
        browser.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": os.path.abspath(download_dir)},
        )

    try:
        yield browser
    finally:
        try:
            browser.quit()
        finally:
            ACTIVE_BROWSER = None
            for profile_dir in created_profile_dirs:
                shutil.rmtree(profile_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def product_context(driver):
    """Detect frontend profile and the administrator's real authorized menu tree."""
    from common.product_profile import build_runtime_context, detect_build_profile
    from pages.Index_Page.index import LoginPage

    login_page = LoginPage(driver=driver)
    current_url = driver.current_url or ""
    if not current_url.startswith(ConfigManager.HST_URL) or "login" in current_url.lower():
        login_page.open_login_url()
        if not login_page.login_with_optional_captcha(
            ConfigManager.USERNAME, ConfigManager.PASSWORD
        ):
            pytest.exit(
                f"管理员登录前置失败：{login_page.last_login_error or '未返回错误提示'}",
                returncode=2,
            )
    # The guide can mount shortly after the first authenticated render. Wait
    # for it only once per session; later page opens use a zero-wait check.
    login_page.dismiss_intro_if_present(timeout=2)
    profile = detect_build_profile(ConfigManager.HST_URL)
    context = build_runtime_context(driver, profile)
    report = {
        "后台版本配置": context.profile,
        "实际授权菜单": context.menu_tree,
        "已授权能力": sorted(context.authorized),
        "未登记菜单": context.unknown_menus,
        "策略排除": ["直播管理"],
        "当前环境明确排除": ConfigManager.EXCLUDED_CAPABILITIES,
    }
    allure.attach(
        json.dumps(report, ensure_ascii=False, indent=2),
        name="后台版本与授权能力",
        attachment_type=allure.attachment_type.JSON,
    )
    if ConfigManager.ACCEPTANCE_MODE and not context.menu_tree:
        pytest.fail("登录后未识别到任何侧边栏菜单，无法判定功能授权")
    return context


@pytest.fixture(scope='session',autouse=True)
def environment_preflight(request):
    if not os.getenv('UIAUTO_RUN_ID'):
        return
    from pages.PersonalProfilePage import PersonalProfilePage
    from pages.Server_Page.DataManagePage import DataManagePage
    from pages.Meeting_Page.MeetingRecordsPage import MeetingRecordsPage
    driver=request.getfixturevalue('driver')
    context=request.getfixturevalue('product_context')
    selected=request.session.items
    fixtures={name for item in selected for name in item.fixturenames}
    if 'personal_profile' in fixtures and ConfigManager.PROFILE_PASSWORD_USERNAME==ConfigManager.USERNAME:
        pytest.exit('前置条件：普通改密账号必须与管理账号不同',returncode=2)
    verifier=None
    verifier_browser=request.getfixturevalue('verification_driver') if {'login','personal_profile'} & fixtures else None
    accounts={}
    for name,username,password in (
        ('登录矩阵账号',ConfigManager.LOGIN_TEST_USERNAME,ConfigManager.LOGIN_TEST_PASSWORD),
        ('个人资料账号',ConfigManager.PROFILE_PASSWORD_USERNAME,ConfigManager.PROFILE_PASSWORD_PASSWORD),
    ):
        required=('login_test_account' in fixtures) if name=='登录矩阵账号' else ('personal_profile' in fixtures)
        if required:
            if verifier is None:verifier=PersonalProfilePage(driver=verifier_browser or request.getfixturevalue('verification_driver'))
            accounts[name]=verifier.login_as(username,password)
    if verifier is not None:verifier.reset_login_state()
    data=DataManagePage(driver=driver)
    backups=[]
    if any('test_backup_download_and_upload' in item.nodeid for item in selected) and data.common_enter_data():
        data.wait_until(lambda: len(data.get_table_headers())>=6 and data.wait_loading_finished(timeout=0.2),timeout=10)
        backups=[name for name in data.get_backup_file_names() if name.endswith(('.sql','.dmp'))]
    record={}
    if any('test_meeting_record_authorized_detail_entries' in item.nodeid for item in selected):
        try:
            records=MeetingRecordsPage(driver=driver)
            record['可用入口']=records.available_record_action_titles()
            record['固定开始时间']=records._detail_start
        except AssertionError as exc:
            record['前置错误']=str(exc)
    evidence={'账号检查':accounts,'实际菜单':context.menu_tree,'备份源数量':len(backups),
        '验证与管理会话隔离':verifier_browser is None or verifier_browser.session_id!=driver.session_id,
        '浏览器版本':driver.capabilities.get('browserVersion'),
        '驱动版本':driver.capabilities.get('chrome',{}).get('chromedriverVersion','').split(' ')[0],
        '会议详情':record,'AI密钥已配置':bool(ConfigManager.AI_CR_API_KEY and ConfigManager.AI_OPENAI_API_KEY),
        '未自动化新业务':['白名单用户业务流程','SSO业务流程']}
    os.makedirs(RUNTIME_DIR,exist_ok=True)
    with open(os.path.join(RUNTIME_DIR,'preconditions.json'),'w',encoding='utf-8') as file:
        json.dump(evidence,file,ensure_ascii=False,indent=2)
    allure.attach(json.dumps(evidence,ensure_ascii=False,indent=2),'环境与固定数据前置检查',allure.attachment_type.JSON)
    if not all(accounts.values()):
        pytest.exit('前置条件：测试账号无法登录，停止业务执行；已保存前置诊断。',returncode=2)


@pytest.fixture(scope="session")
def verification_driver(driver):
    """Second fixed browser; every authentication proof starts a fresh session."""
    options = chrome_options(headless=_is_truthy(os.getenv('UIAUTO_HEADLESS'), default=True), profile_dir=None)
    path = resolve_chromedriver_path()
    try:
        try:
            browser = webdriver.Chrome(service=Service(path), options=options) if path else webdriver.Chrome(options=options)
        except Exception:
            browser=webdriver.Chrome(options=options)
    except Exception as error:
        pytest.exit(f'验证浏览器启动前置失败：{type(error).__name__}',returncode=2)
    browser._ces_management_driver=driver
    driver._ces_verification_driver=browser
    browser.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': 'performance.setResourceTimingBufferSize(10000)'})
    try:
        yield browser
    finally:
        browser.quit()
        browser._ces_management_driver=None
        driver._ces_verification_driver=None


def _case_browser(item):
    for name in ('personal_profile','login'):
        page=item.funcargs.get(name)
        if page is not None and getattr(page,'driver',None) is not None:return page.driver
    return item.funcargs.get('driver') or globals().get('ACTIVE_BROWSER')


@pytest.fixture(autouse=True)
def management_session_hygiene(request):
    # Authentication-only cases operate in the verifier. Reauthenticate the
    # management session only when a later business case actually needs it.
    if {'login','personal_profile'} & set(request.node.fixturenames):return
    browser=globals().get('ACTIVE_BROWSER')
    if browser is None or not getattr(browser,'_needs_admin_login',False):return
    from pages.Index_Page.index import LoginPage
    with allure.step('恢复管理浏览器认证会话'):
        assert LoginPage(driver=browser).common_login() is True,'管理会话重新认证失败'


@pytest.fixture(autouse=True)
def enforce_required_capability(request):
    """Turn unsupported builds into deselection and unauthorized menus into N/A."""
    requirements = {
        str(value)
        for marker in request.node.iter_markers("requires_capability")
        for value in marker.args
    }
    if not requirements:
        yield
        return
    context = request.getfixturevalue("product_context")
    missing = requirements - context.authorized
    if missing:
        required = missing & ConfigManager.REQUIRED_CAPABILITIES
        if required:
            pytest.fail(f"必测能力未授权：{', '.join(sorted(required))}")
        pytest.skip(f"当前环境未授权，功能不适用：{', '.join(sorted(missing))}")
    yield


@pytest.fixture(autouse=True)
def transient_ui_cleanup(request):
    """Cancel this case's open layers without accepting or saving anything."""
    yield
    browser = _case_browser(request.node)
    if browser is None:
        return
    from common.semantic_controls import cancel_transient_layers
    closed=cancel_transient_layers(browser)
    if closed:
        allure.attach(str(closed),'用例结束的弹窗取消记录',allure.attachment_type.TEXT)


@pytest.hookimpl(trylast=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.failed:
        allure.dynamic.label('failure_phase',report.when)
        from common.stability import classify
        from common.privacy import redact
        report.longrepr=_redact_case_failure(item,str(report.longrepr))
        user = item.funcargs.get('user')
        debug = getattr(user, 'last_modify_debug', {}) if user else {}
        if user:
            allure.attach(json.dumps(redact({'修改':debug,'打开修改弹窗':getattr(user,'last_open_profile_debug',{}),'字段输入':getattr(user,'last_field_input_debug',{})}),ensure_ascii=False,default=str),
                '用户操作失败诊断',allure.attachment_type.JSON)
        cause=redact(str(call.excinfo.value)) if call.excinfo else str(report.longrepr)
        ai_debug=getattr(item.funcargs.get('ai_models'),'last_lifecycle_evidence',None)
        kind, root = classify(item.nodeid, cause, report.when, debug, ai_debug)
        allure.dynamic.label('failure_origin', kind)
        allure.dynamic.label('root_cause', root)
        allure.attach(json.dumps({'阶段':report.when,'分类':kind,'根因':root},ensure_ascii=False), '失败归因', allure.attachment_type.JSON)
    if report.when != 'call' and not report.failed:
        return

    # Attach assertion snippets to the report.
    try:
        source_code = inspect.getsource(item.function)
    except OSError:
        source_code = ""

    assertions = re.findall(r"assert\s+(.+?)[\s,;]", source_code)
    if assertions:
        with allure.step("断言清单"):
            for idx, assertion in enumerate(assertions, 1):
                allure.attach(
                    name=f"断言 {idx}",
                    body=f"断言表达式：{assertion.strip()}",
                    attachment_type=allure.attachment_type.TEXT,
                )

    # Add screenshot for failed tests when driver fixture is present.
    if report.failed and _case_browser(item) is not None:
        driver = _case_browser(item)
        try:
            from common.privacy import masked_screenshot
            with masked_screenshot(driver):
                screenshot_path = _save_failure_screenshot(driver, item)
                screenshot = driver.get_screenshot_as_png()
        except Exception as exc:
            allure.attach(type(exc).__name__,'截图采集失败，原失败保留',allure.attachment_type.TEXT)
            return
        allure.attach(
            screenshot,
            name="失败截图",
            attachment_type=allure.attachment_type.PNG,
        )
        allure.attach(
            screenshot_path,
            name="失败截图路径",
            attachment_type=allure.attachment_type.TEXT,
        )
        allure.attach(
            str(report.longrepr),
            name="失败详情",
            attachment_type=allure.attachment_type.TEXT,
        )

    # Emit machine-readable result for external capture.
    from common.allure_reporting import case_title

    description = case_title(item)
    params = {}
    if hasattr(item, "callspec"):
        params = item.callspec.params
        data_params = params.get("params")
        if isinstance(data_params, dict):
            description = data_params.get(
                "description", data_params.get("username", case_title(item))
            )

    if report.passed:
        case_status = "passed"
    elif report.skipped:
        case_status = "skipped"
    else:
        case_status = "failed"

    case_info = {
        "nodeid": item.nodeid,
        "name": case_title(item),
        "description": description,
        "status": case_status,
        "params": str(params.get("params", {})),
        "duration": round(report.duration, 3),
        "error": str(report.longrepr) if report.failed else "",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    result_line = f'TEST_CASE_RESULT: {json.dumps(case_info, ensure_ascii=False)}'
    try:
        print(result_line)
    except UnicodeEncodeError:
        safe_line = result_line.encode(
            sys.stdout.encoding or "utf-8", errors="replace"
        ).decode(sys.stdout.encoding or "utf-8", errors="replace")
        print(safe_line)


@pytest.fixture(scope="module")
def login(verification_driver):
    from pages.Index_Page.index import LoginPage

    return LoginPage(driver=verification_driver)


@pytest.fixture(scope="module")
def personal_profile(verification_driver):
    from pages.PersonalProfilePage import PersonalProfilePage

    return PersonalProfilePage(driver=verification_driver)


@pytest.fixture(scope="module")
def organize(driver):
    from pages.ContactList_Page.OrganizePage import OrganizeManagerPage

    return OrganizeManagerPage(driver=driver)


@pytest.fixture(scope="module")
def user(driver):
    from pages.ContactList_Page.UserPage import UserManagerPage

    return UserManagerPage(driver=driver)


@pytest.fixture(scope="module")
def meeting_info(driver):
    from pages.Meeting_Page.MeetingInfoPage import MeetingInfoPage

    return MeetingInfoPage(driver=driver)


@pytest.fixture(scope="module")
def terminal(driver):
    from pages.ContactList_Page.TerminalPage import TerminalManagerPage

    return TerminalManagerPage(driver=driver)


@pytest.fixture(scope="module")
def back_permissions(driver):
    from pages.Server_Page.BackPermissionsPage import BackPermissionsManagerPage

    return BackPermissionsManagerPage(driver=driver)


@pytest.fixture(scope="module")
def data(driver):
    from pages.Server_Page.DataManagePage import DataManagePage

    return DataManagePage(driver=driver)


@pytest.fixture(scope="module")
def server_list(driver):
    from pages.Server_Page.ServerListPage import ServerListPage

    page = ServerListPage(driver=driver)
    try:
        yield page
    finally:
        page.cleanup_registered_servers()


@pytest.fixture(scope="module")
def feature_manage(driver):
    from pages.Configuration_Center_Page.FeatureManagePage import FeatureManagePage

    return FeatureManagePage(driver=driver)


@pytest.fixture(scope="module")
def feature_params_manage(driver):
    from pages.Configuration_Center_Page.FeatureParamsManagePage import (
        FeatureParamsManagePage,
    )

    return FeatureParamsManagePage(driver=driver)


@pytest.fixture(scope="module")
def product_info(driver):
    from pages.Configuration_Center_Page.ProductInfoPage import ProductInfoPage

    return ProductInfoPage(driver=driver)


@pytest.fixture(scope="module")
def global_record(driver):
    from pages.Record_Page.GlobalRecordPage import GlobalRecordPage

    return GlobalRecordPage(driver=driver)


@pytest.fixture(scope="module")
def log(driver):
    from pages.Log_Page.OperationLogPage import OperationLogPage

    return OperationLogPage(driver=driver)


@pytest.fixture(scope="module")
def server_log(driver):
    from pages.Log_Page.ServerLogPage import ServerLogPage

    return ServerLogPage(driver=driver)


@pytest.fixture(scope="module")
def call(driver):
    from pages.ContactList_Page.CallPage import CallManagerPage

    return CallManagerPage(driver=driver)


@pytest.fixture(scope="module")
def feature_catalog(driver):
    from pages.FeatureCatalogPage import FeatureCatalogPage

    return FeatureCatalogPage(driver=driver)


@pytest.fixture(scope="module")
def meeting_records(driver):
    from pages.Meeting_Page.MeetingRecordsPage import MeetingRecordsPage
    return MeetingRecordsPage(driver=driver)


@pytest.fixture(scope="module")
def meeting_statistics(driver):
    from pages.Meeting_Page.MeetingStatisticsPage import MeetingStatisticsPage
    return MeetingStatisticsPage(driver=driver)


@pytest.fixture(scope="module")
def meeting_scenarios(driver):
    from pages.Meeting_Page.MeetingScenarioPage import MeetingScenarioPage
    return MeetingScenarioPage(driver=driver)


@pytest.fixture(scope="module")
def meeting_log(driver):
    from pages.Log_Page.MeetingLogPage import MeetingLogPage
    return MeetingLogPage(driver=driver)


@pytest.fixture(scope="module")
def terminal_log(driver):
    from pages.Log_Page.TerminalLogPage import TerminalLogPage
    return TerminalLogPage(driver=driver)


@pytest.fixture(scope="module")
def developer_page(driver):
    from pages.DeveloperPage import DeveloperPage
    return DeveloperPage(driver=driver)


@pytest.fixture(scope="module")
def recording_tasks(driver):
    from pages.Record_Page.RecordingTaskPage import RecordingTaskPage
    return RecordingTaskPage(driver=driver)


@pytest.fixture(scope="module")
def ai_models(driver):
    from pages.AIModelPage import AIModelPage

    return AIModelPage(driver=driver)


@pytest.fixture(scope="module")
def face_library(driver):
    from pages.FaceLibraryPage import FaceLibraryPage

    return FaceLibraryPage(driver=driver)


@pytest.fixture(scope="module")
def client_feature(driver):
    from pages.ClientFeaturePage import ClientFeaturePage

    return ClientFeaturePage(driver=driver)
