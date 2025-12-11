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

在 GitHub 仓库 → Settings → Secrets and variables → Actions 添加一个 Secret：

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

## 使用

1. Fork 本仓库
2. 配置 Secrets
3. 启用 Actions
4. 手动触发一次或等待自动运行

## License

MIT
