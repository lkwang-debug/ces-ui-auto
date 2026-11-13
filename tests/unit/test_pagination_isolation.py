import pytest

from common.test_preconditions import pagination_records


class Page:
    def __init__(self):
        self.rows={f'existing-{index}' for index in range(9)}

    def reset_search(self):return True
    def get_total_record_count(self):return len(self.rows)
    def wait_until(self,condition,**kwargs):return condition()


def test_failure_after_preparation_removes_only_this_cases_rows():
    page=Page()
    original=set(page.rows)
    def create(identifier):page.rows.add(identifier);return True
    def remove(identifier):page.rows.remove(identifier);return True
    with pytest.raises(RuntimeError,match='business assertion'):
        with pagination_records(page,lambda:True,create,remove,'UIUNIT'):
            assert len(page.rows)==11
            raise RuntimeError('business assertion')
    assert page.rows==original


def test_cleanup_failure_is_reported_without_abandoning_other_owned_rows():
    page=Page()
    attempted=[]
    def create(identifier):page.rows.add(identifier);return True
    def remove(identifier):
        attempted.append(identifier)
        if len(attempted)==1:raise RuntimeError('delete unavailable')
        page.rows.remove(identifier);return True
    with pytest.raises(AssertionError,match='清理失败'):
        with pagination_records(page,lambda:True,create,remove,'UIUNIT'):pass
    assert len(attempted)==2
    assert len(page.rows)==10
