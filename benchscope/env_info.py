"""系统环境信息采集（Dashboard 环境面板）。

采集硬件 / 操作系统 / 网络 / 框架版本四类信息，缺失项返回 None，
前端统一以 "—" 展示。
"""
from __future__ import annotations

import os
import platform
import socket
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path
from typing import Optional

from benchscope.gpu import detect_gpu

# 虚拟网卡 / docker 相关网卡名前缀（网络环境里过滤不显示）
_VIRTUAL_IFACE_PREFIXES = (
    "docker", "veth", "br-", "virbr", "cni", "flannel", "lo", "tun", "utun",
)


def _pkg(name: str) -> Optional[str]:
    try:
        return _pkg_version(name)
    except PackageNotFoundError:
        return None


def _run(cmd: list[str], timeout: int = 5) -> Optional[str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "").strip()
        return out or None
    except Exception:
        return None


def _cpu_info() -> Optional[str]:
    count = os.cpu_count() or 0
    brand: Optional[str] = None
    if sys.platform == "darwin":
        brand = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
    elif sys.platform.startswith("linux"):
        try:
            for line in Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("model name"):
                    brand = line.split(":", 1)[1].strip()
                    break
        except Exception:
            brand = None
    return f"{brand} × {count} 核" if brand else (f"{count} 核" if count else None)


def _mem_total_gb() -> Optional[str]:
    try:
        if sys.platform == "darwin":
            total = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
            return f"{total / 1024 ** 3:.1f} GB"
        for line in Path("/proc/meminfo").read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("MemTotal:"):
                kb = int(line.split()[1])
                return f"{kb / 1024 ** 2:.1f} GB"
    except Exception:
        pass
    return None


def _os_info() -> dict:
    system = platform.system() or None
    version: Optional[str] = None
    kernel = platform.release() or None
    if system == "Darwin":
        version = platform.mac_ver()[0] or None
    elif system == "Linux":
        try:
            for line in Path("/etc/os-release").read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("PRETTY_NAME="):
                    version = line.split("=", 1)[1].strip().strip('"')
                    break
        except Exception:
            version = None
    return {"name": system, "version": version, "kernel": kernel}


def _network_interfaces() -> list[dict]:
    """网口-IP 列表，过滤 docker / 虚拟网卡。"""
    out: list[dict] = []

    def is_virtual(iface: str) -> bool:
        return any(iface == p or iface.startswith(p) for p in _VIRTUAL_IFACE_PREFIXES)

    try:
        if sys.platform.startswith("linux"):
            raw = _run(["ip", "-o", "-4", "addr", "show"], timeout=5)
            if raw:
                for line in raw.splitlines():
                    parts = line.split()
                    if len(parts) >= 4:
                        iface = parts[1].strip(":")
                        ip = parts[3].split("/")[0]
                        if is_virtual(iface):
                            continue
                        out.append({"iface": iface, "ip": ip})
                return out
        # macOS / fallback：使用 ifconfig 简单解析
        raw = _run(["ifconfig"], timeout=5)
        if raw:
            cur: Optional[str] = None
            for line in raw.splitlines():
                stripped = line.strip()
                if line and not line.startswith((" ", "\t")):
                    cur = line.split(":")[0]
                elif "inet " in stripped and cur:
                    ip = stripped.split()[1]
                    if is_virtual(cur):
                        continue
                    out.append({"iface": cur, "ip": ip})
    except Exception:
        pass
    return out


def collect_env_info() -> dict:
    """采集完整环境信息，缺失项为 None。"""
    gpu = detect_gpu()
    return {
        "hardware": {
            "host": platform.node() or None,
            "cpu": _cpu_info(),
            "memory": _mem_total_gb(),
            "gpu": f"{gpu['name']} × {gpu['count']}" if gpu and gpu.get("name") else (f"{gpu['count']} 块 GPU" if gpu else None),
        },
        "os": _os_info(),
        "network": _network_interfaces(),
        "versions": {
            "python": sys.version.split()[0] if sys.version else None,
            "pytorch": _pkg("torch"),
            "vllm": _pkg("vllm"),
            "sglang": _pkg("sglang"),
            "benchscope": _pkg("benchscope"),
        },
    }
