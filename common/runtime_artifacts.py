# -*- coding: utf-8 -*-
import os
import json
import subprocess
import time
import uuid
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

import allure
import pytest

from conf.conf import ConfigManager


def require_external_data(value, description):
    if value:
        return value
    message = f"Missing required test data: {description}"
    if ConfigManager.ACCEPTANCE_MODE:
        pytest.fail(message)
    pytest.skip(message)


def clean_directory(path):
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    for child in directory.iterdir():
        if child.is_file():
            child.unlink()
    return directory


def configure_download_directory(driver, directory):
    """Set the browser destination explicitly; callers must never inherit it."""
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    try:
        driver.execute_cdp_cmd("Browser.setDownloadBehavior", {
            "behavior": "allow", "downloadPath": str(directory), "eventsEnabled": True,
        })
    except Exception:
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow", "downloadPath": str(directory),
        })
    driver._ces_download_directory = str(directory)
    return directory


def prepare_download(driver, root=None):
    """Give each real UI download its own destination before clicking."""
    directory = Path(root or ConfigManager.DOWNLOAD_DIR) / f"download_{uuid.uuid4().hex[:12]}"
    configure_download_directory(driver, directory)
    # Discard previous request events; no headers, bodies or URL queries are
    # retained. The actual application download is still initiated by its UI.
    try:
        driver.get_log("performance")
    except Exception:
        pass
    driver._ces_download_evidence = {"目录": str(directory), "请求": [], "下载事件": []}
    return directory


def _collect_download_events(driver, evidence):
    try:
        entries = driver.get_log("performance")
    except Exception:
        return
    for entry in entries:
        message = json.loads(entry.get("message", "{}" )).get("message", {})
        method, params = message.get("method", ""), message.get("params", {})
        if method == "Network.responseReceived":
            response = params.get("response", {})
            if params.get("type") not in {"XHR", "Fetch", "Document"}:
                continue
            url = urlsplit(response.get("url", ""))
            evidence["请求"].append({"主机": url.netloc, "路径": url.path,
                "状态码": response.get("status"), "类型": response.get("mimeType")})
        elif method == "Network.loadingFailed":
            evidence["请求"].append({"错误": params.get("errorText"), "拦截原因": params.get("blockedReason")})
        elif method in {"Page.downloadWillBegin", "Browser.downloadWillBegin"}:
            evidence["下载事件"].append({"事件": "开始", "标识": params.get("guid"),
                "文件名": params.get("suggestedFilename")})
        elif method in {"Page.downloadProgress", "Browser.downloadProgress"}:
            evidence["下载事件"].append({"事件": params.get("state"), "标识": params.get("guid"),
                "已接收字节": params.get("receivedBytes"), "总字节": params.get("totalBytes")})
    evidence["请求"] = evidence["请求"][-30:]
    evidence["下载事件"] = evidence["下载事件"][-50:]


def _attach_download_result(driver, evidence, path=None):
    evidence["结果"] = "成功" if path else "未获得有效文件"
    if path:
        evidence["文件"] = {"名称": path.name, "扩展名": path.suffix, "字节": path.stat().st_size}
    else:
        directory = Path(evidence["目录"])
        evidence["当前文件"] = [{"名称": p.name, "字节": p.stat().st_size}
            for p in directory.iterdir() if p.is_file()]
    if driver is not None:
        driver._ces_download_evidence = evidence
    allure.attach(json.dumps(evidence, ensure_ascii=False, indent=2),
        "下载完成证据" if path else "下载失败诊断", allure.attachment_type.JSON)


