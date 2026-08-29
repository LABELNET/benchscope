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
    """Settings → Bench Engines 栏：整页为三个内置引擎列表（Bench CLI / vllm-0.23 /
    sglang-0.5.10）+ 介绍文案 + 环境校验结果。"""
    _open_benches_tab(page)

    cards = page.locator(".bench-card")
    assert cards.count() == 3, f"expected 3 engines, got {cards.count()}"

    names = page.locator(".bench-name").all_inner_texts()
    joined = " | ".join(names)
    # 自研引擎统一命名为 Bench CLI
    assert "Bench CLI" in joined, f"缺少 Bench CLI 自研引擎: {joined}"
    assert "vllm-0.23" in joined or "0.23" in joined, f"缺少 vllm-0.23: {joined}"
    assert "sglang-0.5.10" in joined or "0.5.10" in joined, f"缺少 sglang-0.5.10: {joined}"

    # 每个引擎有介绍文案
    descs = page.locator(".bench-desc").all_inner_texts()
    assert len(descs) == 3 and all(d.strip() for d in descs), f"引擎介绍缺失: {descs}"

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
    _visible(page, ".bench-modal", timeout=8000)

    modal = page.locator(".bench-modal")
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
    _visible(page, ".bench-modal", timeout=8000)

    modal = page.locator(".bench-modal")
    # 拖拽上传区（ant-design-vue 4 渲染为 .ant-upload-drag）
    _visible(page, ".bench-modal .ant-upload-drag")
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
    _visible(page, ".bench-modal", timeout=8000)

    modal = page.locator(".bench-modal")
    _visible(page, ".bench-modal .compare-table")
    # 维度行 + 三个引擎列
    assert modal.locator(".compare-table tbody tr").count() >= 3, "对比表应含多个维度"
    headers = modal.locator(".compare-table thead th").all_inner_texts()
    assert len(headers) == 4, f"表头应为 1 维度列 + 3 引擎列, got {headers}"

    modal.locator(".ant-modal-close").click()
    page.wait_for_timeout(500)


