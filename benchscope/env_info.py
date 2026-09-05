"""系统环境信息采集（Dashboard 环境面板）。

采集硬件 / 操作系统 / 网络 / 框架版本四类信息，缺失项返回 None，
前端统一以 "—" 展示。
"""
from __future__ import annotations

import ipaddress
import os
import platform
import re
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


def _cidr_to_netmask(prefix: int) -> Optional[str]:
    """CIDR 前缀长度 → 点分十进制子网掩码（如 /24 → 255.255.255.0）。"""
    try:
        return str(ipaddress.IPv4Network(f"0.0.0.0/{int(prefix)}").netmask)
    except Exception:
        return None


def _hex_netmask_to_str(hexmask: str) -> Optional[str]:
    """macOS ifconfig 的十六进制掩码（0xffffff00）→ 点分十进制掩码。"""
    try:
        val = int(str(hexmask).replace("0x", ""), 16)
        return ".".join(str((val >> (8 * shift)) & 0xFF) for shift in (3, 2, 1, 0))
    except Exception:
        return None


def _net_addr(ip: str, mask: str) -> Optional[str]:
    """IP + 掩码 → 子网地址（network address）。"""
    try:
        return str(ipaddress.IPv4Network(f"{ip}/{mask}", strict=False).network_address)
    except Exception:
        return None


def _network_interfaces() -> list[dict]:
    """网口信息列表，过滤 docker / 虚拟网卡。

    每个网口返回 {iface, mac, ip, subnet, mask}；MAC 作为「UUID」展示。
    """
    out: list[dict] = []

    def is_virtual(iface: str) -> bool:
        return any(iface == p or iface.startswith(p) for p in _VIRTUAL_IFACE_PREFIXES)

    try:
        if sys.platform.startswith("linux"):
            # IP + CIDR 前缀：`ip -o -4 addr show`
            ip_meta: dict[str, tuple[str, int]] = {}
            raw = _run(["ip", "-o", "-4", "addr", "show"], timeout=5)
            if raw:
                for line in raw.splitlines():
                    parts = line.split()
                    if len(parts) >= 4:
                        iface = parts[1].strip(":")
                        ip_cidr = parts[3]
                        ip = ip_cidr.split("/")[0]
                        prefix = int(ip_cidr.split("/")[1]) if "/" in ip_cidr else None
                        if is_virtual(iface):
                            continue
                        ip_meta[iface] = (ip, prefix)
            # MAC：`ip -o link show`
            mac_meta: dict[str, str] = {}
            raw_link = _run(["ip", "-o", "link", "show"], timeout=5)
            if raw_link:
                for line in raw_link.splitlines():
                    m = re.search(r"\d+:\s*([^\s@]+)[@\d]*:\s.*link/ether\s+([0-9a-f:]+)", line)
                    if m:
                        mac_meta[m.group(1)] = m.group(2)
            for iface, (ip, prefix) in ip_meta.items():
                mask = _cidr_to_netmask(prefix) if prefix is not None else None
                out.append({
                    "iface": iface,
                    "mac": mac_meta.get(iface),
                    "ip": ip,
                    "subnet": _net_addr(ip, mask) if mask else None,
                    "mask": mask,
                })
            return out
        # macOS / fallback：使用 ifconfig 解析（每网口 ether / inet netmask）
        raw = _run(["ifconfig"], timeout=5)
        if raw:
            cur: Optional[str] = None
            mac: Optional[str] = None
            for line in raw.splitlines():
                stripped = line.strip()
                if line and not line.startswith((" ", "\t")):
                    # 网口头行，刷新当前网口与 MAC
                    if cur and cur in [x["iface"] for x in out]:
                        pass
                    cur = line.split(":")[0]
                    mac = None
                elif "ether " in stripped and cur:
                    mac = stripped.split()[1]
                elif "inet " in stripped and cur:
                    parts = stripped.split()
                    ip = parts[1]
                    if is_virtual(cur):
                        continue
                    mask_hex = None
                    for i, p in enumerate(parts):
                        if p == "netmask" and i + 1 < len(parts):
                            mask_hex = parts[i + 1]
                    mask = _hex_netmask_to_str(mask_hex) if mask_hex else None
                    out.append({
                        "iface": cur,
                        "mac": mac,
                        "ip": ip,
                        "subnet": _net_addr(ip, mask) if mask else None,
                        "mask": mask,
                    })
                    mac = None
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
