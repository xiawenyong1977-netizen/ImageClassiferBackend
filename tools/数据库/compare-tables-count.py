#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""比较Web和App服务器上所有表的记录数"""
import pymysql
import sys

# MySQL配置 - 直接使用参数
MYSQL_USER = "classifier"
MYSQL_PASSWORD = "Classifier@2024"
MYSQL_DATABASE = "image_classifier"

# 服务器配置
WEB_MYSQL_HOST = "localhost"  # Web服务器MySQL（本地）
APP_MYSQL_HOST = "47.98.167.63"  # App服务器MySQL主机IP


def get_table_counts(server_name, config):
    """获取服务器上所有表的记录数"""
    try:
        print(f"   连接信息: {config['user']}@{config['host']}/{config['database']}")
        conn = pymysql.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset='utf8mb4',
            connect_timeout=10
        )
        
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            print(f"   ⚠️  警告：数据库 {config['database']} 中没有表")
            cursor.close()
            conn.close()
            return [], {}, 0
        
        # 获取每个表的记录数
        table_counts = {}
        total = 0
        
        print(f"   找到 {len(tables)} 个表，正在统计记录数...")
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                count = cursor.fetchone()[0]
                table_counts[table] = count
                total += count
            except Exception as e:
                print(f"   ⚠️  警告：无法统计表 {table} 的记录数: {e}")
                table_counts[table] = -1  # 标记为错误
        
        cursor.close()
        conn.close()
        
        return tables, table_counts, total
        
    except pymysql.Error as e:
        print(f"❌ 无法连接数据库 {server_name}: {e}")
        print(f"   连接信息: {config['user']}@{config['host']}/{config['database']}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 发生未知错误: {e}")
        sys.exit(1)

def main():
    print("🔵 [DEBUG] main函数已开始执行")
    print("=" * 60)
    print("比较Web和App服务器数据库表记录数")
    print("=" * 60)
    print()
    
    # MySQL配置
    print("MySQL配置:")
    web_config = {
        'host': WEB_MYSQL_HOST,
        'user': MYSQL_USER,
        'password': MYSQL_PASSWORD,
        'database': MYSQL_DATABASE
    }
    app_config = {
        'host': APP_MYSQL_HOST,
        'user': MYSQL_USER,
        'password': MYSQL_PASSWORD,
        'database': MYSQL_DATABASE
    }
    print(f"   Web服务器: {web_config['user']}@{web_config['host']}/{web_config['database']}")
    print(f"   App服务器: {app_config['user']}@{app_config['host']}/{app_config['database']}")
    print()
    
    # 获取表记录数
    print()
    print("正在获取Web服务器表记录数...")
    web_tables, web_counts, web_total = get_table_counts("Web服务器", web_config)
    print(f"✅ Web服务器: {len(web_tables)} 个表，总记录数: {web_total:,}")
    
    print()
    print("正在获取App服务器表记录数...")
    app_tables, app_counts, app_total = get_table_counts("App服务器", app_config)
    print(f"✅ App服务器: {len(app_tables)} 个表，总记录数: {app_total:,}")
    
    # 比较总数
    print()
    print("=" * 60)
    print("总记录数比较")
    print("=" * 60)
    print(f"Web服务器总记录数: {web_total:,}")
    print(f"App服务器总记录数: {app_total:,}")
    print()
    
    if web_total == app_total:
        print("✅ 总记录数一致")
    else:
        diff = web_total - app_total
        print(f"❌ 总记录数不一致，差异: {diff:,} (Web比App多{diff:,}条)")
    
    # 详细比较
    print()
    print("=" * 60)
    print("详细比较每个表的记录数")
    print("=" * 60)
    print()
    
    # 获取所有唯一表名
    all_tables = sorted(set(web_tables + app_tables))
    
    if not all_tables:
        print("⚠️  警告：没有找到任何表")
        return
    
    # 打印表头
    print(f"{'表名':<40} {'Web记录数':>15} {'App记录数':>15} {'差异':>15} {'状态':>15}")
    print("-" * 100)
    
    differences_found = False
    for table in all_tables:
        web_count = web_counts.get(table, 0)
        app_count = app_counts.get(table, 0)
        
        # 初始化显示变量
        web_display = ""
        app_display = ""
        diff_display = ""
        status = ""
        
        # 处理错误情况
        if web_count == -1:
            web_display = "错误"
            app_display = f"{app_count:,}" if app_count != -1 else "错误"
            diff_display = "N/A"
            status = "❌Web错误"
            differences_found = True
        elif app_count == -1:
            web_display = f"{web_count:,}" if web_count != -1 else "错误"
            app_display = "错误"
            diff_display = "N/A"
            status = "❌App错误"
            differences_found = True
        elif table not in web_tables:
            web_display = "不存在"
            app_display = f"{app_count:,}" if app_count != -1 else "错误"
            diff_display = f"-{app_count:,}" if app_count != -1 else "N/A"
            status = "⚠️仅App有"
            differences_found = True
        elif table not in app_tables:
            web_display = f"{web_count:,}" if web_count != -1 else "错误"
            app_display = "不存在"
            diff_display = f"+{web_count:,}" if web_count != -1 else "N/A"
            status = "⚠️仅Web有"
            differences_found = True
        elif web_count == app_count:
            web_display = f"{web_count:,}"
            app_display = f"{app_count:,}"
            diff_display = "0"
            status = "✅一致"
        else:
            diff = web_count - app_count
            web_display = f"{web_count:,}"
            app_display = f"{app_count:,}"
            diff_display = f"{diff:+,}"
            status = "❌不一致"
            differences_found = True
        
        print(f"{table:<40} {web_display:>15} {app_display:>15} {diff_display:>15} {status:>15}")
    
    print("-" * 100)
    print()
    
    # 总结
    if not differences_found:
        print("✅ 所有表的记录数完全一致！")
    else:
        print("⚠️  发现差异，请检查上表")
    
    print()
    print("=" * 60)
    print("比较完成")
    print("=" * 60)

if __name__ == "__main__":
    print("🔵 [DEBUG] 脚本开始执行，准备调用main函数")
    main()
    print("🔵 [DEBUG] main函数执行完成")
