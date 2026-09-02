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


def _open_benches_tab(page):
    """切到 Settings → Bench Engines 栏并等列表就绪。"""
    page.goto(f"{BASE_URL}/settings", wait_until="domcontentloaded")
    _visible(page, ".settings-page")
    page.locator(".menu-item").filter(has_text="Bench Engines").first.click()
    _visible(page, ".bench-list", timeout=15000)


def test_settings_benches_panel(page):
    """Settings → Bench Engines 栏：内置引擎列表（1.0.8 起为 5 个：Bench CLI / vllm-0.23 /
    sglang-0.5.10 / native-hf / mock）+ 介绍文案 + 环境校验结果。"""
    _open_benches_tab(page)

    cards = page.locator(".bench-card")
    assert cards.count() == 5, f"expected 5 engines, got {cards.count()}"

    names = page.locator(".bench-name").all_inner_texts()
    joined = " | ".join(names)
    # 自研引擎统一命名为 Bench CLI
    assert "Bench CLI" in joined, f"缺少 Bench CLI 自研引擎: {joined}"
    assert "vllm-0.23" in joined or "0.23" in joined, f"缺少 vllm-0.23: {joined}"
    assert "sglang-0.5.10" in joined or "0.5.10" in joined, f"缺少 sglang-0.5.10: {joined}"

    # 每个引擎有介绍文案
    descs = page.locator(".bench-desc").all_inner_texts()
    assert len(descs) == 5 and all(d.strip() for d in descs), f"引擎介绍缺失: {descs}"
    # 1.0.8：精度引擎卡片存在
    assert "Native HF" in " | ".join(names), "缺少 native-hf 精度引擎"
    assert "Mock" in " | ".join(names), "缺少 mock 精度引擎"

    # 自研引擎（第 1 张卡）环境恒满足；原生引擎展示环境要求明细
    first_env = cards.nth(0).locator(".ant-tag").all_inner_texts()
    assert "Ready" in " ".join(first_env), f"自研引擎环境应恒满足: {first_env}"
    assert cards.nth(1).locator(".bench-env-row").count() >= 2, "vllm 引擎应展示 torch/vllm 环境要求行"


def test_settings_benches_topbar_actions(page):
    """Bench Engines 右上角三个文字按钮：Create Engine / Upload Engine / Engine Comparison。"""
    _open_benches_tab(page)

    actions = page.locator(".bench-actions .bench-text-btn")
    assert actions.count() == 3, f"右上角应有 3 个操作按钮, got {actions.count()}"

    labels = " ".join(actions.all_inner_texts())
    assert "Create Engine" in labels, f"缺少 Create Engine: {labels}"
    assert "Upload Engine" in labels, f"缺少 Upload Engine: {labels}"
    assert "Engine Comparison" in labels, f"缺少 Engine Comparison: {labels}"

    # 列表区可滑动（内部滚动容器）
    assert page.locator(".bench-list-scroll").count() == 1, "引擎列表应为独立可滚动容器"


def test_settings_benches_create_engine_modal(page):
    """Create Engine 文字按钮 → 中间弹框显示教程 + 上游链接 + 可复制提示词。"""
    _open_benches_tab(page)

    page.locator(".bench-actions .bench-text-btn").filter(has_text="Create Engine").click()
    _visible(page, ".bench-modal:visible", timeout=8000)

    modal = page.locator(".bench-modal:visible")
    # 制作步骤教程
    assert modal.locator(".bench-ol li").count() >= 3, "应展示制作步骤教程"
    # 上游仓库链接
    links = modal.locator("a[href*='github.com']").all_inner_texts()
    assert any("vllm" in x for x in links), f"缺少 vLLM 上游链接: {links}"
    assert any("sglang" in x for x in links), f"缺少 SGLang 上游链接: {links}"
    # 可复制提示词
    prompt = modal.locator(".bench-yaml-view").inner_text()
    assert "create a BenchScope custom bench engine" in prompt, f"提示词内容异常: {prompt[:120]}"
    # 弹框内不再展示引擎定义原文
    assert modal.locator(".bench-yaml-editor").count() == 0, "Create 弹框不应展示引擎定义编辑框"

    # 关闭
    modal.locator(".ant-modal-close").click()
    page.wait_for_timeout(500)


def test_settings_benches_upload_engine_modal(page):
    """Upload Engine 文字按钮 → 中间弹框显示上传区（支持 yaml / tar.gz）。"""
    _open_benches_tab(page)

    page.locator(".bench-actions .bench-text-btn").filter(has_text="Upload Engine").click()
    _visible(page, ".bench-modal:visible", timeout=8000)

    modal = page.locator(".bench-modal:visible")
    # 拖拽上传区（ant-design-vue 4 渲染为 .ant-upload-drag）
    _visible(page, ".bench-modal:visible .ant-upload-drag")
    hint = modal.inner_text()
    assert ".tar.gz" in hint, f"应说明支持 .tar.gz 技能包: {hint[:200]}"
    # 上传前「校验并导入」按钮不可用
    apply_btn = modal.locator("button").filter(has_text="Validate & Import").first
    assert apply_btn.is_disabled(), "未选择文件时导入按钮应禁用"

    modal.locator(".ant-modal-close").click()
    page.wait_for_timeout(500)


def test_settings_benches_comparison_modal(page):
    """Engine Comparison 文字按钮 → 中间弹框显示对比表（维度 × 引擎）。"""
    _open_benches_tab(page)

    # 默认不内联展示对比表
    assert page.locator(".bench-tab .compare-table").count() == 0, "对比表应移入弹框，不在页面内联"

    page.locator(".bench-actions .bench-text-btn").filter(has_text="Engine Comparison").click()
    _visible(page, ".bench-modal:visible", timeout=8000)

    modal = page.locator(".bench-modal:visible")
    _visible(page, ".bench-modal:visible .compare-table")
    # 维度行 + 五个引擎列
    assert modal.locator(".compare-table tbody tr").count() >= 3, "对比表应含多个维度"
    headers = modal.locator(".compare-table thead th").all_inner_texts()
    assert len(headers) == 6, f"表头应为 1 维度列 + 5 引擎列, got {headers}"

    modal.locator(".ant-modal-close").click()
    page.wait_for_timeout(500)


