# CES 后台 UI 自动化测试

CES 私有云后台的 UI 自动化项目。执行入口是 `run.py`，测试完成后自动生成并打开 Allure 报告。

## 直接运行

首次从GitHub获取项目时，先创建虚拟环境、安装requirements.txt，再复制脱敏模板：

```powershell
Copy-Item conf/conf.example.py conf/conf.py
```

已有本地配置不要覆盖。实际地址、登录账号、密码、邮箱和模型密钥只填在本地conf.py或环境变量中，不提交到Git。人脸测试素材由本地`data/image/`或`UIAUTO_FACE_IMAGE_DIR`提供，文件名参考`testcases/test_028_face_library.py`；仓库不包含人像素材、ChromeDriver、虚拟环境和运行产物。

隔离单元检查不加载根conftest的浏览器及环境预检：

```powershell
.\.venv-local\Scripts\python.exe -X utf8 -m pytest tests/unit --confcutdir=tests/unit -o addopts="" -q
```

```powershell
# 默认回归：显示 Chrome，排除高风险和深度矩阵用例
python run.py

# 完整非高风险回归：包含边界、分页、批量等深度用例
python run.py --full
```

常用参数：

| 命令 | 说明 |
| --- | --- |
| `python run.py --headless` | 无界面执行。 |
| `python run.py --no-open` | 生成报告但不自动打开。 |
| `python run.py testcases/test_003_user.py -v` | 仅运行指定模块。 |
| `python run.py --include-destructive` | 启用备份恢复、服务器启停等高风险操作。 |

`run.py` 会自动使用 `.venv-local`，日常不需要手动激活虚拟环境。

## 换电脑或换环境

只需检查 [conf/conf.py](conf/conf.py)：

1、测试环境和账号：
HST_URL = "http://目标环境IP:28080"
USERNAME = "admin"
PASSWORD = "管理员密码"

2、ChromeDriver：
Chrome 主版本必须与本机 Chrome 一致。替换：
.venv-local\Scripts\chromedriver.exe

或在 conf.py 修改：
CHROMEDRIVER_PATH = r"D:\tools\chromedriver.exe"


3、依赖环境
确保项目包含 .venv-local。若没有，在项目根目录执行：
python -m venv .venv-local
.\.venv-local\Scripts\python.exe -m pip install -r requirements.txt

还需要安装 Allure Commandline，并将 allure\bin 加到系统 PATH，否则测试能跑但无法自动生成/打开报告。

4、固定测试数据
若要完整执行录制和终端日志用例，按新环境修改：
RECORD_TASK_KEYWORD = "专用录制任务关键字"
TERMINAL_LOG_USERNAME = "日志对应员工账号"
TERMINAL_LOG_DEVICE_ID = "日志对应设备ID"
TERMINAL_LOG_TYPE = "终端日志"



| 项目 | 要求 |
| --- | --- |
| Python | 建议 Python 3.10 及以上。 |
| 依赖 | `.\.venv-local\Scripts\python.exe -m pip install -r requirements.txt` |
| ChromeDriver | 主版本必须与本机 Chrome 一致；替换 `.venv-local\Scripts\chromedriver.exe`。 |
| Allure | 安装 Allure Commandline 并将 `bin` 加入 `PATH`；用 `allure --version` 验证。 |

正式验收环境还应在 `conf.py` 填写专用登录账号、录制任务关键字和终端日志固定数据。`TERMINAL_LOG_TRIGGER_COMMAND` 可留空，只有需要主动制造终端日志时才填写。

## 目录说明

```text
ces_UI_auto/
├─ run.py              执行入口：pytest + Allure 报告
├─ conftest.py         Chrome、fixture、截图、Allure 全局配置
├─ pytest.ini          pytest 用例发现和 marker
├─ requirements.txt    Python 依赖
├─ conf/conf.py        环境、账号、Driver、下载和前置数据配置
├─ common/             OCR、下载、导入、Allure、前置检查等公共能力
├─ data/               JSON 参数化数据、菜单清单、页面特征
├─ pages/              Page Object；按通讯录、会议、录制、日志、服务器等分目录
├─ testcases/          pytest 用例；`test_000` 至 `test_026` 按模块编号组织
├─ docs/               覆盖矩阵和用例审计记录
├─ scripts/            可选通知脚本
├─ tests/unit/         下载隔离、弹窗恢复、请求完成与执行锁验证
├─ reports/runs/       每轮独立结果、报告、耗时和清理证据
├─ allure-results/     本次执行原始结果，可删除再生成
├─ allure-report/      Allure HTML 报告，可删除再生成
├─ .runtime/           下载、导入等运行时文件，可删除再生成
└─ screenshots/        失败截图，可删除再生成
```

`.venv-local/` 是推荐虚拟环境。`*.log`、`__pycache__/`、`.pytest_cache/`、`.idea/`、`.vscode/` 是本地缓存或历史产物，分发项目时可不带。

## 维护约定

1. 页面操作写入 `pages/`，业务断言写入 `testcases/`，参数化数据写入 `data/`。
2. 新增菜单先更新 `data/menu_inventory.json` 和 `data/page_features.json`。
3. 临时数据使用 `uiauto_` 唯一前缀，并在 teardown 或 `finally` 清理。
4. 导入、导出、下载必须验证真实文件；配置修改必须恢复原值。
5. 环境级危险操作必须加 `@pytest.mark.destructive`。

菜单遍历会在可见 Chrome 中逐页停留 `MENU_VISUAL_DWELL_SECONDS` 秒，默认 2 秒，配置位于 `conf.py`。

稳定性验证使用两个隔离 Chrome，严格串行；不会自动重跑整条失败用例。每轮报告保存在 `reports/runs/运行编号/`，根目录 `allure-report` 仅保留最新报告。根因汇总在该轮报告的 `stability-summary.html`，原始失败不会改判通过。

连续三轮用 `python run.py --full --headless --no-open`。核对命令为 `python scripts/verify_stability.py 第一轮目录 第二轮目录 第三轮目录 --baseline 对照轮目录`。三轮必须使用同一代码、相同节点和配置；产品问题、固定数据缺失仍会失败，脚本稳定不等于功能全绿。详细约定见 [稳定性验收说明](docs/稳定性验收说明.md)。

## 项目框架与技术

- Python 3.10+：测试脚本运行语言。
- pytest：用例组织、参数化、fixture、marker 和断言框架。
- Selenium 4：Chrome 浏览器自动化。
- Page Object Model：页面定位与业务操作封装在 `pages/`。
- Allure：测试报告、中文步骤、截图和附件展示。
- ddddocr：离线验证码 OCR 识别。
- JSON：测试数据、菜单清单和页面特征配置。
