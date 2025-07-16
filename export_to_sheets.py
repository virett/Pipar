# ===================================================================================
# ФАЙЛ: export_to_sheets.py (С УЧЕТОМ РЕГИОНАЛЬНЫХ НАСТРОЕК)
# ===================================================================================
import gspread
from gspread_pandas import Spread
import pandas as pd
import sqlite3
import numpy as np
import re
import os

# --- НАСТРОЙКИ ---
GOOGLE_CREDS_FILE = 'google_credentials.json'
SHEET_NAME = 'Pinterest Stats Export'
DB_FILE = 'pinterest_stats.db'

# --- ФУНКЦИИ ОЧИСТКИ ДАННЫХ ---
def clean_value(value):
    if not isinstance(value, str):
        return np.nan
    match = re.search(r'([\d\.,]+)', value)
    if match:
        try:
            return float(match.group(1).replace(',', '.'))
        except (ValueError, TypeError):
            return np.nan
    return np.nan

def convert_views(view_str):
    if not isinstance(view_str, str):
        return np.nan
    view_str = view_str.lower().strip()
    try:
        if 'k' in view_str:
            return float(view_str.replace('k', '')) * 1000
        return float(view_str)
    except (ValueError, TypeError):
        return np.nan

def export_data_to_sheets():
    """Подключается к БД, забирает все данные и выгружает их в Google Таблицу."""
    try:
        # ... (код подключения к БД и загрузки данных остается без изменений) ...
        conn = sqlite3.connect(DB_FILE)
        query = "SELECT p.profile_name, s.report_date, s.followers, s.monthly_views, s.pin_count, p.profile_url, p.landing_url, p.email FROM DailyStats s JOIN Profiles p ON s.profile_id = p.id ORDER BY p.profile_name, s.report_date"
        df = pd.read_sql_query(query, conn)
        conn.close()

        # Очистка и преобразование данных
        df['followers'] = df['followers'].apply(clean_value)
        df['monthly_views'] = df['monthly_views'].apply(convert_views)
        df['pin_count'] = pd.to_numeric(df['pin_count'], errors='coerce')
        print(f"[ОК] Данные успешно загружены и очищены ({len(df)} строк).")

        # ======================= ГЛАВНОЕ ИЗМЕНЕНИЕ =======================
        # Перед выгрузкой преобразуем числовые столбцы в строки и заменяем точку на запятую
        for col in ['followers', 'monthly_views', 'pin_count']:
             # astype(str) превращает число в текст, .str.replace() меняет точку на запятую
            df[col] = df[col].astype('Int64').astype(str).str.replace('.', ',', regex=False).replace('<NA>', '', regex=False)
        print("[ИНФО] Числовые данные подготовлены для выгрузки (замена '.' на ',').")
        # ===================== КОНЕЦ ИЗМЕНЕНИЯ =======================
        
        print(f"[ИНФО] Подключаемся к Google Sheets и открываем таблицу '{SHEET_NAME}'...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        creds_path = os.path.join(script_dir, GOOGLE_CREDS_FILE)
        gc = gspread.service_account(filename=creds_path)
        spread = Spread(SHEET_NAME, client=gc)
        print("[ОК] Авторизация и доступ к таблице прошли успешно.")
        
        spread.df_to_sheet(df, index=False, sheet='Sheet1', start='A1', replace=True)
        
        print(f"[ОК] Данные успешно выгружены в таблицу '{SHEET_NAME}'.")
        print("\n=======================================================")
        print("             РАБОТА СКРИПТА УСПЕШНО ЗАВЕРШЕНА")
        print("=======================================================")

    except Exception as e:
        print(f"[КРИТИЧЕСКАЯ ОШИБКА] Текст ошибки: {e}")

if __name__ == '__main__':
    export_data_to_sheets()
    input("\nНажмите Enter для выхода...")