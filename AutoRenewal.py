import requests
import re
import json
import time
import random
import os
from datetime import datetime, timedelta

# 加载配置（优先从环境变量读取，用于 GitHub Actions）
def load_config():
    if os.environ.get('CONFIG'):
        return json.loads(os.environ.get('CONFIG'))
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

config = load_config()
BASE_URL = "https://vps.polarbear.nyc.mn"
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
})

# 收集日志用于 Telegram 推送
log_messages = []

def log(msg):
    print(msg)
    log_messages.append(msg)


def send_telegram(message):
    """发送 Telegram 通知"""
    token = config.get('telegram_bot_token', '')
    chat_id = config.get('telegram_chat_id', '')
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=10
        )
    except:
        pass


def login():
    session.get(f"{BASE_URL}/index/login/?referer=", timeout=10)
    r = session.post(
        f"{BASE_URL}/index/login/?referer=",
        data={"swapname": config['username'], "swappass": config['password']},
        headers={"Origin": BASE_URL, "Referer": f"{BASE_URL}/index/login/?referer="},
        timeout=10, allow_redirects=True
    )
    return "success=" in r.url or any(x in r.text for x in ["登陆成功", "欢迎回来", "控制面板"])


def get_expiry_date(pid):
    r = session.get(f"{BASE_URL}/control/detail/{pid}/", timeout=10)
    m = re.search(r"到期时间</th>\s*<td>\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\s*</td>", r.text)
    if not m:
        raise RuntimeError("无法解析到期时间")
    return m.group(1).strip()


def renew_product(pid):
    before = get_expiry_date(pid)
    r = session.post(
        f"{BASE_URL}/control/detail/{pid}/pay/", data={},
        headers={"Origin": BASE_URL, "Referer": f"{BASE_URL}/control/detail/{pid}/"},
        timeout=10, allow_redirects=True
    )
    after = get_expiry_date(pid)
    success = "success=" in r.url or "免费产品已经帮您续期" in r.text
    return {'success': success, 'before': before, 'after': after, 'changed': before != after}


def update_workflow_cron(latest_expiry_date):
    try:
        expiry = datetime.strptime(latest_expiry_date, "%Y-%m-%d")
        days_until_expiry = (expiry - datetime.now()).days
        interval = max(1, days_until_expiry // 3)
        random_hour = random.randint(0, 23)
        random_minute = random.randint(0, 59)
        new_cron = f"{random_minute} {random_hour} */{interval} * *"
        
        # 计算下次运行时间（UTC 转北京时间 +8）
        next_run_utc = datetime.now() + timedelta(days=interval)
        next_run_utc = next_run_utc.replace(hour=random_hour, minute=random_minute, second=0)
        next_run_beijing = next_run_utc + timedelta(hours=8)
        
        log(f"\n📅 更新运行计划:")
        log(f"   到期日期: {latest_expiry_date}, 剩余 {days_until_expiry} 天")
        log(f"   运行间隔: 每 {interval} 天")
        log(f"   下次运行: {next_run_beijing.strftime('%Y-%m-%d %H:%M')} (北京时间)")
        
        workflow_path = '.github/workflows/auto-renewal.yml'
        with open(workflow_path, 'r', encoding='utf-8') as f:
            content = f.read()
        new_content = re.sub(r"- cron: '[^']*'", f"- cron: '{new_cron}'", content, count=1)
        with open(workflow_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        log(f"   ✅ Workflow 已更新")
        return True
    except Exception as e:
        log(f"   ⚠️ 更新失败: {e}")
        return False


def main():
    start = datetime.now()
    log(f"🚀 ArcticCloud续期任务启动")
    log(f"开始时间: {start.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if not login():
        log("❌ 登录失败")
        send_telegram("\n".join(log_messages))
        return
    
    success_count = fail_count = 0
    latest_expiry = None
    
    for pid in config['product_ids']:
        try:
            r = renew_product(pid)
            if r['success']:
                msg = f"从 {r['before']} 到 {r['after']}" if r['changed'] else f"到期: {r['after']}, 已达最大续期"
                log(f"✅ 产品 {pid} 续费成功 ({msg})")
                success_count += 1
                if not latest_expiry or r['after'] < latest_expiry:
                    latest_expiry = r['after']
            else:
                log(f"⚠️ 产品 {pid} 续费未生效 (到期: {r['before']})")
                log(f"   手动: {BASE_URL}/control/detail/{pid}/")
                fail_count += 1
        except Exception as e:
            log(f"❌ 产品 {pid} 失败: {e}")
            log(f"   手动: {BASE_URL}/control/detail/{pid}/")
            fail_count += 1
        
        if len(config['product_ids']) > 1 and pid != config['product_ids'][-1]:
            time.sleep(2)
    
    if latest_expiry:
        update_workflow_cron(latest_expiry)
    
    duration = int((datetime.now() - start).total_seconds())
    log(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"总耗时: {duration} 秒")
    log(f"📊 统计: 成功 {success_count}, 失败 {fail_count}")
    
    # 发送 Telegram 通知
    send_telegram("\n".join(log_messages))


if __name__ == "__main__":
    main()
