#!/usr/bin/env python3
"""
修复 DeepSeek 模型名称配置
将错误的模型名称统一修复为正确的 deepseek-chat
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pymongo import MongoClient
from app.core.config import settings

def fix_deepseek_model():
    """修复 DeepSeek 模型名称配置"""
    print("=" * 80)
    print("🔧 修复 DeepSeek 模型配置")
    print("=" * 80)
    print()
    
    # 连接 MongoDB
    try:
        print("🔌 连接到 MongoDB...")
        client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("✅ MongoDB 连接成功")
        print()
    except Exception as e:
        print(f"❌ MongoDB 连接失败: {e}")
        print("   请确保 MongoDB 服务正在运行")
        sys.exit(1)
    
    db = client[settings.MONGO_DB]
    
    # 正确的模型名称
    correct_model = "deepseek-chat"
    
    # 1. 修复 llm_providers 配置
    print("📋 检查 llm_providers 配置...")
    providers = list(db.llm_providers.find({"provider": "deepseek"}))
    if providers:
        for provider in providers:
            old_model = provider.get("model_name", "N/A")
            if old_model != correct_model:
                print(f"   发现错误模型名称: {old_model} -> {correct_model}")
                db.llm_providers.updateOne(
                    {"_id": provider["_id"]},
                    {"$set": {"model_name": correct_model}}
                )
                print(f"   ✅ 已更新")
            else:
                print(f"   ✅ 模型名称正确: {correct_model}")
    else:
        print("   ℹ️  未找到 deepseek 提供商配置")
    print()
    
    # 2. 修复 user_configs 配置
    print("📋 检查 user_configs 配置...")
    user_configs = list(db.user_configs.find({"llm_provider": "deepseek"}))
    if user_configs:
        fixed_count = 0
        for config in user_configs:
            quick_model = config.get("quick_think_llm", "")
            deep_model = config.get("deep_think_llm", "")
            needs_fix = False
            
            if quick_model and quick_model != correct_model:
                print(f"   发现错误的快速模型: {quick_model} -> {correct_model}")
                needs_fix = True
            if deep_model and deep_model != correct_model:
                print(f"   发现错误的深度模型: {deep_model} -> {correct_model}")
                needs_fix = True
            
            if needs_fix:
                update_data = {}
                if quick_model and quick_model != correct_model:
                    update_data["quick_think_llm"] = correct_model
                if deep_model and deep_model != correct_model:
                    update_data["deep_think_llm"] = correct_model
                
                db.user_configs.updateOne(
                    {"_id": config["_id"]},
                    {"$set": update_data}
                )
                fixed_count += 1
                print(f"   ✅ 已更新用户配置")
        
        if fixed_count == 0:
            print(f"   ✅ 所有用户配置的模型名称都正确")
        else:
            print(f"   ✅ 共修复 {fixed_count} 个用户配置")
    else:
        print("   ℹ️  未找到使用 deepseek 的用户配置")
    print()
    
    # 3. 修复 system_configs 配置
    print("📋 检查 system_configs 配置...")
    system_configs = list(db.system_configs.find({
        "$or": [
            {"key": {"$regex": "deepseek.*model", "$options": "i"}},
            {"key": {"$regex": ".*deepseek.*", "$options": "i"}, "value": {"$ne": correct_model}}
        ]
    }))
    if system_configs:
        fixed_count = 0
        for config in system_configs:
            old_value = config.get("value", "N/A")
            if old_value != correct_model and "model" in config.get("key", "").lower():
                print(f"   发现错误配置: {config.get('key')} = {old_value} -> {correct_model}")
                db.system_configs.updateOne(
                    {"_id": config["_id"]},
                    {"$set": {"value": correct_model}}
                )
                fixed_count += 1
                print(f"   ✅ 已更新")
        
        if fixed_count == 0:
            print(f"   ✅ 所有系统配置都正确")
        else:
            print(f"   ✅ 共修复 {fixed_count} 个系统配置")
    else:
        print("   ℹ️  未找到相关的系统配置")
    print()
    
    # 关闭连接
    client.close()
    
    print("=" * 80)
    print("✅ 修复完成！")
    print("=" * 80)
    print()
    print("📝 后续步骤:")
    print("   1. 重启应用: python -m app")
    print("   2. 测试 DeepSeek 调用是否正常")
    print("   3. 如果仍有问题，检查 .env 文件中的 DEEPSEEK_MODEL 配置")
    print()

if __name__ == "__main__":
    fix_deepseek_model()

