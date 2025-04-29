
import sys
import threading
import time
from datetime import datetime
import requests
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QLineEdit,
                             QTextEdit, QVBoxLayout, QHBoxLayout, QComboBox, QGridLayout, QFrame)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt
from binance.client import Client

API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"
client = Client(API_KEY, API_SECRET)

class TradingBot(QWidget):
    def __init__(self):
        super().__init__()
        self.total_profit = 0.0
        self.daily_profits = {}
        self.current_month = datetime.now().month
        self.current_year = datetime.now().year
        self.running = False
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Binance Auto Trading Bot (통합버전)")
        self.setStyleSheet("background-color: black; color: white;")
        font = QFont("Arial", 10, QFont.Bold)

        self.balance_label = QLabel('잔고: 0 USDT')
        self.balance_label.setFont(font)

        self.total_profit_label = QLabel('누적 수익률: 0.0%')
        self.total_profit_label.setFont(font)

        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems([
            'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'MEMEUSDT'
        ])

        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText('투자금 (USDT)')

        self.leverage_input = QLineEdit()
        self.leverage_input.setPlaceholderText('레버리지')

        self.position_combo = QComboBox()
        self.position_combo.addItems(['자동', '롱', '숏'])

        self.start_btn = QPushButton('매매 시작')
        self.start_btn.setStyleSheet("background-color: #00cc66; color: white;")
        self.start_btn.clicked.connect(self.start_trading)

        self.stop_btn = QPushButton('매매 중지')
        self.stop_btn.setStyleSheet("background-color: #cc0000; color: white;")
        self.stop_btn.clicked.connect(self.stop_trading)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background-color: #1e1e1e; color: white;")

        self.month_label = QLabel()
        self.month_label.setAlignment(Qt.AlignCenter)
        self.month_label.setFont(QFont("Arial", 12, QFont.Bold))

        self.prev_btn = QPushButton("◀")
        self.prev_btn.clicked.connect(self.prev_month)
        self.next_btn = QPushButton("▶")
        self.next_btn.clicked.connect(self.next_month)

        self.calendar_grid = QGridLayout()

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.prev_btn)
        top_layout.addWidget(self.month_label)
        top_layout.addWidget(self.next_btn)

        form_layout = QVBoxLayout()
        form_layout.addWidget(self.balance_label)
        form_layout.addWidget(self.total_profit_label)
        form_layout.addWidget(self.symbol_combo)
        form_layout.addWidget(self.amount_input)
        form_layout.addWidget(self.leverage_input)
        form_layout.addWidget(self.position_combo)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        form_layout.addLayout(button_layout)

        form_layout.addWidget(self.log_text)
        form_layout.addLayout(top_layout)

        cal_frame = QFrame()
        cal_frame.setLayout(self.calendar_grid)
        form_layout.addWidget(cal_frame)

        self.setLayout(form_layout)
        self.update_calendar()

    def update_calendar(self):
        for i in reversed(range(self.calendar_grid.count())):
            widget = self.calendar_grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self.month_label.setText(f"{self.current_year}년 {self.current_month:02d}월")
        days_in_week = ['일', '월', '화', '수', '목', '금', '토']
        for col, day in enumerate(days_in_week):
            label = QLabel(day)
            label.setStyleSheet("color: white; font-weight: bold;")
            label.setAlignment(Qt.AlignCenter)
            self.calendar_grid.addWidget(label, 0, col)

        first_day = datetime(self.current_year, self.current_month, 1)
        start_weekday = first_day.weekday()
        start_col = (start_weekday + 1) % 7
        row, col = 1, start_col
        day = 1
        while True:
            try:
                current_date = datetime(self.current_year, self.current_month, day)
            except ValueError:
                break

            date_str = current_date.strftime('%Y-%m-%d')
            pnl = self.daily_profits.get(date_str)
            label = QLabel(f"{day}")
            label.setAlignment(Qt.AlignCenter)

            if pnl is not None:
                color = "#00FF00" if pnl >= 0 else "#FF3333"
                label.setText(f"{day}\n{pnl:+.1f}%")
                label.setStyleSheet(f"color: {color};")

            self.calendar_grid.addWidget(label, row, col)
            col += 1
            if col > 6:
                col = 0
                row += 1
            day += 1

    def prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.update_calendar()

    def next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.update_calendar()

    def start_trading(self):
        self.running = True
        threading.Thread(target=self.trade_logic).start()

    def stop_trading(self):
        self.running = False
        self.log("매매 중지 요청됨.")

    def trade_logic(self):
        symbol = self.symbol_combo.currentText()
        try:
            balance = get_usdt_balance(client)
            self.balance_label.setText(f'잔고: {balance:.2f} USDT')
        except Exception as e:
            self.log(f'잔고 조회 실패: {e}')
            return

        try:
            amount = float(self.amount_input.text())
            leverage = int(self.leverage_input.text())
        except:
            self.log('투자금 또는 레버리지가 올바르지 않습니다.')
            return

        if amount > balance:
            self.log('투자금이 잔고를 초과했습니다.')
            return

        client.futures_change_leverage(symbol=symbol, leverage=leverage)
        entry_amount = amount * 0.4

        position_mode = self.position_combo.currentText()
        if position_mode == '롱':
            position_side = 'LONG'
        elif position_mode == '숏':
            position_side = 'SHORT'
        else:
            position_side = decide_position(symbol)

        if position_side == 'HOLD':
            self.log("진입 조건 미충족 → 대기")
            return

        side = 'BUY' if position_side == 'LONG' else 'SELL'
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type='MARKET',
            quantity=self.calc_quantity(symbol, entry_amount, leverage)
        )
        self.log(f'{position_side} 포지션 오픈: {order}')
        entry_price = float(order['fills'][0]['price'])

        while self.running:
            time.sleep(5)
            mark_price = float(client.futures_mark_price(symbol=symbol)['markPrice'])
            pnl_percent = ((mark_price - entry_price) / entry_price) * 100
            if side == 'SELL':
                pnl_percent *= -1

            self.log(f'현재 수익률: {pnl_percent:.2f}%')

            if pnl_percent >= 10 or pnl_percent <= -15:
                self.record_profit(pnl_percent)
                self.close_position(symbol, side)
                return

    def record_profit(self, pnl_percent):
        today = datetime.now().strftime('%Y-%m-%d')
        self.daily_profits[today] = pnl_percent
        self.total_profit += pnl_percent
        self.total_profit_label.setText(f'누적 수익률: {self.total_profit:.2f}%')
        self.update_calendar()

    def close_position(self, symbol, side):
        opposite = 'SELL' if side == 'BUY' else 'BUY'
        client.futures_create_order(
            symbol=symbol,
            side=opposite,
            type='MARKET',
            quantity=self.get_current_position_qty(symbol)
        )
        self.log("포지션 종료됨.")

    def get_current_position_qty(self, symbol):
        positions = client.futures_position_information(symbol=symbol)
        for pos in positions:
            if pos['symbol'] == symbol:
                return abs(float(pos['positionAmt']))
        return 0

    def calc_quantity(self, symbol, usdt_amount, leverage):
        price = float(client.futures_mark_price(symbol=symbol)['markPrice'])
        return round((usdt_amount * leverage) / price, 3)

    def log(self, message):
        self.log_text.append(message)

