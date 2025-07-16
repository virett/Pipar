# Файл: app.py (версия с выбором типа отчета)
from flask import Flask, render_template, request, redirect, url_for
import webbrowser
from threading import Timer
import data_logic
from datetime import date, timedelta

app = Flask(__name__)

@app.route('/')
def index():
    return redirect(url_for('daily_report'))

@app.route('/daily_report')
def daily_report():
    # Получаем параметры из URL
    report_type = request.args.get('type', 'period') # 'period' или 'daily'
    period_days = request.args.get('days', '7') # 7 или 30
    selected_date = request.args.get('date', date.today().isoformat())
    
    report_data_html = ""
    report_title = ""

    if report_type == 'daily':
        # Если запрошен отчет за ОДИН день
        report_data = data_logic.get_daily_report_data(selected_date)
        report_title = f"Детальный отчет за: {selected_date}"
    else:
        # Если запрошен СВОДНЫЙ отчет за период
        end_date = date.today()
        start_date = end_date - timedelta(days=int(period_days) - 1)
        report_data = data_logic.get_period_summary_report(start_date.isoformat(), end_date.isoformat())
        report_title = f"Сводный отчет за последние {period_days} дней"
        
    # Превращаем DataFrame в HTML-таблицу
    if not report_data.empty:
        report_data_html = report_data.to_html(index=False, classes='table table-striped table-hover', justify='center')

    # Получаем список дат для календаря
    available_dates = data_logic.get_available_dates()

    return render_template('daily_report.html', 
                           report_table=report_data_html, 
                           report_title=report_title,
                           available_dates=available_dates,
                           selected_date=selected_date,
                           active_period=period_days,
                           report_type=report_type)

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == '__main__':
    Timer(1, open_browser).start()
    app.run(host='127.0.0.1', port=5000, debug=False)