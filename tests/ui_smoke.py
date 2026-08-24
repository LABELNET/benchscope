"""benchscope UI 冒烟测试：加载页面、发起 fake 测试、验证实时结果与日志页。"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
OUT = Path("/tmp/benchscope_shots")
OUT.mkdir(exist_ok=True)

# 使用本机缓存的 chromium（版本可能与 playwright 期望不一致）
EXE = str(Path.home() / ".cache/ms-playwright/chromium-1217/chrome-linux64/chrome")


def log(msg):
    print("[ui-test]", msg, flush=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=EXE)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        errors = []
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: errors.append(f"console[{m.type}]: {m.text}") if m.type == "error" else None)

        # 1. 首页
        log("打开首页")
        page.goto(BASE, wait_until="networkidle", timeout=30000)
        page.wait_for_selector("text=benchscope", timeout=10000)
        page.wait_for_selector("text=服务设置", timeout=10000)
        time.sleep(1.5)
        page.screenshot(path=str(OUT / "01-home.png"), full_page=False)
        log("首页渲染 OK，标题/导航/设置按钮可见")

        # 2. 状态徽标（⭕服务 / ⭕环境）
        page.wait_for_selector("text=环境：就绪", timeout=15000)
        page.wait_for_selector("text=服务：就绪", timeout=15000)
        page.screenshot(path=str(OUT / "02-status.png"))
        log("状态徽标 OK：服务/环境就绪（mock）")

        # 3. 副 tab 栏（vLLM/SGLang 下固定）
        for t in ["Random", "ShareGPT", "Custom"]:
            page.wait_for_selector(f".subtab:has-text('{t}')", timeout=10000)
        log("副 tab 栏 Three tabs OK")

        # 3.1 测试环境面板（服务信息 + 模型选择 + 在线状态）
        page.wait_for_selector("text=测试环境", timeout=10000)
        page.wait_for_selector("text=Base URL", timeout=10000)
        page.wait_for_selector("text=测试模型 Model", timeout=10000)
        page.wait_for_selector("text=测试连接", timeout=10000)
        page.wait_for_selector("text=在线", timeout=10000)
        log("测试环境面板（信息+模型+在线+测试连接）OK")

        # 3.2 左侧固定导航（测试流程）
        for t in ["测试环境", "测试配置", "测试进度", "测试结果"]:
            page.wait_for_selector(f".side-item:has-text('{t}')", timeout=10000)
        log("左侧固定导航（测试流程）OK")

        # 3.3 Random 面板
        for t in ["测试配置", "测试进度", "测试结果"]:
            page.wait_for_selector(f".blocks-wrap .ant-card-head-title:has-text('{t}')", timeout=10000)
        page.wait_for_selector("button:has-text('开始测试')", timeout=10000)
        page.wait_for_selector("button:has-text('取消测试')", timeout=10000)
        log("Random 下面板 OK")

        # 3.4 ShareGPT / Custom tab
        page.locator(".subtab", has_text="ShareGPT").click()
        page.wait_for_timeout(600)
        page.wait_for_selector("text=ShareGPT 数据集", timeout=10000)
        page.locator(".subtab", has_text="Custom").click()
        page.wait_for_timeout(600)
        page.wait_for_selector("text=自定义数据集", timeout=10000)
        log("ShareGPT / Custom tab OK")
        page.locator(".subtab", has_text="Random").click()
        page.wait_for_timeout(600)

        # 4. 模型下拉（测试环境面板，来自 mock /v1/models）
        page.wait_for_selector(".ant-select", timeout=10000)
        page.locator(".ant-select").first.click()
        page.wait_for_timeout(600)
        page.screenshot(path=str(OUT / "03-model-select.png"))
        page.keyboard.press("Escape")
        log("模型下拉 OK")

        # 5. 选择模型（第一个选项）
        page.locator(".ant-select").first.click()
        page.wait_for_timeout(400)
        opts = page.locator(".ant-select-item-option")
        if opts.count() > 0:
            opts.nth(0).click()
            log(f"选择模型: {opts.nth(0).inner_text()}")
        else:
            log("WARN: 无模型选项")

        # 6. 点击开始测试（fake bench 模式；三个数据集 tab 各有一个按钮，点第一个=当前可见 tab）
        page.locator("button", has_text="开始测试").first.click()
        page.wait_for_timeout(2500)
        log("已点击开始测试")
        page.screenshot(path=str(OUT / "04-running.png"))

        # 7. 等待结果行出现（fake 模式 3K1K/1K1K/256X256 x 1,4,8 = 9 行）
        page.wait_for_timeout(12000)
        page.screenshot(path=str(OUT / "05-results.png"))
        log("实时结果面板截图完成")

        # 8. ECharts canvas 数量
        canvases = page.locator("canvas").count()
        log(f"canvas 数量: {canvases}")

        # 9. 日志管理页（主导航，左侧=测试记录，无副导航）
        page.locator(".ant-menu-item", has_text="日志管理").click()
        page.wait_for_timeout(2500)
        page.wait_for_selector("text=测试记录", timeout=10000)
        page.wait_for_selector("text=指标汇总", timeout=10000)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / "06-logs.png"), full_page=False)
        # 副导航不应出现在日志页
        assert page.locator(".subtab").count() == 0, "日志页不应有副导航"
        log("日志管理页 OK（左侧=测试记录，无副导航）")

        # 10. 均值分析 tab
        page.locator(".ant-tabs-tab", has_text="均值分析").click()
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / "07-mean-analysis.png"))
        log("均值分析 tab OK")

        # 11. P99 tab
        page.locator(".ant-tabs-tab", has_text="P99 分析").click()
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT / "08-p99-analysis.png"))
        log("P99 分析 tab OK")

        # 12. 服务设置页
        page.locator("button", has_text="设置").click()
        page.wait_for_timeout(2000)
        page.wait_for_selector("text=推理服务 API 配置", timeout=10000)
        page.screenshot(path=str(OUT / "09-settings.png"))
        log("服务设置页 OK")

        # 13. SGLang 页面
        page.locator(".ant-menu-item", has_text="SGLang").click()
        page.wait_for_timeout(2000)
        page.wait_for_selector("text=测试配置", timeout=10000)
        page.screenshot(path=str(OUT / "10-sglang.png"))
        log("SGLang 页面 OK")

        # 测试状态
        page.goto(BASE + "/vllm", wait_until="networkidle")
        page.wait_for_timeout(1000)
        status = page.locator(".ant-tag").all_inner_texts()
        log(f"页面标签: {status[:12]}")

        print("\n===== 控制台/页面错误 =====")
        if errors:
            for e in errors[:20]:
                print(" ", e)
        else:
            print("  无错误")
        browser.close()

        return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
