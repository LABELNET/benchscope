"""WebUI 功能测试：主导航 / 各页面渲染 / 关键交互（Playwright + Chromium headless）。

依赖：被测服务已启动（./tests/run_tests.sh），浏览器路径可用
BS_CHROMIUM_PATH 覆盖（默认取项目开发环境缓存）。
"""

from __future__ import annotations

import os

import pytest
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("BS_TEST_URL", "http://127.0.0.1:18081")
CHROMIUM = os.environ.get(
    "BS_CHROMIUM_PATH",
    "/home/yuanmingzhuo/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome",
)

# (导航菜单 index, 期望 URL path, 页面容器选择器)
PAGES = [
    (0, "/dashboard", ".dashboard-page"),
    (1, "/performance", ".perf-page"),
    (2, "/accuracy", ".accuracy-page"),
    (3, "/sessions", ".sessions-page"),
    (4, "/datas", ".perfs-page"),
    (5, "/settings", ".settings-page"),
]


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROMIUM, headless=True)
        yield b
        b.close()


@pytest.fixture()
def page(browser):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    yield pg
    ctx.close()


def _visible(page, selector: str, timeout: float = 15000):
    page.locator(selector).first.wait_for(state="visible", timeout=timeout)


def test_landing_dashboard(page):
    """首页 / 重定向到 Dashboard 并渲染。"""
    page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
    _visible(page, ".dashboard-page")
    assert page.locator(".brand-name").first.inner_text().strip() == "BenchScope"


@pytest.mark.parametrize("idx,path,selector", PAGES, ids=[p[1] for p in PAGES])
def test_direct_navigation(page, idx, path, selector):
    """直接访问每个页面路由，页面容器渲染。"""
    page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded")
    _visible(page, selector)


def test_topbar_menu_navigation(page):
    """点击 TopBar 导航菜单可到达各页面（避免依赖文案语言）。"""
    page.goto(f"{BASE_URL}/dashboard", wait_until="domcontentloaded")
    _visible(page, ".dashboard-page")

    for idx, path, selector in PAGES:
        menu = page.locator(".nav-menu li.ant-menu-item").nth(idx)
        menu.click()
        _visible(page, selector)


def test_performance_intro_actions(page):
    """Performance 页面渲染：无任务时展示模式入口，有任务时展示详情（兼容 API 测试留下的任务）。"""
    page.goto(f"{BASE_URL}/performance", wait_until="domcontentloaded")
    _visible(page, ".perf-page")
    if page.locator(".perf-intro").count() > 0:
        assert page.locator(".perf-intro .ant-btn").count() >= 2
    else:
        _visible(page, ".perf-detail")


def test_perf_create_form(page):
    """Perf 创建页三步表单渲染。"""
    page.goto(f"{BASE_URL}/performance/create?mode=concurrency", wait_until="domcontentloaded")
    _visible(page, ".perf-create-page")
    assert page.locator(".ant-steps").count() >= 1


def test_datas_perfs_record_list(page):
    """Datas/Perfs 记录面板与导入入口。"""
    page.goto(f"{BASE_URL}/datas/perfs", wait_until="domcontentloaded")
    _visible(page, ".perfs-page")
    _visible(page, ".record-panel")
    # 导入按钮存在
    assert page.locator(".record-panel-title .icon-btn").count() >= 1


def test_settings_sidebar(page):
    """Settings 侧边菜单与内容区。"""
    page.goto(f"{BASE_URL}/settings", wait_until="domcontentloaded")
    _visible(page, ".settings-page")
    _visible(page, ".settings-sidebar .sidebar-title")


def test_sessions_new_chat(page):
    """Sessions 新建会话 -> 列表出现会话项。"""
    page.goto(f"{BASE_URL}/sessions", wait_until="domcontentloaded")
    _visible(page, ".sessions-page")
    btn = page.locator(".new-session-btn")
    btn.click()
    page.locator(".session-item").first.wait_for(state="visible", timeout=10000)


def test_spa_fallback(page):
    """未知非 api 路径由 SPA fallback 返回应用（TopBar 渲染）。"""
    page.goto(f"{BASE_URL}/nonexistent-page", wait_until="domcontentloaded")
    _visible(page, ".topbar")
