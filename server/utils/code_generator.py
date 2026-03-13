"""
激活码生成工具（命令行）
用法:
    python code_generator.py --count 10 --valid-hours 24
    python code_generator.py --count 1 --prefix VIP
"""

import argparse
import secrets
import string
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from models.database import init_db, create_activation_code, get_db_path


def generate_code(prefix: str = "OC", length: int = 12) -> str:
    """生成一个随机激活码，格式: OC-XXXX-XXXX-XXXX"""
    chars = string.ascii_uppercase + string.digits
    parts = []
    part_len = 4
    num_parts = length // part_len

    for _ in range(num_parts):
        part = ''.join(secrets.choice(chars) for _ in range(part_len))
        parts.append(part)

    return f"{prefix}-" + "-".join(parts)


def main():
    parser = argparse.ArgumentParser(description="激活码批量生成工具")
    parser.add_argument("--count", type=int, default=1, help="生成数量 (默认: 1)")
    parser.add_argument("--valid-hours", type=int, default=24, help="有效期小时数 (默认: 24)")
    parser.add_argument("--prefix", type=str, default="OC", help="激活码前缀 (默认: OC)")
    parser.add_argument("--length", type=int, default=12, help="随机部分长度 (默认: 12)")

    args = parser.parse_args()

    # 初始化数据库
    init_db()
    print(f"数据库路径: {get_db_path()}")
    print(f"正在生成 {args.count} 个激活码 (有效期 {args.valid_hours} 小时)...\n")

    codes = []
    for i in range(args.count):
        code = generate_code(prefix=args.prefix, length=args.length)
        result = create_activation_code(code, valid_hours=args.valid_hours)
        codes.append(result)
        print(f"  [{i + 1}] {result['code']}  (过期: {result['expires_at']})")

    print(f"\n成功生成 {len(codes)} 个激活码")

    # 同时输出纯激活码列表，方便复制
    print("\n--- 纯激活码列表 (方便复制) ---")
    for c in codes:
        print(c["code"])


if __name__ == "__main__":
    main()
