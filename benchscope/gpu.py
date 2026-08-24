"""GPU 信息自动获取（nvidia-smi），失败时回退手动配置。"""
from __future__ import annotations

import shutil
import subprocess
from typing import Optional


def detect_gpu() -> Optional[dict]:
    """尝试自动获取 GPU 型号与数量。成功返回 {"name":..., "count":N}，失败返回 None。"""
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return None
    try:
        result = subprocess.run(
            [nvidia_smi, "--query-gpu=name,count", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        lines = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
        if not lines:
            return None
        names = [ln.split(",")[0].strip() for ln in lines]
        counts = []
        for ln in lines:
            parts = ln.split(",")
            if len(parts) > 1:
                try:
                    counts.append(int(parts[1].strip()))
                except ValueError:
                    pass
        name = names[0] if names else ""
        count = sum(counts) if counts else len(lines)
        return {"name": name, "count": count}
    except Exception:
        return None