# ===== 전략 함수들 =====

def decide_position(symbol):
    try:
        closes = [float(k[4]) for k in get_klines(symbol, interval='5m', limit=100)]
        rsi = calculate_rsi(closes)
        macd, signal = calculate_macd(closes)
        ma = sum(closes[-20:]) / 20
        current_price = closes[-1]

        if macd > signal and rsi >= 55 and current_price > ma:
            return 'LONG'
        elif macd < signal and rsi <= 45 and current_price < ma:
            return 'SHORT'
        else:
            return 'HOLD'
    except Exception as e:
        print(f"전략 계산 오류: {e}")
        return 'HOLD'

def get_usdt_balance(client):
    balances = client.futures_account_balance()
    usdt = next((b for b in balances if b['asset'] == 'USDT'), None)
    return float(usdt['balance']) if usdt else 0.0

def get_klines(symbol, interval='5m', limit=100):
    url = f'https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}'
    response = requests.get(url)
    data = response.json()
    return data

def calculate_rsi(closes, period=14):
    gains = []
    losses = []
    for i in range(1, period + 1):
        delta = closes[-i] - closes[-i - 1]
        if delta >= 0:
            gains.append(delta)
        else:
            losses.append(abs(delta))

    average_gain = sum(gains) / period
    average_loss = sum(losses) / period

    if average_loss == 0:
        return 100

    rs = average_gain / average_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(closes, short=12, long=26, signal_period=9):
    def ema(data, period):
        k = 2 / (period + 1)
        ema_list = [sum(data[:period]) / period]
        for price in data[period:]:
            ema_list.append(price * k + ema_list[-1] * (1 - k))
        return ema_list

    if len(closes) < long + signal_period:
        return 0, 0

    macd_line = [a - b for a, b in zip(
        ema(closes, short)[-len(closes)+long:], 
        ema(closes, long)
    )]
    signal_line = ema(macd_line, signal_period)
    return macd_line[-1], signal_line[-1]

if __name__ == '__main__':
    app = QApplication(sys.argv)
    bot = TradingBot()
    bot.show()
    sys.exit(app.exec_())
