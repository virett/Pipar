# =================================================================
# ФАЙЛ: pinal.py (ПРАВИЛЬНАЯ МНОГОПОТОЧНАЯ ВЕРСИЯ)
# =================================================================
import json
import os
import re
from playwright.sync_api import sync_playwright, Page, TimeoutError
import database as db
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Константы ---
COOKIES_FILE = 'pinterest.json'
SESSION_FILE = 'pinterest_session.json'
MAX_WORKERS = 10  # Количество одновременных потоков

def normalize_cookies(cookies: list) -> list:
    normalized = []
    for cookie in cookies:
        if 'sameSite' in cookie:
            same_site_value = cookie['sameSite'].lower()
            if same_site_value == 'strict': cookie['sameSite'] = 'Strict'
            elif same_site_value == 'lax': cookie['sameSite'] = 'Lax'
            else: cookie['sameSite'] = 'None'
        normalized.append(cookie)
    return normalized

def get_profile_data(page: Page, target_board_name: str) -> dict:
    # ЭТА ФУНКЦИЯ ВЗЯТА ИЗ ВАШЕЙ РАБОЧЕЙ ВЕРСИИ. Я ЕЕ НЕ ТРОГАЛ.
    print(f"[ИНФО] Начинаем сбор данных для доски '{target_board_name}'...")
    data = {"followers": None, "monthly_views": None, "pin_count": None}
    timeout = 15000
    try:
        followers_text = page.locator('[data-test-id="profile-following-count"]').text_content(timeout=5000)
        data['followers'] = followers_text.strip()
        print(f"  [ОК] Найдены подписчики (following): {data['followers']}")
    except Exception:
        print("  [ИНФО] Элемент 'profile-following-count' не найден.")
    try:
        stats_container = page.locator("div:has-text('monthly views')").first
        full_stats_text = stats_container.text_content(timeout=timeout)
        views_match = re.search(r'([\d\.,\s]+[kKmM]?)\s*monthly views', full_stats_text, re.IGNORECASE)
        if views_match:
            data['monthly_views'] = views_match.group(1).strip()
            print(f"  [ОК] Найдены просмотры: {data['monthly_views']}")
    except Exception:
        print("  [ИНФО] Элемент, содержащий 'monthly views', не найден.")
    try:
        board_card = page.locator(f'[data-test-id="pwt-grid-item"]:has-text("{target_board_name}")')
        board_card.first.wait_for(timeout=timeout)
        pin_stats_text = board_card.first.get_by_text("Pins").text_content(timeout=5000)
        pin_count_match = re.search(r'(\d+)', pin_stats_text)
        if pin_count_match:
            data["pin_count"] = pin_count_match.group(1).strip()
            print(f"  [ОК] Найдено пинов на доске: {data['pin_count']}")
    except TimeoutError:
        print(f"  [ОШИБКА] Таймаут! Не удалось найти доску '{target_board_name}'.")
    except Exception as e:
        print(f"  [ОШИБКА] Неизвестная ошибка при поиске пинов: {e}")
    return data

# НОВАЯ ФУНКЦИЯ: обрабатывает один профиль. Полностью изолирована.
def process_single_profile(profile_info):
    profile_id, profile_name, profile_url, target_board_name = profile_info
    
    print("\n" + "="*50)
    print(f"[РАБОТА] Поток для '{profile_name}' (ID: {profile_id}) запущен.")
    
    # КАЖДЫЙ ПОТОК СОЗДАЕТ СВОЙ СОБСТВЕННЫЙ ЭКЗЕМПЛЯР PLAYWRIGHT И БРАУЗЕРА
    with sync_playwright() as p:
        storage_state = SESSION_FILE if os.path.exists(SESSION_FILE) else None
        browser = p.chromium.launch(headless=True, channel="chrome")
        context = browser.new_context(storage_state=storage_state)
        page = context.new_page()
        
        try:
            page.goto(profile_url, timeout=60000, wait_until="domcontentloaded")
            page.locator('h1').wait_for(timeout=20000)
            print(f"[ИНФО] Страница для '{profile_name}' загружена.")
            
            parsed_data = get_profile_data(page, target_board_name)

            if any(v is not None for v in parsed_data.values()):
                db.save_daily_stat(profile_id, parsed_data)
            else:
                print(f"[ПРЕДУПРЕЖДЕНИЕ] Для '{profile_name}' не собрано данных.")

        except Exception as e:
            # Логирование ошибок остается на месте
            print(f"\n[КРИТИЧЕСКАЯ ОШИБКА] Профиль '{profile_name}': {e}")
        finally:
            page.close()
            context.close()
            browser.close()
            print(f"--- Поток для '{profile_name}' завершен. ---")

def main():
    """Основная функция, которая управляет пулом потоков."""
    db.initialize_database()
    profiles_to_parse = db.get_active_profiles()
    if not profiles_to_parse:
        print("[ИНФО] В базе данных нет активных профилей для парсинга.")
        return
    print(f"[ИНФО] Найдено {len(profiles_to_parse)} профилей для обработки в {MAX_WORKERS} потоков.")

    # Создаем пул потоков и раздаем ему задачи
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # executor.map автоматически распределяет задачи и собирает результаты
        # Это более простой и надежный способ
        executor.map(process_single_profile, profiles_to_parse)

    print("\n[ИНФО] ВСЕ РАБОТЫ ЗАВЕРШЕНЫ.")

if __name__ == "__main__":
    main()