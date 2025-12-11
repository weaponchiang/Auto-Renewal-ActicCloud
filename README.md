# ArcticCloud 自动续期

自动续期 ArcticCloud 免费 VPS 产品，支持 GitHub Actions 定时运行。

## 功能

- ✅ 自动登录续期
- ✅ 支持多产品同时续期
- ✅ 智能调整运行间隔（根据到期时间自动计算）
- ✅ 随机化运行时间（避免被识别为脚本）
- ✅ Telegram 推送通知
- ✅ 失败时提供手动续期链接

## 配置

在 GitHub 仓库 → Settings → Secrets and variables → Actions 添加以下 Secrets：

### 1. CONFIG
**名称**: `CONFIG`

**值** (JSON格式):
```json
{
  "username": "你的用户名",
  "password": "你的密码",
  "product_ids": [974],
  "run_interval_days": 4,
  "telegram_bot_token": "可选，TG Bot Token",
  "telegram_chat_id": "可选，TG Chat ID"
}
```

不需要 Telegram 通知的话，把 `telegram_bot_token` 和 `telegram_chat_id` 留空字符串 `""`。

### 2. PAT (Personal Access Token)
**名称**: `PAT`

**获取方法**:
1. 访问 GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. 点击 "Generate new token" → "Generate new token (classic)"
3. 设置 Token 名称，选择过期时间
4. 勾选权限：
   - `repo` (Full control of private repositories)
   - `workflow` (Update GitHub Action workflows)
5. 点击 "Generate token"，复制生成的 token (形如 `ghp_xxx`)
6. 将 token 粘贴到 Secret 的值中

## 使用

1. Fork 本仓库
2. 配置 Secrets
3. 启用 Actions
4. 手动触发一次或等待自动运行

## License

MIT
