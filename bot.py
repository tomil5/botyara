import requests
from bs4 import BeautifulSoup
import telebot
import threading
import time
import os
import json

# 🔐 Настройки
TOKEN = '8172278638:AAF9TSTDai55zMB0Wjn7jwNzXXn3ZIYJrFc'
bot = telebot.TeleBot(TOKEN)

# 📁 Файлы хранения
SEEN_FILE = "seen_ads.json"
USERS_FILE = "users.json"

# 🌍 Ссылки на Avito
URLS = {
    "Кировская область": "https://www.avito.ru/kirovskaya_oblast/avtomobili/do-200000-rubley-ASgCAgECAUXGmgwWeyJmcm9tIjowLCJ0byI6MjAwMDAwfQ?f=ASgBAgECAUTutg3qtygBRcaaDBZ7ImZyb20iOjAsInRvIjoyMDAwMDB9"
}

# 🔁 Загрузка/сохранение просмотренных объявлений
def load_seen_ads():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, 'r') as f:
            return set(json.load(f))
    return set()

def save_seen_ads():
    with open(SEEN_FILE, 'w') as f:
        json.dump(list(seen_ads), f)

seen_ads = load_seen_ads()

# 👥 Загрузка/сохранение пользователей
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return set(json.load(f))
    return set()

def save_users():
    with open(USERS_FILE, 'w') as f:
        json.dump(list(allowed_users), f)

allowed_users = load_users()

# 🔍 Парсинг Avito
def fetch_ads():
    ads = []
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    for region, url in URLS.items():
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"⚠️ Ошибка загрузки {region}: код {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.find_all('div', attrs={"data-marker": "item"})

            for item in items:
                link_tag = item.find('a', href=True)
                if not link_tag:
                    continue

                href = link_tag['href']
                full_link = "https://www.avito.ru" + href

                # Получаем ID из ссылки
                ad_id = href.split('_')[-1].split('?')[0]  # Надёжный способ вытащить ID

                title = link_tag.get_text(strip=True)
                price_tag = item.find(attrs={"data-marker": "item-price"})
                price = price_tag.get_text(strip=True) if price_tag else "Цена не указана"

                ads.append((region, title, price, full_link, ad_id))

        except Exception as e:
            print(f"❌ Ошибка при обработке {region}: {e}")
    return ads

# 📤 Отправка новых объявлений
def check_and_send_new_ads():
    ads = fetch_ads()
    new_ads = []

    for region, title, price, link, ad_id in ads:
        if ad_id not in seen_ads:
            seen_ads.add(ad_id)
            new_ads.append((region, title, price, link))

    if new_ads:
        save_seen_ads()
        print(f"✅ Найдено новых объявлений: {len(new_ads)}")

    for region, title, price, link in new_ads:
        msg = f"🚗 *{region}*\n*{title}*\n💰 {price}\n🔗 [Смотреть объявление]({link})"
        for user_id in allowed_users:
            try:
                bot.send_message(user_id, msg, parse_mode="Markdown")
            except Exception as e:
                print(f"❗ Не удалось отправить сообщение {user_id}: {e}")
    print(f"[DEBUG] Добавлен ID: {ad_id}")

# 🧾 Команды бота
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.chat.id)
    if user_id not in allowed_users:
        allowed_users.add(user_id)
        save_users()
        bot.send_message(message.chat.id, "✅ Вы были добавлены в список подписчиков.")
    else:
        bot.send_message(message.chat.id, "Вы уже в списке подписчиков.")

    bot.send_message(message.chat.id, "Привет! Я бот, который мониторит объявления на Авито.\n"
                                      "Команды:\n"
                                      "/check — проверить новые объявления\n"
                                      "/current — показать текущие объявления\n"
                                      "/help — помощь")

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, "Команды:\n"
                          "/check — проверить новые объявления\n"
                          "/current — текущие объявления\n"
                          "/start — подписка на обновления")

@bot.message_handler(commands=['check'])
def manual_check(message):
    bot.reply_to(message, "🔍 Проверяю новые объявления...")
    check_and_send_new_ads()

@bot.message_handler(commands=['current'])
def current_ads(message):
    bot.reply_to(message, "Вот текущие объявления:")
    ads = fetch_ads()
    if not ads:
        bot.send_message(message.chat.id, "Объявлений не найдено.")
        return
    for region, title, price, link, ad_id in ads[:10]:  # Ограничим до 10
        msg = f"🚗 *{region}*\n{title}\n💰 {price}\n🔗 [Смотреть объявление]({link})"
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        time.sleep(1)  # Пауза, чтобы не попасть под лимиты Telegram

# 🔁 Автопроверка раз в 5 минут
def periodic_check():
    while True:
        try:
            check_and_send_new_ads()
        except Exception as e:
            print(f"⚠️ Ошибка в потоке: {e}")
        time.sleep(300)

# ▶️ Запуск
threading.Thread(target=periodic_check, daemon=True).start()
print("🤖 Бот запущен.")
bot.polling()