def test_perf_create_params_follow_engine(page):
    """创建任务 Step2：参数面板只显示当前所选引擎的参数，并展示引擎名称。"""
    page.goto(f"{BASE_URL}/performance/create?mode=concurrency", wait_until="domcontentloaded")
    _visible(page, ".perf-create-page")
    _visible(page, ".bench-picker", timeout=15000)

    # 默认自研引擎 → 进入 Step2
    page.wait_for_function(
        "() => { const t = document.querySelector('.bench-picker .ant-tag');"
        " return t && /Ready|Not Satisfied/.test(t.textContent); }",
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


def test_perf_create_engine_select_and_env_block(page):
    """创建页引擎选择：默认自研引擎（可用）；切到原生引擎且环境不满足时禁止进入下一步。"""
    page.goto(f"{BASE_URL}/performance/create?mode=concurrency", wait_until="domcontentloaded")
    _visible(page, ".perf-create-page")
    _visible(page, ".bench-picker", timeout=15000)

    # 等待环境校验完成（校验中为 spin，无状态标签）
    page.wait_for_function(
        "() => { const t = document.querySelector('.bench-picker .ant-tag');"
        " return t && /Ready|Not Satisfied/.test(t.textContent); }",
        timeout=15000,
    )
    # 默认引擎为自研 bench（无框架环境依赖，标签显示 Ready）
    tags = page.locator(".bench-picker .ant-tag").all_inner_texts()
    assert any("Ready" in x for x in tags), f"默认引擎环境应可用: {tags}"

    # 选择原生引擎 vllm-0.23 → 环境校验（本机未安装 → Not Satisfied）
    page.locator(".bench-picker .ant-select").first.click()
    _visible(page, ".ant-select-dropdown", timeout=8000)
    page.locator(".ant-select-item-option").filter(has_text="vLLM 0.23").first.click()
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


def test_settings_environment_no_framework(page):
    """Settings → Environment：仅保留 Base URL（OpenAI 接口）与 API Key，不再有 Framework 选择。"""
    page.goto(f"{BASE_URL}/settings", wait_until="domcontentloaded")
    _visible(page, ".settings-page")
    page.locator(".menu-item").filter(has_text="Environment").first.click()
    _visible(page, ".panel-card", timeout=10000)

    labels = page.locator(".panel-card .panel-label").all_inner_texts()
    joined = " | ".join(labels)
    assert "Base URL" in joined, f"应保留 Base URL: {joined}"
    assert "API Key" in joined, f"应保留 API Key: {joined}"
    assert "Framework" not in joined, f"不应再有 Framework 选项: {joined}"
    assert page.locator(".panel-card .ant-radio-group").count() == 0, "不应再有框架单选组"


def test_settings_benches_english_only(page):
    """Bench Engines 默认英文：卡片文案与对比表均不含中文。"""
    _open_benches_tab(page)

    text = page.locator(".bench-list-scroll").inner_text()
    cjk = [ch for ch in text if "一" <= ch <= "鿿"]
    assert not cjk, f"引擎列表出现中文: {''.join(cjk[:40])}"

    page.locator(".bench-actions .bench-text-btn").filter(has_text="Engine Comparison").click()
    _visible(page, ".bench-modal .compare-table", timeout=8000)
    modal_text = page.locator(".bench-modal").inner_text()
    cjk = [ch for ch in modal_text if "一" <= ch <= "鿿"]
    assert not cjk, f"对比表出现中文: {''.join(cjk[:40])}"
    page.locator(".bench-modal .ant-modal-close").click()


def test_settings_bench_modal_header_footer_width(page):
    """引擎弹框：header 为标题 + 提示，footer 为文字按钮，宽度约 1/3 浏览器宽度。"""
    _open_benches_tab(page)
    page.locator(".bench-actions .bench-text-btn").filter(has_text="Create Engine").click()
    _visible(page, ".bench-modal", timeout=8000)
    page.wait_for_timeout(600)  # 等待弹框缩放动画结束再测量宽度

    modal = page.locator(".bench-modal")
    # header：标题 + 提示文案
    _visible(page, ".bench-modal .bench-modal-title")
    hint = modal.locator(".bench-modal-hint").inner_text()
    assert hint.strip(), "header 应包含提示文案"

    # footer：文字操作按钮
    footer = modal.locator(".bench-modal-footer")
    assert footer.locator("button").count() >= 1, "footer 应含文字操作按钮"

    # 宽度 ≈ 1/3 视口（视口 1440 → 约 480）；a-modal 的 class 落在 .ant-modal 本身
    box = modal.bounding_box()
    viewport = page.viewport_size["width"]
    assert box, "弹框应已渲染"
    assert abs(box["width"] - viewport / 3) <= 60, \
        f"弹框宽度应约为 1/3 视口: {box['width']} vs {viewport / 3}"
    page.locator(".bench-modal .ant-modal-close").click()


def test_settings_benches_list_scrollable(page):
    """Bench Engines 列表区可滚动（内容超出时出现滚动条）。"""
    _open_benches_tab(page)
    scrollable = page.evaluate(
        "() => { const el = document.querySelector('.bench-list-scroll');"
        " return !!el && (el.scrollHeight > el.clientHeight ||"
        " getComputedStyle(el).overflowY === 'auto' || el.clientHeight > 0); }"
    )
    assert scrollable, "引擎列表应为独立滚动容器且可见可滚动"


def test_all_pages_bottom_padding(page):
    """所有页面底部保留 18px 间距。"""
    page.goto(f"{BASE_URL}/settings", wait_until="domcontentloaded")
    _visible(page, ".app-content-layout")
    pad = page.evaluate(
        "() => { const el = document.querySelector('.app-content-layout');"
        " return el ? getComputedStyle(el).paddingBottom : null; }"
    )
    assert pad == "18px", f"页面底部应保留 18px: {pad}"
