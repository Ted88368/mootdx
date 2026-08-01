"""ServerManager / AutoSwitchClient 单元测试 (不联网)."""

import unittest.mock

from mootdx2.quotes import AutoSwitchClient
from mootdx2.server import ServerManager

HQ_HOSTS = [('site-a', '10.0.0.1', 7709), ('site-b', '10.0.0.2', 7709), ('site-c', '10.0.0.3', 7709)]


def patch_config(bestip=None, servers=None):
    """把 mock 数据注入 mootdx2.config.settings."""
    settings = {'SERVER': {'HQ': servers or HQ_HOSTS}, 'BESTIP': {'HQ': bestip or ''}}

    patcher = unittest.mock.patch('mootdx2.config.settings', settings)
    patcher.start()
    return patcher


class FakeApi:
    """模拟 tdxpy API: 依次返回预设结果, 记录 connect/disconnect."""

    def __init__(self, results=None, connect_ok=True, raise_on=None):
        self.results = list(results or [])
        self.connect_ok = connect_ok
        self.raise_on = raise_on
        self.calls = 0
        self.connects = []
        self.disconnects = 0

    def get_security_bars(self, *args, **kwargs):
        self.calls += 1

        if self.raise_on and self.calls == self.raise_on:
            raise ConnectionError('mock network error')

        return self.results.pop(0) if self.results else []

    def connect(self, ip, port, time_out=None):
        self.connects.append((ip, int(port)))
        return self.connect_ok

    def disconnect(self):
        self.disconnects += 1


def test_default_candidates_bestip_first_and_dedup():
    patcher = patch_config(bestip=('10.0.0.2', 7709))
    try:
        manager = ServerManager('HQ')
        assert manager.candidates == [('10.0.0.2', 7709), ('10.0.0.1', 7709), ('10.0.0.3', 7709)]
    finally:
        patcher.stop()


def test_default_candidates_without_bestip():
    patcher = patch_config()
    try:
        manager = ServerManager('HQ')
        assert manager.candidates == [('10.0.0.1', 7709), ('10.0.0.2', 7709), ('10.0.0.3', 7709)]
    finally:
        patcher.stop()


def test_report_failure_switches_at_threshold():
    manager = ServerManager('HQ', candidates=[('10.0.0.1', 7709), ('10.0.0.2', 7709)], threshold=3)

    assert manager.report_failure() is False
    assert manager.report_failure() is False
    assert manager.report_failure() is True
    assert manager.current_server() == ('10.0.0.2', 7709)


def test_report_success_resets_failures():
    manager = ServerManager('HQ', candidates=[('10.0.0.1', 7709), ('10.0.0.2', 7709)], threshold=3)

    manager.report_failure()
    manager.report_failure()
    manager.report_success()
    assert manager.report_failure() is False
    assert manager.report_failure() is False
    assert manager.report_failure() is True


def test_threshold_one_switches_immediately():
    manager = ServerManager('HQ', candidates=[('10.0.0.1', 7709), ('10.0.0.2', 7709)], threshold=1)

    assert manager.report_failure() is True
    assert manager.current_server() == ('10.0.0.2', 7709)


def test_mark_connected_syncs_cursor():
    manager = ServerManager('HQ', candidates=[('10.0.0.1', 7709), ('10.0.0.2', 7709)], threshold=3)

    manager.mark_connected('10.0.0.2', 7709)
    assert manager.current_server() == ('10.0.0.2', 7709)


def test_autoswitch_retries_on_new_server():
    manager = ServerManager('HQ', candidates=[('10.0.0.1', 7709), ('10.0.0.2', 7709)], threshold=3)
    api = FakeApi(results=[None, None, None, 'ok'])
    client = AutoSwitchClient(api, manager, timeout=1)

    assert client.get_security_bars(9, 1, '600036', 0, 100) is None
    assert client.get_security_bars(9, 1, '600036', 0, 100) is None

    # 第三次失败触发切换, 并在新服务器上重试成功
    assert client.get_security_bars(9, 1, '600036', 0, 100) == 'ok'
    assert manager.current_server() == ('10.0.0.2', 7709)
    assert api.connects == [('10.0.0.2', 7709)]
    assert api.disconnects == 1


def test_autoswitch_success_resets_counter():
    manager = ServerManager('HQ', candidates=[('10.0.0.1', 7709), ('10.0.0.2', 7709)], threshold=3)
    api = FakeApi(results=[None, 'ok', None, None, None, 'ok'])
    client = AutoSwitchClient(api, manager, timeout=1)

    assert client.get_security_bars(9, 1, '600036', 0, 100) is None
    assert client.get_security_bars(9, 1, '600036', 0, 100) == 'ok'  # 成功清零
    assert client.get_security_bars(9, 1, '600036', 0, 100) is None
    assert client.get_security_bars(9, 1, '600036', 0, 100) is None
    assert client.get_security_bars(9, 1, '600036', 0, 100) == 'ok'  # 又触发切换并成功
    assert api.disconnects == 1


def test_autoswitch_exception_counts_as_failure():
    manager = ServerManager('HQ', candidates=[('10.0.0.1', 7709), ('10.0.0.2', 7709)], threshold=2)
    api = FakeApi(results=[None, None, 'ok'], raise_on=3)
    client = AutoSwitchClient(api, manager, timeout=1)

    # 前两次返回 None, 第3次调用抛异常 → 累计第2次失败 → 切换服务器
    assert client.get_security_bars(9, 1, '600036', 0, 100) is None
    assert client.get_security_bars(9, 1, '600036', 0, 100) is None
    assert manager.current_server() == ('10.0.0.2', 7709)
    assert api.disconnects == 1
    # 新服务器上重试成功
    assert client.get_security_bars(9, 1, '600036', 0, 100) == 'ok'


def test_autoswitch_failure_below_threshold_surfaces():
    manager = ServerManager('HQ', candidates=[('10.0.0.1', 7709), ('10.0.0.2', 7709)], threshold=3)
    api = FakeApi(results=[None, None])
    client = AutoSwitchClient(api, manager, timeout=1)

    assert client.get_security_bars(9, 1, '600036', 0, 100) is None
    assert api.disconnects == 0
    assert manager.current_server() == ('10.0.0.1', 7709)
