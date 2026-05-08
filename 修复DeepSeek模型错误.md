# 修复 DeepSeek "Model Not Exist" 错误

## 错误信息

```
❌ [DeepSeek] 调用失败: Error code: 400 - {'error': {'message': 'Model Not Exist', 'type': 'invalid_request_error', 'param': None, 'code': 'invalid_request_error'}}
```

## 问题原因

这个错误表示配置的 DeepSeek 模型名称不正确。DeepSeek API 只支持特定的模型名称。

## 解决方案

### 方法 1：检查并修复配置中的模型名称（推荐）

#### 1. 检查当前配置的模型名称

```powershell
# 进入项目目录
cd D:\AI-Traiding\TradingAgents-CN

# 检查环境变量
echo $env:DEEPSEEK_MODEL

# 或者查看 .env 文件
Get-Content .env | Select-String "DEEPSEEK"
```

#### 2. 正确的 DeepSeek 模型名称

DeepSeek API 支持的模型名称：

| 模型名称 | 说明 | 推荐场景 |
|---------|------|---------|
| **deepseek-chat** | 通用对话模型（推荐） | 股票分析、投资建议 |
| **deepseek-coder** | 代码生成模型 | 代码分析、技术指标计算 |

⚠️ **重要**：不要使用以下错误的模型名称：
- ❌ `deepseek-v3`
- ❌ `deepseek-chat-v3`
- ❌ `deepseek-reasoner`
- ❌ `deepseek-r1`
- ❌ 其他自定义名称

#### 3. 修复配置

**选项 A：修改 .env 文件**

编辑 `.env` 文件，确保使用正确的模型名称：

```bash
# DeepSeek 配置
DEEPSEEK_API_KEY=sk-your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

**选项 B：通过 Web 界面修改**

1. 启动应用：`python -m app`
2. 访问前端界面
3. 进入"设置" -> "大模型厂家"
4. 找到 DeepSeek 配置
5. 将模型名称改为 `deepseek-chat`

**选项 C：通过数据库修改**

```powershell
# 连接 MongoDB
docker exec -it tradingagents-mongodb mongosh -u admin -p tradingagents123

# 切换到数据库
use tradingagents

# 查看当前配置
db.llm_providers.find({"provider": "deepseek"}).pretty()

# 更新模型名称
db.llm_providers.updateOne(
  {"provider": "deepseek"},
  {"$set": {"model_name": "deepseek-chat"}}
)

# 或者更新用户配置
db.user_configs.updateMany(
  {"llm_provider": "deepseek"},
  {
    "$set": {
      "quick_think_llm": "deepseek-chat",
      "deep_think_llm": "deepseek-chat"
    }
  }
)
```

### 方法 2：使用脚本修复配置

创建一个修复脚本：

```python
# scripts/fix_deepseek_model.py
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pymongo import MongoClient
from app.core.config import settings

def fix_deepseek_model():
    """修复 DeepSeek 模型名称配置"""
    print("🔧 修复 DeepSeek 模型配置...")
    
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    
    # 修复 llm_providers 配置
    result1 = db.llm_providers.updateMany(
        {"provider": "deepseek", "model_name": {"$ne": "deepseek-chat"}},
        {"$set": {"model_name": "deepseek-chat"}}
    )
    print(f"✅ 更新了 {result1.modified_count} 个 LLM 提供商配置")
    
    # 修复 user_configs 配置
    result2 = db.user_configs.updateMany(
        {"llm_provider": "deepseek"},
        {
            "$set": {
                "quick_think_llm": "deepseek-chat",
                "deep_think_llm": "deepseek-chat"
            }
        }
    )
    print(f"✅ 更新了 {result2.modified_count} 个用户配置")
    
    # 修复 system_configs 配置
    result3 = db.system_configs.updateMany(
        {"key": {"$regex": "deepseek.*model", "$options": "i"}},
        {"$set": {"value": "deepseek-chat"}}
    )
    print(f"✅ 更新了 {result3.modified_count} 个系统配置")
    
    client.close()
    print("✅ 修复完成！")

if __name__ == "__main__":
    fix_deepseek_model()
```

运行脚本：

```powershell
python scripts\fix_deepseek_model.py
```

### 方法 3：验证 API Key 和模型名称

```python
# scripts/test_deepseek_api.py
import os
import requests

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    print("❌ DEEPSEEK_API_KEY 未设置")
    exit(1)

# 测试 deepseek-chat 模型
url = "https://api.deepseek.com/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
data = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
}

response = requests.post(url, json=data, headers=headers)
if response.status_code == 200:
    print("✅ deepseek-chat 模型可用")
    print(response.json())
else:
    print(f"❌ 错误: {response.status_code}")
    print(response.text)
```

## 验证修复

修复后，重新运行应用并测试：

```powershell
# 重启应用
python -m app

# 在另一个终端测试
python scripts\test_deepseek_api.py
```

## 常见问题

### Q1: 为什么会出现 "Model Not Exist" 错误？

**A**: DeepSeek API 只支持特定的模型名称。如果使用了错误的模型名称（如 `deepseek-v3`），API 会返回此错误。

### Q2: 如何确认当前使用的模型名称？

**A**: 查看日志文件或运行以下命令：

```powershell
# 查看最近的错误日志
Get-Content logs\error.log -Tail 20 | Select-String "DeepSeek"
```

### Q3: 修复后仍然报错怎么办？

**A**: 检查以下几点：
1. ✅ API Key 是否正确
2. ✅ 模型名称是否为 `deepseek-chat` 或 `deepseek-coder`
3. ✅ 网络连接是否正常
4. ✅ DeepSeek API 服务是否可用

### Q4: 可以使用其他模型名称吗？

**A**: 不可以。DeepSeek API 只支持：
- `deepseek-chat` - 通用对话模型
- `deepseek-coder` - 代码生成模型

其他名称都会导致 "Model Not Exist" 错误。

## 预防措施

1. **使用默认配置**：系统默认使用 `deepseek-chat`，不要随意修改
2. **验证配置**：修改配置后，先测试 API 调用
3. **查看文档**：参考 DeepSeek 官方文档确认支持的模型名称

## 相关文档

- [DeepSeek 配置指南](docs/configuration/deepseek-config.md)
- [LLM 配置文档](docs/configuration/llm-config.md)
- [DeepSeek 官方文档](https://platform.deepseek.com/api-docs/)

## 快速修复命令

```powershell
# 1. 检查当前配置
Get-Content .env | Select-String "DEEPSEEK"

# 2. 修改 .env 文件（如果模型名称错误）
# 将 DEEPSEEK_MODEL=xxx 改为 DEEPSEEK_MODEL=deepseek-chat

# 3. 重启应用
python -m app
```

