"""WebUI 功能测试：主导航 / 各页面渲染 / 关键交互（Playwright + Chromium headless）。

依赖：被测服务已启动（./tests/run_tests.sh），浏览器路径可用
BS_CHROMIUM_PATH 覆盖（默认取项目开发环境缓存）。
"""

from __future__ import annotations

import os

import pytest
from playwright.sync_api import sync_playwright

import tests.helpers as helpers

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


def test_perf_create_threshold_mode(page):
    """阈值模式创建页：TTFT/TPOT(Mean/Median/P99)+Output 三行阈值；三者全 0 不能下一步并提醒。"""
    page.goto(f"{BASE_URL}/performance/create?mode=threshold", wait_until="domcontentloaded")
    _visible(page, ".perf-create-page")
    _visible(page, ".condition-panel")

    # 三行阈值输入：TTFT / TPOT / Output token throughput
    assert page.locator(".threshold-field").count() == 3
    # 两个统计量选择器（TTFT/TPOT）默认 Mean
    sel_texts = page.locator(".threshold-field .ant-select-selection-item").all_inner_texts()
    assert [s for s in sel_texts if s == "Mean"], f"expected Mean selects, got {sel_texts}"
    # 默认值：TTFT=0、TPOT=100、Output=0
    nums = page.locator(".threshold-field .ant-input-number-input")
    vals = nums.evaluate_all("els => els.map(e => e.value)")
    vals = [v for v in vals if v not in (None, "")]
    assert vals[:3] == ["0", "100", "0"], f"expected [0,100,0] defaults, got {vals[:3]}"

    # 三者全部置 0 → 不能进入下一步，并弹出提醒
    nums.nth(0).fill("0")
    nums.nth(1).fill("0")
    nums.nth(2).fill("0")
    page.locator(".panel-footer button").filter(has_text="Next").first.click()
    _visible(page, ".ant-message", timeout=8000)
    msg = page.locator(".ant-message").inner_text()
    assert "cannot all be 0" in msg, f"unexpected message: {msg}"
    # 仍停留在 Step1（条件面板可见，未跳转 Step2）
    assert page.locator(".condition-panel").is_visible()


def test_settings_benches_panel(page):
    """Settings → Bench 引擎栏：三个内置引擎（自研 / vllm-0.23 / sglang-0.5.10）
    + 介绍文案 + 环境校验结果 + 引擎对比表。"""
    page.goto(f"{BASE_URL}/settings", wait_until="domcontentloaded")
    _visible(page, ".settings-page")

    # 切换到 Bench 引擎栏（菜单项文本：Bench Engines）
    page.locator(".menu-item").filter(has_text="Bench Engines").first.click()
    _visible(page, ".bench-list", timeout=15000)

    cards = page.locator(".bench-card")
    assert cards.count() == 3, f"expected 3 engines, got {cards.count()}"

    names = page.locator(".bench-name").all_inner_texts()
    joined = " | ".join(names)
    assert "BenchScope" in joined, f"缺少自研引擎: {joined}"
    assert "vllm-0.23" in joined or "0.23" in joined, f"缺少 vllm-0.23: {joined}"
    assert "sglang-0.5.10" in joined or "0.5.10" in joined, f"缺少 sglang-0.5.10: {joined}"

    # 每个引擎有介绍文案
    descs = page.locator(".bench-desc").all_inner_texts()
    assert len(descs) == 3 and all(d.strip() for d in descs), f"引擎介绍缺失: {descs}"

    # 自研引擎（第 1 张卡）环境恒满足；原生引擎展示环境要求明细
    first_env = cards.nth(0).locator(".ant-tag").all_inner_texts()
    assert "Ready" in " ".join(first_env), f"自研引擎环境应恒满足: {first_env}"
    assert cards.nth(1).locator(".bench-env-row").count() >= 2, "vllm 引擎应展示 torch/vllm 环境要求行"

    # 对比表：维度列 + 各引擎取值
    _visible(page, ".compare-table")
    assert page.locator(".compare-table tbody tr").count() >= 3