def test_perf_create_params_follow_engine(page):
    """创建任务 Step2：参数面板只显示当前所选引擎的参数，并展示引擎名称。"""
    page.goto(f"{BASE_URL}/performance/create?mode=concurrency", wait_until="domcontentloaded")
    _visible(page, ".perf-create-page")
    _visible(page, ".bench-picker", timeout=15000)

    # 默认自研引擎 → 进入 Step2（等待环境校验完成：任一状态 tag 出现）
    page.wait_for_function(
        "() => { const tags = [...document.querySelectorAll('.bench-picker .ant-tag')];"
        " return tags.some(t => /Ready|Not Satisfied|Real|Mock/.test(t.textContent)); }",
        timeout=15000,
    )
    page.locator(".panel-footer button").filter(has_text="Next").first.click()
    _visible(page, ".params-engine", timeout=10000)

    # 展示当前引擎名（Bench CLI）
    engine_text = page.locator(".params-engine").inner_text()
    assert "Bench CLI" in engine_text, f"Step2 应显示当前引擎: {engine_text}"

    # 不再展示 vllm / sglang 双框架参数 Tab
    assert page.locator(".ant-tabs-tab").filter(has_text="SGLang").count() == 0, \
        "Step2 不应再展示其他框架的参数 Tab"

    # 展示 Bench CLI 专属参数（Backend / Request Rate 等）
    keys = page.locator(".param-row").all_inner_texts()
    joined = " | ".join(keys)
    assert "Backend" in joined or "backend" in joined, f"缺少 Backend 参数: {joined[:200]}"

    # 参数 label 与说明（help/选项描述）默认显示英文（不含中文）
    keys = page.locator(".param-row").all_inner_texts()
    joined_en = " | ".join(keys)
    assert not any("\u4e00" <= ch <= "\u9fff" for ch in joined_en), \
        f"默认语言应为英文，不应含中文: {joined_en[:200]}"
    descs_en = " | ".join(page.locator(".param-desc").all_inner_texts())
    assert any(ch.isascii() and ch.isalpha() for ch in descs_en), \
        f"参数描述默认应为英文: {descs_en[:200]}"
    assert not any("\u4e00" <= ch <= "\u9fff" for ch in descs_en), \
        f"参数描述默认应为英文，不应含中文: {descs_en[:200]}"

    # 切换界面语言为中文 → 参数 label 与描述显示中文（通过全局辅助切换语言）
    page.evaluate("() => { window.__switchLocale && window.__switchLocale('zh') }")
    page.wait_for_timeout(400)
    keys_zh = " | ".join(page.locator(".param-row").all_inner_texts())
    assert any("\u4e00" <= ch <= "\u9fff" for ch in keys_zh), \
        f"切换中文后参数应含中文: {keys_zh[:200]}"
    descs_zh = " | ".join(page.locator(".param-desc").all_inner_texts())
    assert any("\u4e00" <= ch <= "\u9fff" for ch in descs_zh), \
        f"切换中文后参数描述应含中文: {descs_zh[:200]}"

    # 恢复英文，避免影响后续依赖默认英文的用例
    page.evaluate("() => { window.__switchLocale && window.__switchLocale('en') }")
    page.wait_for_timeout(200)


