#!/usr/bin/env python3
"""手动清除 Shaobor_electricity 的存储数据"""
import os
import json

# 存储文件路径
storage_file = os.path.expanduser("~/.homeassistant/.storage/Shaobor_electricity_auth")

# 检查文件是否存在
if os.path.exists(storage_file):
    print(f"找到存储文件: {storage_file}")
    # 读取内容
    with open(storage_file, 'r') as f:
        data = json.load(f)
    print(f"当前存储的数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    # 删除文件
    os.remove(storage_file)
    print("✓ 已删除存储文件")
else:
    print(f"存储文件不存在: {storage_file}")
    print("✓ 无需清除")

print("\n请重启 Home Assistant 以使更改生效")
print("重启命令: 在 Home Assistant 中进入 开发者工具 -> 重启")