def test_perf_create_engine_select_and_env_block(page):
    """创建页引擎选择：默认自研引擎（可用）；切到原生引擎且环境不满足时禁止进入下一步。"""
    page.goto(f"{BASE_URL}/performance/create?mode=concurrency", wait_until="domcontentloaded")
    _visible(page, ".perf-create-page")
    _visible(page, ".bench-picker", timeout=15000)

    # 默认引擎为自研 bench（无框架环境依赖，标签显示 Ready）
    tags = page.locator(".bench-picker .ant-tag").all_inner_texts()
    assert any("Ready" in x for x in tags), f"默认引擎环境应可用: {tags}"

    # 选择原生引擎 vllm-0.23 → 环境校验（本机未安装 → Not Satisfied）
    page.locator(".bench-picker .ant-select").first.click()
    _visible(page, ".ant-select-dropdown", timeout=8000)
    page.locator(".ant-select-item-option").filter(has_text="vLLM Bench").first.click()
    # 等待环境校验完成（标签变为 Ready / Not Satisfied）
    page.wait_for_function(
        "() => { const t = document.querySelector('.bench-picker .ant-tag');"
        " return t && /Ready|Not Satisfied/.test(t.textContent); }",
        timeout=15000,
    )
    tags = page.locator(".bench-picker .ant-tag").all_inner_texts()
    # 环境不满足时展示安装提示或环境明细；满足时直接进入下一步
    if any("Not Satisfied" in x for x in tags):
        assert page.locator(".bench-env-row").count() >= 2, "环境不满足应展示逐项检查结果"
        assert page.locator(".bench-hint").count() >= 1, "环境不满足应展示安装提示"
        # 点击下一步 → 被阻断，仍停留在 Step1
        page.locator(".panel-footer button").filter(has_text="Next").first.click()
        _visible(page, ".ant-message", timeout=8000)
        msg = page.locator(".ant-message").inner_text()
        assert "Environment not satisfied" in msg, f"unexpected message: {msg}"
        assert page.locator(".condition-panel").is_visible()


def test_datas_perfs_record_list(page):
    """Datas/Perfs 记录面板与导入入口。"""
    page.goto(f"{BASE_URL}/datas/perfs", wait_until="domcontentloaded")
    _visible(page, ".perfs-page")
    _visible(page, ".record-panel")
    # 导入按钮存在
    assert page.locator(".record-panel-title .icon-btn").count() >= 1


def test_threshold_cond_in_case_group(page):
    """阈值信息并入 case 分组标记右侧：Performance 执行页 + Datas/Perfs Cases Info 不再单独显示阈值块。
    阈值信息跟随每组请求配置（length_pairs 第 5 元素），标识含统计量（TTFT-Mean/Median/P99、TPOT-Mean/Median/P99）。"""
    import requests as req

    snap = helpers.create_and_run_task(
        req,
        BASE_URL,
        {
            "mode": "threshold",
            # 阈值信息在每组请求配置中，不跟随主任务
            "dataset": {
                "type": "random",
                "length_pairs": [[64, 64, "用例A", "case-a", {
                    "ttft_statistic": "mean", "ttft_threshold_ms": 50,
                    "tpot_statistic": "median", "tpot_threshold_ms": 100,
                    "output_throughput_threshold": 200,
                }]],
            },
        },
        timeout=120,
    )
    task_id = snap["task_id"]
    try:
        # 1) Performance 任务执行页：阈值文本在分组标记右侧（含统计量标识），无独立阈值区块
        page.goto(f"{BASE_URL}/performance", wait_until="domcontentloaded")
        _visible(page, ".perf-detail")
        _visible(page, ".case-threshold")
        assert page.locator(".threshold-conds").count() == 0
        text = page.locator(".case-threshold").first.inner_text()
        assert "TTFT-Mean ≤ 50ms" in text and "TPOT-Median ≤ 100ms" in text and "Output ≤ 200 tok/s" in text, text

        # 2) Datas/Perfs Cases Info 面板：同样并入分组标记右侧，无独立阈值 info-row
        page.goto(f"{BASE_URL}/datas/perfs?run_id={helpers.run_id_of(task_id)}", wait_until="domcontentloaded")
        _visible(page, ".perfs-page")
        cases_card = page.locator(".half-card", has=page.locator(".case-groups"))
        cases_card.locator(".case-threshold").first.wait_for(state="visible", timeout=10000)
        assert cases_card.locator(".info-row").count() == 0
    finally:
        req.delete(f"{BASE_URL}/api/tasks/{task_id}", timeout=10)