def test_perf_create_engine_select_and_env_block(page):
    """创建页引擎选择：默认自研引擎（可用）；切到原生引擎且环境不满足时禁止进入下一步。"""
    page.goto(f"{BASE_URL}/performance/create?mode=concurrency", wait_until="domcontentloaded")
    _visible(page, ".perf-create-page")
    _visible(page, ".bench-picker", timeout=15000)

    # 等待环境校验完成（校验中为 spin，无状态标签）
    page.wait_for_function(
        "() => { const tags = [...document.querySelectorAll('.bench-picker .ant-tag')];"
        " return tags.some(t => /Ready|Not Satisfied|Real|Mock/.test(t.textContent)); }",
        timeout=15000,
    )
    # 默认引擎为自研 bench（无框架环境依赖，标签显示 Ready）
    tags = page.locator(".bench-picker .ant-tag").all_inner_texts()
    assert any("Ready" in x for x in tags), f"默认引擎环境应可用: {tags}"

    # 选择原生引擎 vllm-0.23 → 环境校验（本机未安装 → Not Satisfied）
    page.locator(".bench-picker .ant-select").first.click()
    _visible(page, ".ant-select-dropdown", timeout=8000)
    page.locator(".ant-select-item-option").filter(has_text="vLLM 0.23").first.click()
    # 等待环境校验完成（标签变为 Ready / Not Satisfied / Real）
    page.wait_for_function(
        "() => { const tags = [...document.querySelectorAll('.bench-picker .ant-tag')];"
        " return tags.some(t => /Ready|Not Satisfied|Real|Mock/.test(t.textContent)); }",
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
    # 若有任务记录：每条记录在任务 ID 右侧显示 framework 高亮标记
    page.wait_for_timeout(800)
    if page.locator(".record-item").count() > 0:
        first = page.locator(".record-item").first
        assert first.locator(".record-framework").count() == 1, "每条记录应显示 framework 标记（任务 ID 右侧）"
        assert first.locator(".record-framework").inner_text().strip(), "framework 标记不应为空"


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


def test_settings_root_dir_confirm_cancel(page):
    """Root Dir 变更：点击 Save 后弹确认弹窗；点击取消不修改并恢复原值。"""
    page.goto(f"{BASE_URL}/settings", wait_until="domcontentloaded")
    _visible(page, ".settings-page")
    # General 为默认栏：找到 Root Dir 可编辑项并读取原始值
    row = page.locator(".dir-row").filter(has_text="Root Dir").first
    row.wait_for(state="visible", timeout=10000)
    original = row.locator(".dir-value.editable").inner_text()

    # 点击进入编辑，改值后点击 Save（触发弹确认，而非直接保存/失焦）
    row.locator(".dir-value.editable").click()
    input_el = row.locator(".dir-input")
    input_el.wait_for(state="visible", timeout=5000)
    input_el.fill(original + "__cancel_test")
    row.locator(".dir-save-btn").click()

    # 确认弹窗出现
    modal = page.locator(".dir-confirm-modal")
    modal.wait_for(state="visible", timeout=8000)
    # 点击取消 → 弹窗关闭，值恢复原路径
    page.locator(".dir-confirm-modal .ant-btn").filter(has_text="Cancel").first.click()
    page.wait_for_timeout(400)
    row = page.locator(".dir-row").filter(has_text="Root Dir").first
    assert row.locator(".dir-value.editable").inner_text() == original, "取消后应恢复原路径"


def test_settings_root_dir_confirm_ok_saves(page):
    """Root Dir 变更：确认后保存为新空白路径（无迁移）；测试结束恢复原值，避免污染后续用例。"""
    page.goto(f"{BASE_URL}/settings", wait_until="domcontentloaded")
    _visible(page, ".settings-page")
    row = page.locator(".dir-row").filter(has_text="Root Dir").first
    row.wait_for(state="visible", timeout=10000)
    original = row.locator(".dir-value.editable").inner_text()

    def change_to(value):
        row = page.locator(".dir-row").filter(has_text="Root Dir").first
        row.locator(".dir-value.editable").click()
        page.locator(".dir-input").wait_for(state="visible", timeout=5000)
        page.locator(".dir-input").fill(value)
        row.locator(".dir-save-btn").click()
        page.locator(".dir-confirm-modal").wait_for(state="visible", timeout=8000)
        page.locator(".dir-confirm-modal .ant-btn-primary").first.click()
        page.locator(".dir-confirm-modal").wait_for(state="hidden", timeout=8000)

    try:
        change_to(original + "__ok_test")
        acts = [el.inner_text() for el in page.locator(".dir-row").filter(has_text="Root Dir").locator(".dir-value.editable").all()]
        assert any("__ok_test" in a for a in acts), f"确认后应保存新路径: {acts}"
    finally:
        # 恢复原根目录，保持被测服务配置一致
        try:
            change_to(original)
        except Exception:
            pass


def test_sessions_new_chat(page):
    """Sessions 新建会话 -> 列表出现会话项。"""
    page.goto(f"{BASE_URL}/sessions", wait_until="domcontentloaded")
    _visible(page, ".sessions-page")
    btn = page.locator(".new-session-btn")
    btn.click()
    page.locator(".session-item").first.wait_for(state="visible", timeout=10000)


def test_sessions_rename_modal(page):
    """Sessions 会话项三点菜单 -> 重命名弹框：输入新标题保存后列表标题更新。"""
    page.goto(f"{BASE_URL}/sessions", wait_until="domcontentloaded")
    _visible(page, ".sessions-page")
    page.locator(".new-session-btn").click()
    page.locator(".session-item").first.wait_for(state="visible", timeout=10000)
    # 点击三点菜单，展开 Rename / Delete
    page.locator(".session-item").first.locator(".session-more").click()
    item = page.locator(".ant-dropdown-menu-item").filter(has_text="Rename").first
    item.wait_for(state="visible", timeout=5000)
    item.click()
    # 重命名弹框：清空输入并填写新标题，保存
    modal = page.locator(".ant-modal:visible")
    modal_input = modal.locator("input").first
    modal_input.fill("renamed-by-ui")
    modal.locator(".ant-modal-footer button").filter(has_text="Save").click()
    page.locator(".session-item").first.wait_for(state="visible", timeout=10000)
    name = page.locator(".session-name").first.inner_text()
    assert "renamed-by-ui" in name


def test_spa_fallback(page):
    """未知非 api 路径由 SPA fallback 返回应用（TopBar 渲染）。"""
    page.goto(f"{BASE_URL}/nonexistent-page", wait_until="domcontentloaded")
    _visible(page, ".topbar")


def test_settings_environment_no_framework(page):
    """Settings → Providers（原 Environment，1.0.7 改名）：Provider 面板保留 Base URL/API Key，不再有 Framework 选择。"""
    page.goto(f"{BASE_URL}/settings", wait_until="domcontentloaded")
    _visible(page, ".settings-page")
    page.locator(".menu-item").filter(has_text="Providers").first.click()
    _visible(page, ".provider-card", timeout=10000)

    labels = page.locator(".provider-card .panel-label").all_inner_texts()
    joined = " | ".join(labels)
    assert "Base URL" in joined, f"应保留 Base URL: {joined}"
    assert "API Key" in joined, f"应保留 API Key: {joined}"
    assert "Framework" not in joined, f"不应再有 Framework 选项: {joined}"
    assert page.locator(".provider-card .ant-radio-group").count() == 0, "不应再有框架单选组"


def test_settings_benches_english_only(page):
    """Bench Engines 默认英文：卡片文案与对比表均不含中文。"""
    _open_benches_tab(page)

    text = page.locator(".bench-list-scroll").inner_text()
    cjk = [ch for ch in text if "一" <= ch <= "鿿"]
    assert not cjk, f"引擎列表出现中文: {''.join(cjk[:40])}"

    page.locator(".bench-actions .bench-text-btn").filter(has_text="Engine Comparison").click()
    _visible(page, ".bench-modal:visible .compare-table", timeout=8000)
    modal_text = page.locator(".bench-modal:visible").inner_text()
    cjk = [ch for ch in modal_text if "一" <= ch <= "鿿"]
    assert not cjk, f"对比表出现中文: {''.join(cjk[:40])}"
    page.locator(".bench-modal:visible .ant-modal-close").click()


def test_settings_bench_modal_header_footer_width(page):
    """引擎弹框：header 为标题 + 提示，footer 为文字按钮，宽度约 1/2 浏览器宽度。"""
    _open_benches_tab(page)
    page.locator(".bench-actions .bench-text-btn").filter(has_text="Create Engine").click()
    _visible(page, ".bench-modal:visible", timeout=8000)
    page.wait_for_timeout(600)  # 等待弹框缩放动画结束再测量宽度

    # 弹框关闭后仍留在 DOM，必须限定可见的那个
    modal = page.locator(".bench-modal:visible")
    # header：标题 + 提示文案
    _visible(page, ".bench-modal:visible .bench-modal-title")
    hint = modal.locator(".bench-modal-hint").inner_text()
    assert hint.strip(), "header 应包含提示文案"

    # footer：文字操作按钮
    footer = modal.locator(".bench-modal-footer")
    assert footer.locator("button").count() >= 1, "footer 应含文字操作按钮"

    # 宽度 ≈ 1/2 视口（视口 1440 → 720）
    # 容差收紧到 20px：此前容差 60 会让「样式未生效的 520px 默认值」误判通过
    box = modal.bounding_box()
    viewport = page.viewport_size["width"]
    assert box, "弹框应已渲染"
    assert abs(box["width"] - viewport / 2) <= 20, \
        f"弹框宽度应约为 1/2 视口: {box['width']} vs {viewport / 2}"
    modal.locator(".ant-modal-close").click()


def test_settings_benches_list_scrollable(page):
    """Bench Engines 列表区可滚动：容器限高 + 内容超出时实际发生滚动位移。

    回归背景：a-spin 的 .ant-spin-container 未传递高度约束（scoped 下需 :deep()），
    导致 .bench-list-scroll 拿不到限高，内容被外层 overflow:hidden 裁掉而无法滚动。
    """
    _open_benches_tab(page)

    # 1) 高度约束链完整：a-spin 内部容器必须是 flex + min-height:0
    chain = page.evaluate(
        "() => { const c = document.querySelector('.ant-spin-container');"
        " const el = document.querySelector('.bench-list-scroll');"
        " return { cDisplay: c && getComputedStyle(c).display,"
        "          cMinH: c && getComputedStyle(c).minHeight,"
        "          ovfY: el && getComputedStyle(el).overflowY }; }"
    )
    assert chain["cDisplay"] == "flex", f"ant-spin-container 应为 flex: {chain}"
    assert chain["cMinH"] == "0px", f"ant-spin-container 应 min-height:0: {chain}"
    assert chain["ovfY"] == "auto", f"列表容器 overflow-y 应为 auto: {chain}"

    # 2) 实际滚动：缩小视口使内容超出 → 滚动位移 > 0
    page.set_viewport_size({"width": 1440, "height": 400})
    page.wait_for_timeout(500)
    before = page.evaluate(
        "() => { const el = document.querySelector('.bench-list-scroll');"
        " return { h: el.clientHeight, sh: el.scrollHeight }; }"
    )
    assert before["sh"] > before["h"], \
        f"内容应超出容器（h={before['h']}, scrollH={before['sh']}）"
    page.evaluate("document.querySelector('.bench-list-scroll').scrollTop = 999")
    page.wait_for_timeout(200)
    top = page.evaluate("document.querySelector('.bench-list-scroll').scrollTop")
    assert top > 0, f"列表应实际发生滚动位移: scrollTop={top}"

    page.set_viewport_size({"width": 1440, "height": 900})
    page.wait_for_timeout(400)


def test_all_pages_bottom_padding(page):
    """所有页面底部保留 18px 间距。"""
    page.goto(f"{BASE_URL}/settings", wait_until="domcontentloaded")
    _visible(page, ".app-content-layout")
    pad = page.evaluate(
        "() => { const el = document.querySelector('.app-content-layout');"
        " return el ? getComputedStyle(el).paddingBottom : null; }"
    )
    assert pad == "18px", f"页面底部应保留 18px: {pad}"


# ---------------- 1.0.7 增量：Providers / 介绍卡片 / Conditions / mocks ----------------


def test_settings_providers_panel(page):
    """Settings → Providers：菜单与面板头均为 Providers（无 Envs）；
    每个 Provider 一个面板（header 显示名称）；Add Provider 弹窗含必填 Provider Name。"""
    page.goto(f"{BASE_URL}/settings", wait_until="domcontentloaded")
    _visible(page, ".settings-page")

    # 菜单显示 Providers
    menu = page.locator(".menu-item").filter(has_text="Providers")
    assert menu.count() == 1, "菜单应有 Providers 项"

    menu.first.click()
    _visible(page, ".providers-head-card", timeout=10000)

    # 面板头：Providers（不是 Envs），含 Add Provider 按钮
    head_text = page.locator(".providers-head-card").inner_text()
    assert "Providers" in head_text, f"面板头应为 Providers: {head_text[:120]}"
    assert "Envs" not in head_text, "不应再显示 Envs 字样"

    # 迁移出的 Default Provider 面板存在，header 显示名称
    _visible(page, ".provider-card")
    names = page.locator(".prov-name").all_inner_texts()
    assert any("Default" in n for n in names), f"应显示迁移的 Default Provider: {names}"

    # Add Provider 弹窗：Provider Name 必填
    page.locator(".providers-head-card button").filter(has_text="Add Provider").click()
    _visible(page, ".provider-modal", timeout=8000)
    modal = page.locator(".provider-modal:visible")
    assert modal.locator(".panel-label").filter(has_text="Provider Name").count() >= 1
    save_btn = modal.locator("button").filter(has_text="Save").first
    assert save_btn.is_disabled(), "Provider Name 为空时 Save 应禁用（必填）"
    modal.locator(".ant-modal-close").click()


def test_create_page_conditions_no_rate_and_max_requests(page):
    """创建任务：Conditions 无 Request Rate 配置；阈值模式显示 Max Requests（默认 4096）。"""
    # 并发模式：无 Request Rate 行
    page.goto(f"{BASE_URL}/performance/create?mode=concurrency", wait_until="domcontentloaded")
    _visible(page, ".perf-create-page")
    _visible(page, ".condition-panel", timeout=15000)
    cond_text = page.locator(".condition-panel").inner_text()
    assert "Request Rate" not in cond_text, f"Conditions 不应再含 Request Rate: {cond_text[:200]}"

    # 阈值模式：Max Requests 默认 4096
    page.goto(f"{BASE_URL}/performance/create?mode=threshold", wait_until="domcontentloaded")
    _visible(page, ".condition-panel", timeout=15000)
    maxreq = page.locator(".maxreq-panel input")
    assert maxreq.count() == 1, "阈值模式应有 Max Requests 输入框（面板形式 .maxreq-panel）"
    assert maxreq.input_value() == "4096", f"默认应为 4096: {maxreq.input_value()}"


def _goto_step3_launch(page, mode):
    """进入创建页 Step3 并点击 Launch，返回预警弹窗 locator。"""
    page.goto(f"{BASE_URL}/performance/create?mode={mode}", wait_until="domcontentloaded")
    _visible(page, ".perf-create-page", timeout=15000)
    page.wait_for_function(
        "() => { const tags = [...document.querySelectorAll('.bench-picker .ant-tag')];"
        " return tags.some(t => /Ready|Not Satisfied|Real|Mock/.test(t.textContent)); }",
        timeout=15000,
    )
    page.locator(".panel-footer button").filter(has_text="Next").first.click()
    page.wait_for_timeout(1500)
    page.locator(".panel-footer button").filter(has_text="Next").first.click()
    page.wait_for_timeout(2000)
    page.locator(".panel-footer button").filter(has_text="Launch").first.click()
    page.wait_for_timeout(1200)
    return page.locator(".ant-modal-content")


def test_create_page_token_warning_concurrency(page):
    """创建页 Step3：并发模式点 Launch 弹出 token 使用预警（每组输入/输出 + 总计百万单位 + 确定/取消）。"""
    modal = _goto_step3_launch(page, "concurrency")
    assert modal.count() >= 1, "点 Launch 后应弹出 token 使用预警弹窗"
    # 每组预估：输入/输出 token 表
    assert modal.locator(".token-table").count() >= 1, "应显示每组 token 预估表"
    assert modal.locator(".token-table tbody tr").count() >= 1, "应有请求数行"
    # 全部总计（百万单位，footer 左侧）
    total_text = modal.locator(".token-footer").inner_text()
    assert "M" in total_text or "百万" in total_text, f"总计应为百万单位: {total_text}"
    # footer 确定/取消
    btns = modal.locator(".ant-modal-footer button").all_inner_texts()
    assert len(btns) == 2, f"footer 应有确定/取消两个按钮: {btns}"
    # 取消 → 弹窗消失，不启动任务
    modal.locator(".ant-modal-footer button").filter(has_text="Cancel").first.click()
    page.wait_for_timeout(800)
    assert page.locator(".ant-modal-content.token-warning").count() == 0 or \
        not page.locator(".ant-modal-content").first.is_visible(), "取消后预警弹窗应消失"


def test_create_page_token_warning_threshold(page):
    """创建页 Step3：阈值模式按 2 的次方阶梯累计预估 token（请求 1/2/4 逐级累加）。"""
    modal = _goto_step3_launch(page, "threshold")
    assert modal.count() >= 1, "阈值模式点 Launch 后应弹出 token 使用预警弹窗"
    rows = modal.locator(".token-table tbody tr")
    assert rows.count() >= 3, f"阈值模式应有多级阶梯: {rows.count()}"
    # 阶梯累计：第 2 行(请求2) token = 第 1 行(请求1) token * 3（1+2）
    def cell(r, i):
        return int(rows.nth(r).locator("td").nth(i).inner_text().replace(",", ""))
    r0_in, r1_in = cell(0, 1), cell(1, 1)
    assert r1_in == r0_in * 3, f"阈值模式第 2 阶梯应累计(1+2=3)倍: {r0_in} -> {r1_in}"
    # 总计百万单位（footer 左侧）
    total_text = modal.locator(".token-footer").inner_text()
    assert "M" in total_text or "百万" in total_text, f"总计应为百万单位: {total_text}"
    # 取消关闭
    modal.locator(".ant-modal-footer button").filter(has_text="Cancel").first.click()
    page.wait_for_timeout(600)


def test_create_page_mock_env_option(page):
    """创建页：不显示 Use Mock Environment 勾选（mock 由 Bench Engines 每引擎开关控制），
    引擎选择后显示 Mock/Real 状态 tag。"""
    page.goto(f"{BASE_URL}/performance/create?mode=concurrency", wait_until="domcontentloaded")
    _visible(page, ".bench-picker", timeout=15000)
    page.wait_for_function(
        "() => { const tags = [...document.querySelectorAll('.bench-picker .ant-tag')];"
        " return tags.some(t => /Ready|Not Satisfied|Real|Mock/.test(t.textContent)); }",
        timeout=15000,
    )

    # 默认选中 Bench CLI（第一个内置引擎）→ 不显示 Use Mock Environment 勾选
    assert page.locator(".mock-env-row").count() == 0, "创建页不应显示 Use Mock Environment 勾选"

    # 选择 vllm-0.23（原生引擎）→ 同样不显示，且显示 Mock/Real 状态 tag
    engine_sel = page.locator(".bench-picker .ant-select").first
    engine_sel.click()
    page.locator(".ant-select-item-option").filter(has_text="vLLM 0.23").first.click()
    page.wait_for_timeout(800)
    assert page.locator(".mock-env-row").count() == 0, "任何引擎创建页均不应显示 Use Mock Environment"
    assert page.locator(".bench-picker .ant-tag", has_text="Real").count() >= 1, "应显示 Real 状态 tag"


def test_create_page_base_provider_select(page):
    """创建任务 Base 面板：标题 Provider（无 Framework 行）；Provider 下拉默认选中第一个；模型联动。"""
    page.goto(f"{BASE_URL}/performance/create?mode=concurrency", wait_until="domcontentloaded")
    _visible(page, ".base-env-panel", timeout=15000)
    panel_text = page.locator(".base-env-panel").inner_text()
    assert "Framework" not in panel_text, f"Base 面板不应再有 Framework 行: {panel_text[:200]}"

    # Provider 下拉存在且默认选中第一个（异步加载，等待选中值出现）
    provider_sel = page.locator(".base-env-panel .ant-select").first
    # 无任何 Provider 配置时跳过；有配置则必须默认选中第一项
    page.wait_for_function(
        "() => { const s = document.querySelector('.base-env-panel .ant-select .ant-select-selection-item');"
        " return s && s.textContent.trim() !== ''; }",
        timeout=15000,
    )
    selected = provider_sel.locator(".ant-select-selection-item").first
    selected_text = selected.inner_text().strip()
    assert selected_text, "应默认选中第一个 Provider"
    # 展开下拉：第一个选项应与默认选中项一致
    provider_sel.click()
    page.wait_for_timeout(500)
    first_option = page.locator(".ant-select-dropdown:visible .ant-select-item-option").first
    assert first_option.inner_text().strip() == selected_text, "默认选中项应为 Providers 第一个"
    page.keyboard.press("Escape")

    # 模型下拉存在（联动所选 Provider）
    model_sel = page.locator(".base-env-panel .ant-select").nth(1)
    model_sel.click()
    page.wait_for_timeout(300)
    assert page.locator(".ant-select-dropdown:visible .ant-select-item-option").count() >= 1, "模型下拉应有候选项（联动 Provider）"
    page.keyboard.press("Escape")


def test_settings_providers_no_activate_with_status(page):
    """Settings → Providers：无 Activate 按钮/Active 标签；状态与模型显示在各 Provider 面板内。"""
    page.goto(f"{BASE_URL}/settings", wait_until="domcontentloaded")
    _visible(page, ".settings-page")
    page.locator(".menu-item").filter(has_text="Providers").first.click()
    _visible(page, ".provider-card", timeout=10000)

    card = page.locator(".provider-card").first
    card_text = card.inner_text()
    assert "Activate" not in card_text, "Provider 面板不应再有 Activate 按钮"
    assert "Active" not in card_text, "Provider 面板不应再有 Active 标签"

    # 状态显示在面板内（online/offline）
    assert card.locator(".env-status").count() >= 1, "Provider 面板应显示在线状态"
    # 模型行：等待探测完成（在线显示绿色模型标签 / 离线显示「暂无模型」）
    page.wait_for_function(
        "() => { const c = document.querySelector('.provider-card');"
        " return c && (c.querySelector('.provider-model-tag') || c.querySelector('.no-model')); }",
        timeout=15000,
    )
    card = page.locator(".provider-card").first
    assert card.locator(".provider-model-tag, .no-model").count() >= 1, "模型行应显示模型标签或暂无模型"
    # 模型标签为绿色框且带复制图标
    if card.locator(".provider-model-tag").count():
        assert card.locator(".provider-model-tag .tag-copy").count() >= 1, "每个模型标签应带复制图标"


def test_sessions_provider_select_header_color(page):
    """Sessions：输入栏有 Provider 下拉；header 颜色标记所选模型状态（默认红色）。"""
    page.goto(f"{BASE_URL}/sessions", wait_until="domcontentloaded")
    _visible(page, ".sessions-page")
    page.locator(".new-session-btn").click()
    _visible(page, ".chat-header", timeout=10000)

    # 输入栏：Provider 下拉在模型下拉左侧
    selects = page.locator(".input-right .ant-select")
    assert selects.count() >= 2, f"输入栏应有 Provider+模型下拉: {selects.count()}"
    provider_sel = selects.nth(0)
    provider_sel.click()
    page.wait_for_timeout(300)
    assert page.locator(".ant-select-item-option").count() >= 1, "Provider 下拉应有候选项"
    page.keyboard.press("Escape")

    # header 颜色：初始未探测/离线为红色（chat-bad）；在线则绿色（chat-ok）
    header = page.locator(".chat-header")
    cls = header.get_attribute("class") or ""
    assert "chat-bad" in cls or "chat-ok" in cls, f"header 应标记状态颜色: {cls}"


def test_mock_env_tag_in_task_detail(page):
    """use_mock_env 任务：Performance 详情 Perf 面板 framework 行旁显示 Mock 标识。"""
    import requests as req

    snap = helpers.create_and_run_task(
        req,
        BASE_URL,
        {"engine_id": "vllm-0.23", "use_mock_env": True},
        timeout=120,
    )
    task_id = snap["task_id"]
    try:
        page.goto(f"{BASE_URL}/performance", wait_until="domcontentloaded")
        _visible(page, ".perf-detail")
        tag = page.locator(".mock-env-tag")
        tag.wait_for(state="visible", timeout=10000)
        assert "Mock" in tag.inner_text(), f"应显示 Mock 标识: {tag.inner_text()}"
    finally:
        req.delete(f"{BASE_URL}/api/tasks/{task_id}", timeout=10)


def test_perf_landing_intro_cards(page):
    """Performance 默认页介绍卡片：并发测试 / 阈值搜索 / 实时可视化。"""
    page.goto(f"{BASE_URL}/performance", wait_until="domcontentloaded")
    _visible(page, ".perf-intro", timeout=15000)

    titles = page.locator(".feature-card .ant-card-meta-title").all_inner_texts()
    joined = " | ".join(titles)
    assert "Concurrency Testing" in joined, f"缺并发测试卡片: {joined}"
    assert "Threshold Search" in joined, f"缺阈值搜索卡片: {joined}"
    assert "Realtime Performance Charts" in joined, f"缺实时图表卡片: {joined}"
    assert "Multi-Framework" not in joined, f"旧文案应移除: {joined}"

    # Threshold Search 描述精简为 2 行（自动搜索满足阈值的最大并发）
    thr = page.locator(".feature-card").filter(has_text="Threshold Search")
    desc = thr.inner_text()
    assert "max concurrency" in desc.lower() or "最大并发" in desc, f"Threshold 描述应含最大并发: {desc}"


def _open_settings_tab(page, text, wait_sel):
    """切到 Settings 指定栏并等待内容区就绪。"""
    page.goto(f"{BASE_URL}/settings", wait_until="domcontentloaded")
    _visible(page, ".settings-page")
    page.locator(".menu-item").filter(has_text=text).first.click()
    _visible(page, wait_sel, timeout=15000)


def test_settings_models_panel(page):
    """Settings → Models：分类在顶部，面板化三分区（Header=模型名+操作；内容=描述/精度/链接；footer=下载命令）。"""
    _open_settings_tab(page, "Models", ".cat-chip")
    # 顶部分类：厂商组分类 chip 可点击
    assert page.locator(".cat-bar .cat-chip").count() >= 2, "顶部分类应显示厂商分类 chip"
    # 选择前端 modelCatalog 有数据的厂商 DeepSeek（DeepSeek-V3 含 homepage/精度/下载命令）
    page.locator(".cat-chip").filter(has_text="DeepSeek").first.click()
    page.wait_for_timeout(500)
    card = page.locator(".model-panel-card").first
    # Header 左侧模型名 + 右侧操作高亮链接
    assert "DeepSeek-V3" in card.locator(".ant-card-head-title").inner_text(), "面板 Header 应为模型名称"
    action = card.locator(".mp-action").first
    assert action.is_visible(), "Header 右侧应显示操作高亮链接"
    # 内容区：描述 + 精度 tags + 访问链接（三分区 body）
    assert card.locator(".card-body").count() >= 1, "面板应含内容（body）分区"
    assert card.locator(".mp-intro").inner_text().strip(), "面板应含模型描述"
    assert card.locator(".mp-tags .ant-tag").count() >= 1, "应显示精度列表"
    assert card.locator(".mp-link").count() >= 1, "应显示访问链接"
    # footer 分区：下载命令（可复制）
    assert card.locator(".card-footer").count() >= 1, "面板应含 footer 分区"
    assert card.locator(".mp-cmd").count() >= 1, "footer 应显示下载命令"


def test_settings_datasets_panel(page):
    """Settings → Datasets：分类在顶部，面板化三分区（Header=名称+下载按钮；内容=描述/链接；footer=下载命令）。"""
    _open_settings_tab(page, "Datasets", ".ds-panel-card")
    # 顶部分类：All Categories + 各分类 chip
    assert page.locator(".cat-bar .cat-chip").count() >= 2, "顶部分类应显示分类 chip"
    card = page.locator(".ds-panel-card").first
    assert card.locator(".ant-card-head-title").inner_text().strip(), "面板 Header 应为数据集名称"
    assert card.locator(".ant-card-head .ant-btn").count() >= 1, "Header 右侧应显示下载按钮"
    assert card.locator(".card-body").count() >= 1, "面板应含内容（body）分区"
    assert card.locator(".ds-desc").inner_text().strip(), "应含数据集描述"
    assert card.locator(".ds-link").count() >= 1, "应显示访问链接"
    assert card.locator(".card-footer").count() >= 1, "面板应含 footer 分区"
    assert card.locator(".ds-cmd").count() >= 1, "footer 应显示下载命令"


def test_settings_skills_panel(page):
    """Settings → Skills：内置技能清单面板（名称+id / 版本号 / 描述 / 特性 / 使用说明 / 提示词 / footer 文字按钮）。"""
    _open_settings_tab(page, "Skills", ".skill-card")
    card = page.locator(".skill-card").first
    assert card.locator(".skill-name").inner_text().strip(), "Header 左侧应显示技能名称"
    assert card.locator(".ant-tag").first.inner_text().strip(), "应显示技能 id tag"
    assert "v" in card.locator(".skill-version").inner_text(), "Header 右侧应显示版本号"
    assert card.locator(".skill-desc").inner_text().strip(), "应含功能描述"
    assert card.locator(".skill-ul li").count() >= 1, "应含功能特性列表"
    assert card.locator(".skill-ol li").count() >= 1, "应含使用说明列表"
    assert card.locator(".skill-prompt").inner_text().strip(), "应含提示词"
    # footer 文字按钮：仅 Download / Copy Prompt 两个
    footer_btns = card.locator(".skill-footer button")
    assert footer_btns.count() == 2, f"footer 应仅 Download/Copy Prompt 两个文字按钮: {footer_btns.count()}"
    texts = footer_btns.all_inner_texts()
    joined = " | ".join(texts)
    assert "Download" in joined and ("Copy" in joined or "Prompt" in joined), \
        f"footer 按钮应包含 Download 与 Copy Prompt: {joined}"


def test_settings_benches_mock_switch(page):
    """Settings → Bench Engines：每个引擎卡片有 Mock 开关（默认关闭）；切换后刷新环境状态标记 Mock/Real。"""
    # 先通过 API 确保第一个引擎（Bench CLI）mock 关闭，避免其他测试残留影响
    import requests as req
    first_id = req.get(f"{BASE_URL}/api/benchs").json()["engines"][0]["id"]
    req.post(f"{BASE_URL}/api/benchs/{first_id}/mock", json={"enabled": False}, timeout=10)

    _open_settings_tab(page, "Bench Engines", ".bench-card")
    cards = page.locator(".bench-card")
    assert cards.count() >= 3, f"引擎卡片应 ≥3: {cards.count()}"
    first = cards.first
    sw = first.locator(".bench-mock .ant-switch")
    assert sw.count() == 1, "每个引擎卡片应有 Mock 开关"
    assert "ant-switch-checked" not in (sw.first.get_attribute("class") or ""), "Mock 开关默认应关闭"
    try:
        # 打开 Mock 开关 → 刷新出 Mock 状态
        sw.first.click()
        page.wait_for_timeout(800)
        assert first.locator(".ant-tag", has_text="Mock").count() >= 1, "打开 Mock 后应显示 Mock 状态 tag"
    finally:
        # 恢复关闭，避免影响其他依赖真实环境的用例
        req.post(f"{BASE_URL}/api/benchs/{first_id}/mock", json={"enabled": False}, timeout=10)
        page.wait_for_timeout(400)


# ---------------------------------------------------------------------------
# 精度测试模块（1.0.8 Accuracy）
# ---------------------------------------------------------------------------


def test_accuracy_landing_intro(page):
    """Accuracy 页：无任务时展示介绍页与「Create Accuracy Task」入口（默认 en 语境）。"""
    # 清理历史任务，确保 intro 状态
    import requests as _rq

    for task in (_rq.get(f"{BASE_URL}/api/accuracy/tasks", timeout=10).json().get("tasks") or []):
        _rq.delete(f"{BASE_URL}/api/accuracy/tasks/{task['task_id']}", timeout=10)

    page.goto(f"{BASE_URL}/accuracy", wait_until="domcontentloaded")
    _visible(page, ".accuracy-page")
    _visible(page, ".perf-intro")
    _visible(page, ".planned-card")
    btn = page.locator(".ant-result-extra button", has_text="Create Accuracy Task").first
    btn.wait_for(state="visible", timeout=15000)
    # 介绍页结构与特性卡（与 Performance 默认页一致）
    assert page.locator(".ant-result").count() >= 1, "介绍页应使用 a-result 结构"
    assert page.locator(".feature-card").count() >= 3, "介绍页应显示特性卡片"


def test_accuracy_create_wizard(page):
    """精度创建向导：三步表单渲染 + 内置评测数据集 + 引擎环境明细。"""
    page.goto(f"{BASE_URL}/accuracy/create", wait_until="domcontentloaded")
    _visible(page, ".acc-create-page")
    _visible(page, ".steps")
    # Step1 数据集：下拉含内置评测数据集（MMLU）
    page.locator(".step-body .ant-select").first.click()
    opt = page.locator(".ant-select-dropdown .ant-select-item-option", has_text="MMLU").first
    opt.wait_for(state="visible", timeout=15000)
    opt.click()
    # Step2：引擎环境明细（benchscope 恒通过 → 无校验行；切换 native-hf 展示 torch/transformers/CUDA 明细）
    page.locator(".actions button", has_text="Next").first.click()
    page.locator(".step-body:visible .ant-select").first.click()
    page.locator(".ant-select-dropdown:visible .ant-select-item-option", has_text="Native HF").first.click()
    env_tag = page.locator(".env-item .ant-tag", has_text="FAIL").first
    env_tag.wait_for(state="visible", timeout=15000)
    # 切回自研引擎（恒通过，不阻断）
    page.locator(".step-body:visible .ant-select").first.click()
    page.locator(".ant-select-dropdown:visible .ant-select-item-option", has_text="Bench CLI").first.click()
    page.wait_for_timeout(800)


def test_accuracy_task_flow_list_and_detail(page):
    """全链路：API 创建 mock 精度任务 → 列表出现 → 详情指标卡渲染。"""
    import json as _json
    import pathlib
    import uuid

    import requests as _rq

    ds = pathlib.Path("/tmp") / f"acc_ui_{uuid.uuid4().hex[:6]}.jsonl"
    lines = [_json.dumps({"question": f"q{i}", "choices": ["甲", "乙", "丙", "丁"],
                          "answer": "ABCD"[i % 4], "subject": "s"}, ensure_ascii=False)
             for i in range(4)]
    ds.write_text("\n".join(lines) + "\n", encoding="utf-8")

    r = _rq.post(f"{BASE_URL}/api/accuracy/tasks", timeout=15, json={
        "engine_id": "mock", "model": "ui-model", "dataset": {"path": str(ds)},
        "mock_correct_rate": 1.0, "api": {"base_url": "http://mock.invalid"},
    })
    assert r.status_code == 200, r.text
    task_id = r.json()["task"]["task_id"]

    deadline = __import__("time").time() + 30
    status = None
    while __import__("time").time() < deadline:
        status = _rq.get(f"{BASE_URL}/api/accuracy/tasks/{task_id}", timeout=10).json()["task"]["status"]
        if status in ("done", "error", "stopped"):
            break
        __import__("time").sleep(0.2)
    assert status == "done"

    page.goto(f"{BASE_URL}/accuracy", wait_until="domcontentloaded")
    _visible(page, ".accuracy-page")
    # 任务列表出现该任务
    cell = page.locator(".accuracy-page .ant-table", has_text=task_id).first
    cell.wait_for(state="visible", timeout=15000)
    # 详情指标卡渲染（accuracy 100%）
    metric = page.locator(".metric-box", has_text="Accuracy").first
    metric.wait_for(state="visible", timeout=15000)
    val = page.locator(".metric-value", has_text="100").first
    val.wait_for(state="visible", timeout=15000)

    _rq.delete(f"{BASE_URL}/api/accuracy/tasks/{task_id}", timeout=10)
    ds.unlink(missing_ok=True)


def test_datas_evals_records_page(page):
    """Datas/evals 记录页渲染（空态或列表）。"""
    page.goto(f"{BASE_URL}/datas/evals", wait_until="domcontentloaded")
    _visible(page, ".evals-page")
    _visible(page, ".list-card")
