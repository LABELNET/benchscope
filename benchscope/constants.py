"""全局常量与默认值。"""

# 默认并发数列表（可编辑、可添加、可删除）
DEFAULT_CONCURRENCY_LIST = [1, 4, 8, 16, 32, 40, 64, 128]

# random 数据集默认输入/输出长度组合 (input_len, output_len, 显示后缀)
DEFAULT_LENGTH_PAIRS = [
    (3072, 1024, "3K1K"),
    (1024, 1024, "1K1K"),
    (256, 256, "256X256"),
]

# 框架标识
FRAMEWORK_VLLM = "vllm"
FRAMEWORK_SGLANG = "sglang"
FRAMEWORK_NAMES = {FRAMEWORK_VLLM: "vLLM", FRAMEWORK_SGLANG: "SGLang"}

# 数据集类型
DATASET_RANDOM = "random"
DATASET_SHAREGPT = "sharegpt"
DATASET_CUSTOM = "custom"

# ShareGPT 数据集（modelscope）
SHAREGPT_DATASET_ID = "gliang1001/ShareGPT_V3_unfiltered_cleaned_split"

# 状态
STATUS_READY = "ready"
STATUS_OFFLINE = "offline"
STATUS_RUNNING = "running"

# 默认配置
DEFAULT_CONFIG = {
    "framework": FRAMEWORK_VLLM,
    "api": {
        "base_url": "http://127.0.0.1:8000",
        "endpoint": "/v1/chat/completions",
        "api_key": "",
        "extra_headers": {},
    },
    "gpu": {"auto": True, "name": "", "count": 8},
    # 缓存目录体系（数据根目录为 data_dir，其余为各功能目录）
    "data_dir": "~/.benchscope",  # 数据根目录（服务端数据持久化 / 任务 / 会话等）
    "perfs_dir": "~/.benchscope/perfs",  # 性能测试任务目录
    "evals_dir": "~/.benchscope/evals",  # 精度测试任务目录
    "analysis_dir": "~/.benchscope/analysys",  # 数据分析目录（联动 Datas）
    "logs_dir": "~/.benchscope/logs",  # 日志目录（runtime 日志 + 任务终端输出）
    "sessions_dir": "~/.benchscope/sessions",  # 会话缓存目录
    "models_dir": "~/.benchscope/models",  # 模型下载缓存目录（联动 Settings/Models）
    "datasets_dir": "~/.benchscope/datasets",  # 数据集下载目录（联动 Settings/Datasets）
    "plugins_dir": "~/.benchscope/plugins",  # 插件安装加载目录（联动 Settings/Plugins）
    "tpot_threshold_ms": 100,
    "request_rate": "inf",  # inf 或数字
    "bench_commands": {
        "vllm": "vllm bench serve",
        "sglang": "python -m sglang.bench_serving",
    },
}
