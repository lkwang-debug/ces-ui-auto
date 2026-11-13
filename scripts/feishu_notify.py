# -*- coding: utf-8 -*-
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


def _load_allure_results(results_dir):
    results_path = Path(results_dir)
    summary = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "broken": 0,
        "skipped": 0,
        "unknown": 0,
        "failed_cases": [],
    }

    if not results_path.exists():
        return summary

    for result_file in results_path.glob("*-result.json"):
        try:
            data = json.loads(result_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        status = data.get("status") or "unknown"
        summary["total"] += 1
        summary[status if status in summary else "unknown"] += 1

        if status in {"failed", "broken"}:
            summary["failed_cases"].append(
                {
                    "name": data.get("fullName") or data.get("name") or result_file.stem,
                    "status": status,
                    "message": (data.get("statusDetails") or {}).get("message", ""),
                }
            )

    return summary


def _build_card(summary, job_name, build_number, build_url, report_url):
    failed_count = summary["failed"] + summary["broken"]
    success = failed_count == 0
    title = "UI 自动化测试通过" if success else "UI 自动化测试失败"
    color = "green" if success else "red"

    fields = [
        f"**任务**：{job_name}",
        f"**构建号**：{build_number}",
        f"**总数**：{summary['total']}",
        f"**通过**：{summary['passed']}",
        f"**失败**：{summary['failed']}",
        f"**异常**：{summary['broken']}",
        f"**跳过**：{summary['skipped']}",
        f"**时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    if build_url:
        fields.append(f"**Jenkins**：[打开构建]({build_url})")
    if report_url:
        fields.append(f"**Allure**：[查看报告]({report_url})")

    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "\n".join(fields),
            },
        }
    ]

    if summary["failed_cases"]:
        case_lines = []
        for case in summary["failed_cases"][:10]:
            message = case["message"].splitlines()[0] if case["message"] else ""
            case_lines.append(f"- `{case['status']}` {case['name']} {message}")
        elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**失败用例 Top 10**\n" + "\n".join(case_lines),
                },
            }
        )

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": color,
                "title": {"tag": "plain_text", "content": title},
            },
            "elements": elements,
        },
    }


def _post_json(webhook, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        webhook,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read().decode("utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default="allure-results")
    parser.add_argument("--webhook", default=os.getenv("FEISHU_WEBHOOK", ""))
    parser.add_argument("--job-name", default=os.getenv("JOB_NAME", "UI Auto Test"))
    parser.add_argument("--build-number", default=os.getenv("BUILD_NUMBER", "local"))
    parser.add_argument("--build-url", default=os.getenv("BUILD_URL", ""))
    parser.add_argument("--report-url", default=os.getenv("ALLURE_REPORT_URL", ""))
    args = parser.parse_args()

    if not args.webhook:
        print("FEISHU_WEBHOOK is empty, skip feishu notification.")
        return 0

    summary = _load_allure_results(args.results_dir)
    payload = _build_card(
        summary=summary,
        job_name=args.job_name,
        build_number=args.build_number,
        build_url=args.build_url,
        report_url=args.report_url,
    )

    try:
        print(_post_json(args.webhook, payload))
    except urllib.error.URLError as exc:
        print(f"Failed to send feishu notification: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
