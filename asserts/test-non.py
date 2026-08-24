import os
import re
import subprocess
import requests
from pathlib import Path
from enum import Enum
from dataclasses import dataclass


# ===================== 核心配置 =====================
VLLM_HOST = "127.0.0.1"
VLLM_PORT = "8000"
VLLM_SERVER = f'http://{VLLM_HOST}:{VLLM_PORT}'

GPU_COUNTS = "8"

CONCURRENCY_LIST = [1, 4, 8, 32, 40, 64, 128]
TEST_CASES = [
    (3072, 1024, "3K1K"),
    (1024, 1024, "1K1K"),
    (256,256,"256X256")
]
BENCH_BASE_ARGS = [
    "--host",f'{VLLM_HOST}',
    "--port",f'{VLLM_PORT}',
    "--trust-remote-code",
    "--backend", "openai-chat",
    "--dataset-name", "random",
    "--endpoint", "/v1/chat/completions",
    "--ignore-eos"
]
LOG_DIR = Path("./logs")
# ====================================================



def check_dependencies():
    try:
        subprocess.run(["vllm", "--version"], check=True, capture_output=True)
    except FileNotFoundError:
        raise RuntimeError("未找到 vllm 命令！")
    try:
        import requests
    except ImportError:
        raise RuntimeError("未安装 requests：pip install requests")

def get_vllm_model() -> str:
    print(f"正在连接 vLLM 服务：{VLLM_SERVER}")
    try:
        resp = requests.get(f"{VLLM_SERVER}/v1/models", timeout=5)
        resp.raise_for_status()
        models = resp.json()
        model_id = models["data"][0]["id"]
        if not model_id:
            raise ValueError("未获取到有效模型信息")
        print(f"✅ 获取模型成功：{model_id}")
        return model_id
    except Exception as e:
        raise RuntimeError(f"连接vLLM服务失败：{str(e)}")

def parse_bench_metrics(output: str) -> dict:
    metrics = {}
    patterns = {
        "concurrency": r"Maximum request concurrency:\s+(\d+)",
        "output_token": r"Output token throughput \(tok/s\):\s+([\d.]+)",
        "peak_output_token": r"Peak output token throughput \(tok/s\):\s+([\d.]+)",
        "total_token": r"Total token throughput \(tok/s\):\s+([\d.]+)",
        "ttft": r"Mean TTFT \(ms\):\s+([\d.]+)",
        "tpot": r"Mean TPOT \(ms\):\s+([\d.]+)",
        "itl": r"Mean ITL \(ms\):\s+([\d.]+)"
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, output)
        metrics[key] = match.group(1) if match else "0.0"
    return metrics

def run_bench(model: str, concurrency: int, input_len: int, output_len: int) -> tuple[str, str]:
    """返回 (命令字符串, 执行输出)"""
    cmd = [
        "vllm", "bench", "serve",
        "--max-concurrency", str(concurrency),
        "--num-prompts", str(concurrency),
        "--random-input-len", str(input_len),
        "--random-output-len", str(output_len),
        "--model", model,
        "--tokenizer", model,
        *BENCH_BASE_ARGS
    ]
    cmd_str = " ".join(cmd)
    print(f"执行命令：{cmd_str}")
    
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8"
    )
    # 捕获执行失败
    if result.returncode != 0:
        raise RuntimeError(f"Bench命令执行异常，返回码{result.returncode}\n完整日志：{result.stdout}")
    bench_output = result.stdout
    # 调试打印完整输出，定位问题
    print("===== Bench完整输出 =====")
    print(bench_output)
    print("========================")
    return cmd_str, bench_output