def test_group_threshold_in_data_tables(page):
    """分组阈值展示到数据表格：Performance Realtime Data 分组标题行（.group-threshold）
    与 Datas/Perfs Perf Datas 分组 tab 内（.group-threshold-bar），文本含统计量标识。"""
    import requests as req

    snap = helpers.create_and_run_task(
        req,
        BASE_URL,
        {
            "mode": "threshold",
            "dataset": {
                "type": "random",
                "length_pairs": [[64, 64, "用例A", "case-a", {
                    "ttft_statistic": "mean", "ttft_threshold_ms": 50,
                    "tpot_statistic": "median", "tpot_threshold_ms": 100,
                    "output_throughput_threshold": 200,
                }]],
            },
        },
        timeout=120,
    )
    task_id = snap["task_id"]
    try:
        # 1) Performance 执行页：Realtime Data 分组标题行展示该组阈值（跟随 Groups）
        page.goto(f"{BASE_URL}/performance", wait_until="domcontentloaded")
        _visible(page, ".perf-detail")
        _visible(page, ".metrics-table .group-title", timeout=15000)
        gtext = page.locator(".metrics-table .group-threshold").first.inner_text()
        assert "TTFT-Mean ≤ 50ms" in gtext and "TPOT-Median ≤ 100ms" in gtext and "Output ≤ 200 tok/s" in gtext, gtext

        # 2) Datas/Perfs Perf Datas：分组 tab 内阈值条展示该组阈值
        page.goto(f"{BASE_URL}/datas/perfs?run_id={helpers.run_id_of(task_id)}", wait_until="domcontentloaded")
        _visible(page, ".perfs-page")
        bar = page.locator(".group-threshold-bar")
        bar.first.wait_for(state="visible", timeout=10000)
        btext = bar.first.inner_text()
        assert "TTFT-Mean ≤ 50ms" in btext and "TPOT-Median ≤ 100ms" in btext and "Output ≤ 200 tok/s" in btext, btext
    finally:
        req.delete(f"{BASE_URL}/api/tasks/{task_id}", timeout=10)


def test_legacy_task_threshold_fallback(page):
    """旧格式任务（阈值在任务级，cases 无 per-group 阈值）兼容：
    Performance Cases 面板与 Datas/Perfs Cases Info 回退显示任务级阈值（含统计量标识）。"""
    import requests as req

    snap = helpers.create_and_run_task(
        req,
        BASE_URL,
        {
            "mode": "threshold",
            "tpot_threshold_ms": 80,
            "tpot_statistic": "mean",
            "ttft_threshold_ms": 0,
            "output_throughput_threshold": 0,
            "dataset": {
                "type": "random",
                "length_pairs": [[64, 64, "用例B", "case-b"]],
            },
        },
        timeout=120,
    )
    task_id = snap["task_id"]
    try:
        page.goto(f"{BASE_URL}/performance", wait_until="domcontentloaded")
        _visible(page, ".perf-detail")
        _visible(page, ".case-threshold", timeout=15000)
        ctext = page.locator(".case-threshold").first.inner_text()
        assert "TPOT-Mean ≤ 80ms" in ctext, ctext
        # 旧格式任务回退任务级阈值 → Realtime Data 标记 BestPerf 高亮行（行背景色恢复）
        best_row2 = page.locator(".metrics-table .row-bestperf").first
        best_row2.wait_for(state="visible", timeout=10000)
        assert best_row2.locator("td").count() > 0

        page.goto(f"{BASE_URL}/datas/perfs?run_id={helpers.run_id_of(task_id)}", wait_until="domcontentloaded")
        _visible(page, ".perfs-page")
        _visible(page, ".case-threshold", timeout=10000)
        dtext = page.locator(".case-threshold").first.inner_text()
        assert "TPOT-Mean ≤ 80ms" in dtext, dtext
        # 旧格式任务回退任务级阈值 → Perf Datas 标记 BestPerf 高亮行（行背景色恢复）
        best_row = page.locator(".metrics-table .row-bestperf").first
        best_row.wait_for(state="visible", timeout=10000)
        assert best_row.locator("td").count() > 0
    finally:
        req.delete(f"{BASE_URL}/api/tasks/{task_id}", timeout=10)


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
