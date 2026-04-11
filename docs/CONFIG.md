# 用户配置指南

## 支持的 LLM 提供商

DarkFactory 支持多种 LLM 提供商：

### Anthropic 风格
- **Anthropic Claude** - `api.anthropic.com`
- **MiniMax** - 国产大模型

### OpenAI 风格
- **OpenAI** - GPT-4, GPT-3.5
- **Qwen (通义千问)** - 阿里云
- **DeepSeek** - 深度求索
- **其他 OpenAI 兼容 API**

---

## 快速开始

### 1. 环境变量配置

```bash
# 方式一: 直接设置（推荐）
export DARKFACTORY_API_KEY="your-api-key"
export DARKFACTORY_PROVIDER_TYPE="openai"  # 或 "anthropic"
export DARKFACTORY_MODEL="gpt-4o"

# 方式二: 提供商特定变量
export ANTHROPIC_API_KEY="sk-ant-xxxxx"
export OPENAI_API_KEY="sk-xxxxx"

# 方式三: 自定义端点（用于第三方提供商）
export DARKFACTORY_BASE_URL="https://api.minimax.chat/v1/text/chatcompletion_v2"
```

### 2. 配置文件

创建 `~/.darkfactory/config.json`:

```json
{
  "llm": {
    "provider_type": "openai",
    "api_key": "your-api-key",
    "base_url": "https://api.openai.com/v1/chat/completions",
    "model": "gpt-4o",
    "max_tokens": 4096,
    "temperature": 0.7
  },
  "agent": {
    "max_agents": 4
  }
}
```

---

## 提供商配置示例

### Anthropic Claude

```bash
export DARKFACTORY_PROVIDER_TYPE="anthropic"
export DARKFACTORY_API_KEY="sk-ant-xxxxx"
export DARKFACTORY_MODEL="claude-sonnet-4-20250514"
```

或配置文件中:

```json
{
  "llm": {
    "provider_type": "anthropic",
    "api_key": "sk-ant-xxxxx",
    "model": "claude-sonnet-4-20250514"
  }
}
```

### OpenAI GPT-4

```bash
export DARKFACTORY_PROVIDER_TYPE="openai"
export DARKFACTORY_API_KEY="sk-xxxxx"
export DARKFACTORY_MODEL="gpt-4o"
```

### MiniMax

```bash
export DARKFACTORY_PROVIDER_TYPE="anthropic"
export DARKFACTORY_API_KEY="your-minimax-key"
export DARKFACTORY_BASE_URL="https://api.minimax.chat/v1/text/chatcompletion_v2"
export DARKFACTORY_MODEL="MiniMax-Text-01"
```

配置文件:

```json
{
  "llm": {
    "provider_type": "anthropic",
    "api_key": "your-minimax-key",
    "base_url": "https://api.minimax.chat/v1/text/chatcompletion_v2",
    "model": "MiniMax-Text-01"
  }
}
```

### Qwen (通义千问)

```bash
export DARKFACTORY_PROVIDER_TYPE="openai"
export DARKFACTORY_API_KEY="your-qwen-key"
export DARKFACTORY_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export DARKFACTORY_MODEL="qwen-plus"
```

配置文件:

```json
{
  "llm": {
    "provider_type": "openai",
    "api_key": "your-qwen-key",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model": "qwen-plus"
  }
}
```

### DeepSeek

```bash
export DARKFACTORY_PROVIDER_TYPE="openai"
export DARKFACTORY_API_KEY="your-deepseek-key"
export DARKFACTORY_BASE_URL="https://api.deepseek.com/v1"
export DARKFACTORY_MODEL="deepseek-chat"
```

---

## 完整配置项

```json
{
  "llm": {
    "provider": "custom",
    "provider_type": "openai|anthropic",
    "api_key": "required",
    "base_url": "optional-custom-endpoint",
    "model": "model-name",
    "max_tokens": 4096,
    "temperature": 0.7,
    "timeout": 60,
    "extra": {}
  },
  "memory": {
    "memory_path": "./memory",
    "palace_path": "./memory/palace",
    "kg_path": "./memory/kg.db"
  },
  "agent": {
    "max_agents": 4,
    "max_retries": 3,
    "agent_timeout": 300
  },
  "validation": {
    "level": "relaxed|standard|strict",
    "auto_validate": true,
    "require_tests": true
  },
  "skill": {
    "auto_generate": true,
    "min_tool_calls": 5
  },
  "workspace": "."
}
```

---

## 验证配置

```bash
# 检查配置是否正确
python -c "
from src.config import load_config
try:
    cfg = load_config()
    print(f'Provider: {cfg.llm.provider_type.value}')
    print(f'Model: {cfg.llm.model}')
    print(f'API Key: {\"***\" + cfg.llm.api_key[-4:]}')
    print('Config is valid!')
except ValueError as e:
    print(f'Config error: {e}')
"
```

---

## 常见问题

### 1. API Key 无效
```
ValueError: Invalid API key
```
检查 API Key 是否正确，是否有空格或引号。

### 2.  Rate Limit
```
ValueError: Rate limit exceeded
```
减少请求频率或升级 API 套餐。

### 3. 网络问题
```
RuntimeError: Failed to call API
```
检查网络代理设置，或使用国内提供商（Qwen、MiniMax）。

### 4. 模型不支持
```
RuntimeError: Model not found
```
检查模型名称是否正确，参考提供商的模型列表。

---

## 获取 API Key

| 提供商 | 地址 | 说明 |
|--------|------|------|
| Anthropic | https://console.anthropic.com/ | Claude 系列 |
| OpenAI | https://platform.openai.com/ | GPT-4, GPT-3.5 |
| 阿里云 | https://dashscope.console.aliyun.com/ | 通义千问 |
| MiniMax | https://platform.minimax.chat/ | MiniMax 系列 |
| DeepSeek | https://platform.deepseek.com/ | DeepSeek 系列 |
