#!/usr/bin/env python3
"""
检查生产环境 .env 配置文件是否有缺失的配置项
使用方法：
    python scripts/check_env_config.py [.env文件路径]
    如果不指定路径，默认检查当前目录下的 .env 文件
"""

import sys
import re
from pathlib import Path
from typing import Set, Dict, Tuple


def extract_env_vars(file_path: Path) -> Tuple[Set[str], Dict[str, str]]:
    """
    从 .env 文件中提取环境变量名和值
    
    Returns:
        (变量名集合, 变量名到值的字典)
    """
    var_names = set()
    var_dict = {}
    
    if not file_path.exists():
        return var_names, var_dict
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            # 移除注释和空行
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 匹配 KEY=VALUE 格式
            match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$', line)
            if match:
                key = match.group(1)
                value = match.group(2).strip()
                # 移除引号
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                var_names.add(key)
                var_dict[key] = value
    
    return var_names, var_dict


def main():
    # 获取项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # 读取 env.example
    env_example_path = project_root / 'env.example'
    if not env_example_path.exists():
        print(f"❌ 错误: 找不到 env.example 文件: {env_example_path}")
        sys.exit(1)
    
    example_vars, example_dict = extract_env_vars(env_example_path)
    print(f"📋 从 env.example 中提取到 {len(example_vars)} 个配置项\n")
    
    # 读取实际的 .env 文件
    if len(sys.argv) > 1:
        env_path = Path(sys.argv[1])
    else:
        env_path = project_root / '.env'
    
    if not env_path.exists():
        print(f"❌ 错误: 找不到 .env 文件: {env_path}")
        print(f"💡 提示: 请指定 .env 文件路径，或确保文件存在于项目根目录")
        sys.exit(1)
    
    actual_vars, actual_dict = extract_env_vars(env_path)
    print(f"📋 从 .env 中提取到 {len(actual_vars)} 个配置项\n")
    
    # 找出缺失的配置项
    missing_vars = example_vars - actual_vars
    
    # 找出注释中提到的敏感配置（这些应该在 .env.secrets 中）
    secrets_vars = {
        'MYSQL_PASSWORD',
        'LLM_API_KEY',
        'DEEPSEEK_API_KEY',
        'JWT_SECRET_KEY',
        'ADMIN_PASSWORD_HASH',
        'WECHAT_SECRET',
        'WECHAT_TOKEN',
        'WECHAT_PAY_MCHID',
        'WECHAT_PAY_API_KEY',
        'GAODE_API_KEY',
    }
    
    # 过滤掉应该在 .env.secrets 中的配置
    missing_in_env = missing_vars - secrets_vars
    
    # 输出结果
    print("=" * 80)
    print("📊 配置检查结果")
    print("=" * 80)
    
    if missing_in_env:
        print(f"\n⚠️  发现 {len(missing_in_env)} 个缺失的配置项（应该在 .env 中）:\n")
        for var in sorted(missing_in_env):
            example_value = example_dict.get(var, '')
            print(f"  ❌ {var}")
            if example_value:
                print(f"     示例值: {example_value}")
        print()
    else:
        print("\n✅ .env 文件中没有缺失的配置项\n")
    
    # 检查敏感配置是否在 .env.secrets 中
    secrets_path = project_root / '.env.secrets'
    if secrets_path.exists():
        secrets_vars_set, secrets_dict = extract_env_vars(secrets_path)
        missing_secrets = secrets_vars & missing_vars & secrets_vars_set
        if missing_secrets:
            print(f"⚠️  以下敏感配置在 .env.secrets 中已配置（这是正确的）:\n")
            for var in sorted(missing_secrets):
                print(f"  ✅ {var} (在 .env.secrets 中)")
            print()
        elif secrets_vars & missing_vars:
            print(f"⚠️  以下敏感配置应该在 .env.secrets 中配置:\n")
            for var in sorted(secrets_vars & missing_vars):
                print(f"  ⚠️  {var} (应该在 .env.secrets 中)")
            print()
    else:
        if secrets_vars & missing_vars:
            print(f"⚠️  以下敏感配置应该在 .env.secrets 中配置（但 .env.secrets 文件不存在）:\n")
            for var in sorted(secrets_vars & missing_vars):
                print(f"  ⚠️  {var}")
            print()
    
    # 检查是否有额外的配置项（不在 env.example 中）
    extra_vars = actual_vars - example_vars
    if extra_vars:
        print(f"ℹ️  发现 {len(extra_vars)} 个额外的配置项（不在 env.example 中）:\n")
        for var in sorted(extra_vars):
            print(f"  ℹ️  {var} = {actual_dict.get(var, '')}")
        print()
    
    # 总结
    print("=" * 80)
    if missing_in_env:
        print(f"❌ 检查失败: 发现 {len(missing_in_env)} 个缺失的配置项")
        print("\n💡 建议:")
        print("   1. 将缺失的配置项添加到 .env 文件中")
        print("   2. 参考 env.example 中的示例值")
        print("   3. 敏感配置应放在 .env.secrets 文件中")
        sys.exit(1)
    else:
        print("✅ 检查通过: 所有必需的配置项都已配置")
        sys.exit(0)


if __name__ == '__main__':
    main()