def wait_for_download(directory, existing=None, extensions=None, timeout=20, driver=None):
    directory = Path(directory)
    existing = set(existing or [])
    allowed = {value.lower() for value in (extensions or [])}
    evidence = {"目录": str(Path(directory).resolve()), "请求": [], "下载事件": []}
    previous = {}
    end = time.time() + timeout
    while time.time() < end:
        if driver is not None:
            _collect_download_events(driver, evidence)
        for path in directory.iterdir():
            if path.name in existing or path.suffix.lower() in {".crdownload", ".tmp"}:
                continue
            if allowed and path.suffix.lower() not in allowed:
                continue
            if path.is_file() and path.stat().st_size > 0:
                size = path.stat().st_size
                if previous.get(path.name) != size:
                    previous[path.name] = size
                    continue
                events = evidence["下载事件"]
                # If the browser emitted a start event, require its completion.
                matching = [e for e in events if e.get("文件名") == path.name]
                if matching and not any(e.get("标识") == matching[-1].get("标识")
                        and e["事件"] == "completed" for e in events):
                    continue
                if path.suffix.lower() in {".zip", ".xlsx"}:
                    try:
                        with zipfile.ZipFile(path) as archive:
                            if not archive.namelist() or archive.testzip() is not None:
                                continue
                            if path.suffix.lower() == '.xlsx' and 'xl/workbook.xml' not in archive.namelist():
                                continue
                    except (OSError, zipfile.BadZipFile):
                        continue
                _attach_download_result(driver, evidence, path)
                return path
        time.sleep(0.25)
    _attach_download_result(driver, evidence)
    return None


def trigger_terminal_log():
    command = (ConfigManager.TERMINAL_LOG_TRIGGER_COMMAND or "").strip()
    if not command:
        return None
    return subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=60,
        env=os.environ.copy(),
    )


def build_import_workbook(template_path, output_path, rows):
    template_path = Path(template_path)
    output_path = Path(output_path)
    if not template_path.exists():
        raise FileNotFoundError(f"Import template not found: {template_path}")

    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ET.register_namespace("", ns)
    with zipfile.ZipFile(template_path, "r") as source:
        files = {name: source.read(name) for name in source.namelist()}
    sheet_name = "xl/worksheets/sheet1.xml"
    if sheet_name not in files:
        raise ValueError("Import template has no first worksheet")

    shared = []
    if "xl/sharedStrings.xml" in files:
        shared_root = ET.fromstring(files["xl/sharedStrings.xml"])
        for item in shared_root.findall(f"{{{ns}}}si"):
            shared.append("".join(item.itertext()))

    root = ET.fromstring(files[sheet_name])
    sheet_data = root.find(f"{{{ns}}}sheetData")
    template_rows = sheet_data.findall(f"{{{ns}}}row") if sheet_data is not None else []
    if not template_rows:
        raise ValueError("Import template has no header row")
    headers = []
    for candidate in template_rows:
        values = []
        for cell in candidate.findall(f"{{{ns}}}c"):
            value = cell.find(f"{{{ns}}}v")
            if value is None:
                values.append("".join(cell.itertext()))
            elif cell.get("t") == "s":
                values.append(shared[int(value.text)])
            else:
                values.append(value.text or "")
        nonempty = [value.strip() for value in values if value and value.strip()]
        if len(nonempty) >= 2 and len(set(nonempty)) >= 2:
            headers = values
            break
    if not headers:
        raise ValueError("Import template has no header values")

    next_index = max(int(row.get("r", "0")) for row in sheet_data.findall(f"{{{ns}}}row")) + 1
    def normalized_header(value):
        return "".join(
            char
            for char in str(value or "")
            if char not in " *()（）:：-_/\\\t\r\n"
        ).lower()

    def value_for_header(values, header):
        if header in values:
            return values[header]
        target = normalized_header(header)
        for key, value in values.items():
            normalized_key = normalized_header(key)
            if normalized_key == target or normalized_key in target or target in normalized_key:
                return value
        return ""

    for values in rows:
        row_node = ET.SubElement(sheet_data, f"{{{ns}}}row", {"r": str(next_index)})
        for column, header in enumerate(headers, 1):
            letters = ""
            number = column
            while number:
                number, remainder = divmod(number - 1, 26)
                letters = chr(65 + remainder) + letters
            cell = ET.SubElement(
                row_node,
                f"{{{ns}}}c",
                {"r": f"{letters}{next_index}", "t": "inlineStr"},
            )
            inline = ET.SubElement(cell, f"{{{ns}}}is")
            text_node = ET.SubElement(inline, f"{{{ns}}}t")
            text_node.text = str(value_for_header(values, header))
        next_index += 1
    files[sheet_name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as target:
        for name, content in files.items():
            target.writestr(name, content)
    return output_path
