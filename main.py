import time
import json
import logging
import os
import requests
import sys
import re
from datetime import datetime
import pytz

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

KEY_COMPONENTS = ("BearBoss_Is_Watching", "_You_XHG")


def setup_logging():
    if not os.path.exists('log'): os.makedirs('log')
    log_filename = datetime.now().strftime('renewal_log_%Y-%m-%d_%H-%M-%S.log')
    log_filepath = os.path.join('log', log_filename)
    logger = logging.getLogger('RenewalBot')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    if not logger.handlers:
        fh = logging.FileHandler(log_filepath, encoding='utf-8');
        fh.setFormatter(formatter);
        logger.addHandler(fh)
        ch = logging.StreamHandler();
        ch.setFormatter(formatter);
        logger.addHandler(ch)
    return logger


def load_configs(logger):
    try:
        account_config_str = os.environ['ACCOUNT_CONFIG_JSON']
        telegram_config_str = os.environ['TELEGRAM_CONFIG_JSON']
        account_config = json.loads(account_config_str)
        telegram_config = json.loads(telegram_config_str)
        logger.info("从环境变量中加载并解析JSON配置成功。")
        return account_config, telegram_config
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"加载或解析JSON配置失败: {e}")
        return None, None


def escape_markdown_v2(text):
    """转义Telegram MarkdownV2的特殊字符"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


def send_telegram_message(tg_config, text):
    if not tg_config or not tg_config.get('bot_token') or not tg_config.get('chat_id'):
        logging.error("Telegram配置不完整，无法发送通知。")
        return
    api_url = f"https://api.telegram.org/bot{tg_config['bot_token']}/sendMessage"
    payload = {'chat_id': tg_config['chat_id'], 'text': text, 'parse_mode': 'MarkdownV2'}
    try:
        response = requests.post(api_url, data=payload, timeout=10)
        if response.status_code != 200:
            logging.error(f"发送Telegram通知失败，状态码: {response.status_code}, 响应: {response.text}")
    except Exception as e:
        logging.error(f"发送 Telegram 通知失败: {e}")


def get_master_key():
    return "".join(KEY_COMPONENTS)


def renew_single_product(driver, product_id, logger):
    wait = WebDriverWait(driver, 10)
    product_url = f"https://vps.polarbear.nyc.mn/control/detail/{product_id}/"

    try:
        logger.info(f"--- 开始处理产品ID: {product_id} ---")
        driver.get(product_url)

        before_date_str = get_expiry_date(driver, wait)
        if not before_date_str:
            return f"❌ *产品ID `{product_id}` 处理失败* \\(无法获取操作前日期\\)"

        logger.info(f"产品 {product_id} 操作前到期时间: {before_date_str}")

        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '续费产品')]"))).click()
        time.sleep(2)

        submit_button_xpath = "//input[contains(@class, 'install-complete')]"
        submit_buttons = driver.find_elements(By.XPATH, submit_button_xpath)

        if submit_buttons:
            driver.execute_script("arguments[0].click();", submit_buttons[0])
            logger.info(f"产品 {product_id}: 已执行点击'续期'操作。")
            time.sleep(5)
            driver.refresh()
        else:
            logger.warning(f"产品 {product_id}: 未发现'续期'按钮，跳过点击。")

        after_date_str = get_expiry_date(driver, wait)
        if not after_date_str:
            return f"❌ *产品ID `{product_id}` 处理失败* \\(无法获取操作后日期\\)"

        # 【修复】对所有包含特殊字符的返回字符串进行转义
        if before_date_str != after_date_str:
            return f"✅ *产品ID `{product_id}` 续费成功* \\(从 `{before_date_str}` 到 `{after_date_str}`\\)"
        else:
            return f"ℹ️ *产品ID `{product_id}` 状态未变* \\(到期日: `{before_date_str}`\\)"

    except Exception as e:
        logger.error(f"处理产品ID {product_id} 时发生错误。", exc_info=True)
        error_text = escape_markdown_v2(str(e).splitlines()[0])
        return f"❌ *产品ID `{product_id}` 处理失败* \\(错误: `{error_text}`\\)"


def get_expiry_date(driver, wait):
    try:
        list_item_xpath = "//li[contains(text(), '到期时间')]"
        list_item = wait.until(EC.presence_of_element_located((By.XPATH, list_item_xpath)))
        full_text = list_item.text
        parts = full_text.split(' ')
        return parts[parts.index('到期时间') + 1]
    except Exception:
        return None


def main():
    logger = setup_logging()
    account_config, tg_config = load_configs(logger)
    if not account_config: sys.exit(1)

    if account_config.get('script_secret_key') != get_master_key():
        logger.error("密钥验证失败！程序退出。");
        sys.exit()
    logger.info("密钥验证成功，准许执行。")

    start_time = time.monotonic()
    beijing_tz = pytz.timezone('Asia/Shanghai')
    start_time_str = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
    send_telegram_message(tg_config, f"🚀 *ArcticCloud续期任务启动*\n\n*开始时间:* `{start_time_str}`")

    driver = None
    results = []
    final_report = ""
    try:
        logger.info("初始化浏览器并登录账户...")
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless");
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage");
        chrome_options.add_argument("--window-size=1920,1080")
        service = ChromeService(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("https://vps.polarbear.nyc.mn/index/login/")
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.NAME, "swapname"))).send_keys(account_config['username'])
        driver.find_element(By.NAME, "swappass").send_keys(account_config['password'])
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(3)
        logger.info("登录成功。")

        product_ids = account_config.get("product_ids", [])
        logger.info(f"即将处理 {len(product_ids)} 个产品: {product_ids}")
        for pid in product_ids:
            result_message = renew_single_product(driver, pid, logger)
            results.append(result_message)

        final_report = "📝 *任务总结报告*\n\n" + "\n".join(results)

    except Exception as e:
        logger.error("在主流程中发生严重错误。", exc_info=True)
        error_text = escape_markdown_v2(str(e).splitlines()[0])
        final_report = f"❌ *主流程执行失败*\n\n错误: `{error_text}`"

    finally:
        if driver: driver.quit()
        end_time = time.monotonic()
        end_time_str = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
        duration = round(end_time - start_time)
        timing_info = f"\n\n*结束时间:* `{end_time_str}`\n*总耗时:* `{duration} 秒`"
        schedule_info = "\n*任务计划:* `每2天自动运行一次`"

        if not final_report:
            final_report = "🤔 *任务意外结束，未生成报告*"

        final_report += timing_info + schedule_info
        final_report += "\n\n`我要告诉熊老板你开挂！--by  XHG`"
        send_telegram_message(tg_config, final_report)
        logger.info("=" * 10 + " 自动续期任务结束 " + "=" * 10)


if __name__ == "__main__":
    main()