def clean_model_logs(model_name: str, gpu_count: int):
    """清理带卡数标识的旧日志"""
    log_files = [
        LOG_DIR / f"{model_name}_X{gpu_count}.log",
        LOG_DIR / f"{model_name}_3K1K_X{gpu_count}.log",
        LOG_DIR / f"{model_name}_1K1K_X{gpu_count}.log"
    ]
    cleaned = False
    for log_file in log_files:
        if log_file.exists():
            log_file.unlink()
            print(f"🗑️  已清理旧日志：{log_file}")
            cleaned = True
    if not cleaned:
        print("📝 未检测到旧日志，将全新生成日志")

def main():
    check_dependencies()
    LOG_DIR.mkdir(exist_ok=True)
    
    # 1. 获取模型
    model_path = get_vllm_model()
    model_name = Path(model_path).name
    
    used_gpu_count = GPU_COUNTS
    # 3. 清理带卡数的旧日志
    clean_model_logs(model_name, used_gpu_count)
    
    # 4. 汇总日志（带卡数标识）
    summary_log = LOG_DIR / f"{model_name}_X{used_gpu_count}.log"

    # 5. 执行测试用例
    for input_len, output_len, case_suffix in TEST_CASES:
        # 执行日志命名：模型_3K1K_X1.log
        detail_log = LOG_DIR / f"{model_name}_{case_suffix}_X{used_gpu_count}.log"
        
        print(f"\n{'='*60}")
        print(f"开始测试：{case_suffix} | 输入={input_len} 输出={output_len} | GPU数={used_gpu_count}")
        print(f"详细日志：{detail_log}")
        print(f"汇总日志：{summary_log}")
        print(f"{'='*60}\n")
        
        # 写入汇总日志分隔线+条件
        with open(summary_log, "a", encoding="utf-8") as f:
            f.write(f"{'='*60}\n")
            f.write(f"测试条件：{case_suffix} | 输入={input_len} | 输出={output_len} | 部署GPU={used_gpu_count}张\n")
            f.write(f"{'='*60}\n")
            f.write("并发数,Output Token,Peak Output Token,Total Token,TTFT,TPOT,ITL\n")

        # 遍历并发
        for concurrency in CONCURRENCY_LIST:
            print(f"\n▶ 测试并发数：{concurrency}")
            try:
                # 执行测试，获取命令+输出
                cmd_str, bench_output = run_bench(model_path, concurrency, input_len, output_len)
                
                # 写入详细日志：命令 + 执行结果
                with open(detail_log, "a", encoding="utf-8") as f:
                    f.write(f"{'='*50} 并发数={concurrency} {'='*50}\n")
                    f.write(f"执行命令：{cmd_str}\n\n")  # 记录执行命令
                    f.write(bench_output)
                    f.write("\n\n")
                
                # 解析指标
                metrics = parse_bench_metrics(bench_output)
                line = (f"{metrics['concurrency']},{metrics['output_token']},{metrics['peak_output_token']},"
                        f"{metrics['total_token']},{metrics['ttft']},{metrics['tpot']},{metrics['itl']}\n")
                
                # 写入汇总日志
                with open(summary_log, "a", encoding="utf-8") as f:
                    f.write(line)
                
                # 实时打印
                print(f"\n📊 并发数 {concurrency} 性能测试结果：")
                print(f"├─ 并发数：{metrics['concurrency']}")
                print(f"├─ Output Token (tok/s)：{metrics['output_token']}")
                print(f"├─ Peak Output Token (tok/s)：{metrics['peak_output_token']}")
                print(f"├─ Total Token (tok/s)：{metrics['total_token']}")
                print(f"├─ TTFT (ms)：{metrics['ttft']}")
                print(f"├─ TPOT (ms)：{metrics['tpot']}")
                print(f"└─ ITL (ms)：{metrics['itl']}")
                
                print(f"\n✅ 并发数 {concurrency} 测试完成")
            except Exception as e:
                print(f"❌ 并发数 {concurrency} 测试失败：{str(e)}")
                continue

    print(f"\n{'='*60}")
    print("🎉 所有测试任务执行完成！")
    print(f"日志文件均保存在：{LOG_DIR.resolve()}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()