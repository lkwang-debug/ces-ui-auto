# -*- coding: utf-8 -*-
from pages.FeatureActionsPage import FeatureActionsPage


class MeetingLogPage(FeatureActionsPage):
    group_name, item_name = "日志管理", "会议日志"
    def open_logs(self): return self.open_page(self.group_name, self.item_name)
    def clear_search(self):
        # Clear is the right-most page toolbar action in this 4.39.7 log view.
        buttons = [item for item in self.driver.find_elements("css selector", "main button") if item.is_displayed()]
        if not buttons:
            return False
        self.driver.execute_script("arguments[0].click()", buttons[-1])
        return True
