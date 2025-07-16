# =================================================================
# ФАЙЛ: data_logic.py (ПОЛНАЯ ВЕРСИЯ С ОБЕИМИ ФУНКЦИЯМИ ОТЧЕТОВ)
# =================================================================
import sqlite3
import pandas as pd
import re
from datetime import date, timedelta

DB_FILE = 'pinterest_stats.db'

def natural_sort_key(s):
    """Ключ для "естественной" сортировки."""
    match = re.search(r'(\d+)$', s)
    if not match: return (s, 0)
    return (s[:match.start()], int(match.group(1)))

def clean_and_convert_numeric(value):
    """Универсальная функция для очистки и преобразования в число."""
    if pd.isna(value): return 0
    value_str = str(value).lower().strip()
    multiplier = 1000 if 'k' in value_str else 1
    cleaned_str = re.sub(r'[^\d\.]', '', value_str)
    try:
        return float(cleaned_str) * multiplier if cleaned_str else 0
    except (ValueError, TypeError):
        return 0

# --- ВОЗВРАЩАЕМ ФУНКЦИЮ ДЛЯ ДЕТАЛЬНОГО ОТЧЕТА ---
def get_daily_report_data(selected_date: str):
    """
    Возвращает детальный отчет за ОДИН выбранный день.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        # Нам нужен и выбранный день, и предыдущий для расчета
        day_before = (date.fromisoformat(selected_date) - timedelta(days=1)).isoformat()
        
        query = f"""
        SELECT 
            p.profile_name,
            s.report_date,
            s.monthly_views,
            s.pin_count
        FROM DailyStats s
        JOIN Profiles p ON s.profile_id = p.id
        WHERE s.report_date = '{selected_date}' OR s.report_date = '{day_before}'
        ORDER BY p.profile_name, s.report_date
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty: return pd.DataFrame()

        df['monthly_views'] = df['monthly_views'].apply(clean_and_convert_numeric)
        df['pin_count'] = df['pin_count'].apply(clean_and_convert_numeric)
        
        df['views_growth'] = df.groupby('profile_name')['monthly_views'].diff().fillna(0)
        df['pins_growth'] = df.groupby('profile_name')['pin_count'].diff().fillna(0)
        
        report_df = df[df['report_date'] == selected_date].copy()
        
        report_df['sort_key'] = report_df['profile_name'].apply(natural_sort_key)
        report_df = report_df.sort_values(by='sort_key').drop(columns=['sort_key'])

        report_df = report_df.rename(columns={
            'report_date': 'Дата',
            'profile_name': 'Профиль',
            'monthly_views': 'Просмотры',
            'pin_count': 'Пины',
            'views_growth': 'Прирост просмотров',
            'pins_growth': 'Прирост пинов'
        })
        
        for col in ['Просмотры', 'Пины', 'Прирост просмотров', 'Прирост пинов']:
            report_df[col] = report_df[col].astype(int)

        return report_df[['Дата', 'Профиль', 'Просмотры', 'Пины', 'Прирост просмотров', 'Прирост пинов']]
        
    except Exception as e:
        print(f"Ошибка при получении детального отчета: {e}")
        return pd.DataFrame()

# --- ФУНКЦИЯ ДЛЯ СВОДНОГО ОТЧЕТА ОСТАЕТСЯ БЕЗ ИЗМЕНЕНИЙ ---
def get_period_summary_report(start_date: str, end_date: str):
    """
    Рассчитывает СВОДНЫЙ отчет за период.
    Возвращает одну строку на профиль с суммарным приростом.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        day_before_start = (date.fromisoformat(start_date) - timedelta(days=1)).isoformat()
        
        query = f"""
        SELECT 
            p.profile_name,
            s.report_date,
            s.monthly_views,
            s.pin_count
        FROM DailyStats s
        JOIN Profiles p ON s.profile_id = p.id
        WHERE s.report_date BETWEEN '{day_before_start}' AND '{end_date}'
        ORDER BY p.profile_name, s.report_date
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty: return pd.DataFrame()

        df['monthly_views'] = df['monthly_views'].apply(clean_and_convert_numeric)
        df['pin_count'] = df['pin_count'].apply(clean_and_convert_numeric)
        
        df['views_growth'] = df.groupby('profile_name')['monthly_views'].diff()
        df['pins_growth'] = df.groupby('profile_name')['pin_count'].diff()

        period_df = df[df['report_date'] >= start_date].copy()

        summary = period_df.groupby('profile_name').agg(
            total_views_growth=('views_growth', 'sum'),
            total_pins_growth=('pins_growth', 'sum'),
            last_views=('monthly_views', 'last'),
            last_pins=('pin_count', 'last')
        ).reset_index()

        summary['sort_key'] = summary['profile_name'].apply(natural_sort_key)
        summary = summary.sort_values(by='sort_key').drop(columns=['sort_key'])

        summary = summary.rename(columns={
            'profile_name': 'Профиль',
            'last_views': 'Просмотры (тек.)',
            'last_pins': 'Пины (тек.)',
            'total_views_growth': 'Прирост просмотров за период',
            'total_pins_growth': 'Прирост пинов за период'
        })

        for col in summary.columns:
            if 'Прирост' in col or 'Пины' in col or 'Просмотры' in col:
                summary[col] = summary[col].fillna(0).astype(int)
        
        return summary[['Профиль', 'Просмотры (тек.)', 'Пины (тек.)', 'Прирост просмотров за период', 'Прирост пинов за период']]

    except Exception as e:
        print(f"Ошибка при создании сводного отчета: {e}")
        return pd.DataFrame()

def get_available_dates():
    """Эта функция остается без изменений."""
    try:
        conn = sqlite3.connect(DB_FILE)
        dates = pd.read_sql_query("SELECT DISTINCT report_date FROM DailyStats ORDER BY report_date DESC", conn)
        conn.close()
        return dates['report_date'].tolist()
    except Exception as e:
        print(f"Ошибка при получении дат: {e}")
        return []