from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from datetime import datetime
import re
from conf.conf import ConfigManager
from common.ui_state import click_toolbar_search, wait_query_finished

from pages.FeatureActionsPage import FeatureActionsPage


def has_record_detail_content(evidence):
    """Require rendered business content, independent of the selected AI template."""
    summary = (evidence.get('summary_content') or '').strip()
    summary_ready = bool(summary) and not any(
        marker in summary for marker in ('暂无会议纪要', '暂无纪要', '正在生成', '加载中')
    )
    recording_ready = any(
        re.search(r'\.(mp4|mkv|webm|wav|mp3)$', item.get('name', ''), re.I)
        and re.fullmatch(r'\d{2,}:\d{2}:\d{2}', item.get('duration', ''))
        and item.get('download_available')
        for item in evidence.get('recordings', [])
    )
    return bool(summary_ready or recording_ready)


class MeetingRecordsPage(FeatureActionsPage):
    group_name, item_name = "会议管理", "会议记录"

    def open_records(self):
        return self.open_page(self.group_name, self.item_name)

    def sort_by_duration(self):
        buttons = [item for item in self.driver.find_elements("css selector", "main button") if item.is_displayed()]
        # On this page export is first and duration sort is the second toolbar button.
        if len(buttons) < 2:
            return False
        self.driver.execute_script("arguments[0].click()", buttons[1])
        return True

    def search_by_room(self, room_name, room_id):
        self.open_records()
        return self.fill_first_inputs(["", "", room_name, room_id]) and self.submit_and_wait()

    def clear_search(self):
        buttons = [item for item in self.driver.find_elements("css selector", "main button") if item.is_displayed()]
        if not buttons:
            return False
        # Header clear is the right-most filter bar button.
        self.driver.execute_script("arguments[0].click()", buttons[-1])
        return True

    def available_record_action_titles(self):
        self.prepare_detail_target()
        return self.driver.execute_script(
            """
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            return [...new Set([...document.querySelectorAll('[data-ces-detail] td:last-child [title]')]
              .filter(visible).map(e => e.title).filter(Boolean))];
            """
        )

    def prepare_detail_target(self):
        if not self.open_records():
            raise AssertionError('会议记录页面未完成导航，不能读取详情前置')
        match = re.search(r'_(\d+)_(\d{14})', ConfigManager.RECORD_TASK_KEYWORD)
        room = ConfigManager.MEETING_RECORD_ROOM_ID or (match.group(1) if match else '')
        anchor = ConfigManager.MEETING_RECORD_START_TIME or (datetime.strptime(match.group(2),'%Y%m%d%H%M%S').strftime('%Y-%m-%d %H:%M:%S') if match else '')
        if not room or not anchor:
            raise AssertionError('前置条件：会议详情需要配置固定会议室ID与开始时间或可解析的录制任务')
        field = self.wait_until(lambda: self.driver.execute_script(
            """
            return [...document.querySelectorAll('main input')].find(e=>e.offsetParent!==null&&
              e.closest('.search-box,.ant-input-group-wrapper')?.innerText.includes('会议室ID'))||null;
            """
        ), timeout=8, poll_frequency=0.1)
        if field is False:
            raise AssertionError('会议记录的会议室ID搜索字段未显示')
        field.click();field.send_keys(Keys.CONTROL,'a');field.send_keys(Keys.DELETE);field.send_keys(room)
        started = self.driver.execute_script('return performance.now()')
        if not click_toolbar_search(self.driver,field) or not wait_query_finished(self,started):
            raise AssertionError('固定会议记录查询未完成')
        pinned = getattr(self,'_detail_start',None)
        anchor_time = datetime.strptime(anchor,'%Y-%m-%d %H:%M:%S')
        for _ in range(30):
            rows = self.driver.execute_script(
                """
                return [...document.querySelectorAll('main tbody tr')].filter(r=>r.offsetParent!==null&&!r.classList.contains('ant-table-measure-row'))
                  .map(r=>({room:r.querySelectorAll('td')[0]?.innerText.trim(),start:r.querySelectorAll('td')[4]?.innerText.trim()}));
                """
            )
            candidates=[]
            for row in rows:
                if row.get('room') != room or not row.get('start'):
                    continue
                stamp=datetime.strptime(row['start'],'%Y-%m-%d %H:%M:%S')
                distance=abs((stamp-anchor_time).total_seconds())
                if (pinned and row['start']==pinned) or (not pinned and distance<=120):
                    candidates.append((distance,row['start']))
            if candidates:
                self._detail_start = min(candidates)[1]
                marked = self.driver.execute_script(
                    """
                    document.querySelectorAll('[data-ces-detail]').forEach(e=>e.removeAttribute('data-ces-detail'));
                    const rows=[...document.querySelectorAll('main tbody tr')].filter(r=>r.offsetParent!==null&&
                      r.querySelectorAll('td')[0]?.innerText.trim()===arguments[0]&&r.querySelectorAll('td')[4]?.innerText.trim()===arguments[1]);
                    if(rows.length!==1)return false;rows[0].setAttribute('data-ces-detail','true');return true;
                    """, room,self._detail_start,
                )
                if not marked:
                    raise AssertionError('固定会议记录定位不唯一')
                return
            next_button=self.find_visible_now((By.CSS_SELECTOR,'main .ant-pagination-next:not(.ant-pagination-disabled)'))
            if next_button is False:
                break
            started=self.driver.execute_script('return performance.now()');next_button.click()
            if not wait_query_finished(self,started):
                raise AssertionError('固定会议记录翻页请求未完成')
        raise AssertionError(f'前置条件：未找到固定会议记录 {room} / {pinned or anchor}')

    def open_record_action(self, title):
        """Open one read-only meeting-record action and return observable evidence."""
        self.prepare_detail_target()
        target_count = self.driver.execute_script(
            """
            const title=arguments[0]; const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            return [...document.querySelectorAll('[data-ces-detail] td:last-child [title]')]
              .filter(e => visible(e) && e.title === title).length;
            """,
            title,
        ) or 0
        last_evidence = None
        for target_index in range(min(int(target_count), 8)):
            self.open_records()
            previous_text = self._page_body_text()
            clicked = self.driver.execute_script(
            """
            const title=arguments[0], index=arguments[1];
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const target=[...document.querySelectorAll('[data-ces-detail] td:last-child [title]')]
              .filter(e => visible(e) && e.title === title)[index];
            if (!target) return false; target.click(); return true;
            """,
            title,
                target_index,
            )
            if not clicked:
                continue

            if title == "录制与纪要":
                def rendered_content():
                    nonlocal last_evidence
                    evidence = self.driver.execute_script("""
                      const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                      const text=e=>e&&visible(e)?e.innerText.trim():'';
                      const summary=[...document.querySelectorAll('.meeting-summary .summary-body .marked')].find(visible);
                      return {summary_content:text(summary),recordings:
                        [...document.querySelectorAll('.recording-item')].filter(visible).map(e=>({
                          name:text(e.querySelector('.recording-info .name')),
                          duration:text(e.querySelector('.recording-info .duration')),
                          download_available:[...e.querySelectorAll('[aria-label="download"], [title="下载"]')].some(visible)
                        })),text:(document.body.innerText||'').replace(/\\s+/g,' ').trim()};
                    """)
                    evidence.update(title=title, route=self.driver.current_url, headers=[])
                    last_evidence = evidence
                    if self._page_body_text() != previous_text and has_record_detail_content(evidence):
                        return evidence
                    return False

                loaded = self.wait_until(rendered_content, timeout=12, poll_frequency=.2)
                if loaded is not False:
                    return loaded
                continue

            modal = self.wait_until(
            lambda: self.driver.execute_script(
                """
                const title=arguments[0]; const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                return [...document.querySelectorAll('.ant-modal-content')].filter(visible)
                  .find(e => (e.querySelector('.ant-modal-title')?.innerText || '').trim() === title) || null;
                """,
                title,
            ),
            timeout=5,
            poll_frequency=.2,
            )
            if modal is False:
                continue
            self.wait_until(
                lambda: bool(modal.find_elements(By.CSS_SELECTOR, "th"))
                or "暂无数据" in (modal.text or ""),
                timeout=4,
                poll_frequency=.1,
            )
            evidence = self.driver.execute_script(
            """
            const modal=arguments[0];
            return {
              title:(modal.querySelector('.ant-modal-title')?.innerText || '').trim(),
              text:(modal.innerText || '').replace(/\s+/g,' ').trim(),
              headers:[...modal.querySelectorAll('th')].map(e => (e.innerText || '').trim()).filter(Boolean),
            };
            """,
                modal,
            )
            last_evidence = evidence
            close = modal.find_element(By.CSS_SELECTOR, "button.ant-modal-close")
            self.driver.execute_script("arguments[0].click()", close)
            self.wait_until(lambda: not modal.is_displayed(), timeout=3, poll_frequency=.1)
            if (
                evidence["headers"]
                or title in {"投票结果", "签到结果"}
                or (title == "参会人详情" and "全部下载" in evidence["text"])
            ):
                return evidence
        return last_evidence

    def _page_body_text(self):
        return self.driver.execute_script(
            "return (document.body.innerText || '').replace(/\\s+/g,' ').trim()"
        )
