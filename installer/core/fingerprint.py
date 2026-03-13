"""
机器指纹生成器
采集 MAC 地址 + 硬盘序列号 生成唯一指纹 hash
"""

import hashlib
import subprocess
import uuid
import platform
import re


def get_mac_address() -> str:
    """获取 MAC 地址"""
    mac = uuid.getnode()
    mac_str = ':'.join(f'{(mac >> i) & 0xff:02x}' for i in range(0, 48, 8))
    return mac_str


def get_disk_serial_windows() -> str:
    """获取 Windows 硬盘序列号"""
    try:
        result = subprocess.run(
            ["wmic", "diskdrive", "get", "serialnumber"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        )
        lines = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        # 第一行是 "SerialNumber"，取后续行
        serials = [line for line in lines if line.lower() != "serialnumber"]
        return serials[0] if serials else "unknown"
    except Exception:
        return "unknown"


def get_disk_serial_linux() -> str:
    """获取 Linux 硬盘序列号"""
    try:
        result = subprocess.run(
            ["lsblk", "-ndo", "SERIAL", "/dev/sda"],
            capture_output=True, text=True, timeout=10
        )
        serial = result.stdout.strip()
        return serial if serial else "unknown"
    except Exception:
        return "unknown"


def get_disk_serial() -> str:
    """跨平台获取硬盘序列号"""
    system = platform.system()
    if system == "Windows":
        return get_disk_serial_windows()
    elif system == "Linux":
        return get_disk_serial_linux()
    elif system == "Darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPStorageDataType"],
                capture_output=True, text=True, timeout=10
            )
            # 简单提取序列号
            for line in result.stdout.split('\n'):
                if 'serial' in line.lower() or 'uuid' in line.lower():
                    parts = line.split(':')
                    if len(parts) > 1:
                        return parts[1].strip()
        except Exception:
            pass
        return "unknown"
    return "unknown"


def get_computer_name() -> str:
    """获取计算机名"""
    return platform.node()


def generate_fingerprint() -> str:
    """
    生成机器指纹
    基于 MAC 地址 + 硬盘序列号 + 计算机名 生成 SHA256 hash
    """
    mac = get_mac_address()
    disk = get_disk_serial()
    name = get_computer_name()

    raw = f"{mac}|{disk}|{name}"
    fingerprint = hashlib.sha256(raw.encode()).hexdigest()

    return fingerprint


if __name__ == "__main__":
    print(f"MAC 地址:    {get_mac_address()}")
    print(f"硬盘序列号:  {get_disk_serial()}")
    print(f"计算机名:    {get_computer_name()}")
    print(f"机器指纹:    {generate_fingerprint()}")
