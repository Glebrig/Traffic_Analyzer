import time
import requests
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ===================================================================
# НАСТРОЙКИ
# ===================================================================
COIN_ID = "btc-bitcoin"      # ID монеты: btc-bitcoin, eth-ethereum, sol-solana
COIN_SYMBOL = "BTC"          # Символ для отображения
COIN_NAME = "Bitcoin"        # Название

START_TIME = time.time()
request_counter = 0

# Кеширование (данные обновляются каждые 30 секунд)
CACHE_DURATION = 30
last_cache = None
cached_data = None

# ===================================================================
# ПОЛУЧЕНИЕ ЦЕНЫ ИЗ COINPAPRIKA
# ===================================================================
def fetch_crypto_price():
    """Получение текущей цены криптовалюты через CoinPaprika API"""
    global last_cache, cached_data

    # Если кеш свежий — используем его
    if cached_data and (time.time() - last_cache) < CACHE_DURATION:
        return cached_data

    try:
        url = f"https://api.coinpaprika.com/v1/tickers/{COIN_ID}"
        response = requests.get(url, timeout=5)

        if response.status_code != 200:
            print(f"[CRYPTO] Ошибка: HTTP {response.status_code}")
            return cached_data if cached_data else {
                'price': 50000.0,
                'change_24h': 0.0,
                'change_1h': 0.0,
                'volume': 0,
                'market_cap': 0
            }

        data = response.json()

        quotes = data.get('quotes', {}).get('USD', {})
        price = quotes.get('price', 0)
        change_24h = quotes.get('percent_change_24h', 0)
        change_1h = quotes.get('percent_change_1h', 0)
        volume = quotes.get('volume_24h', 0)
        market_cap = quotes.get('market_cap', 0)

        result = {
            'price': round(price, 2),
            'change_24h': round(change_24h, 2),
            'change_1h': round(change_1h, 2),
            'volume': int(volume),
            'market_cap': int(market_cap),
            'last_updated': data.get('last_updated', '')
        }

        last_cache = time.time()
        cached_data = result

        print(f"[CRYPTO] {COIN_SYMBOL}: ${price:,.2f} (24h: {change_24h:+.2f}%)")
        return result

    except Exception as e:
        print(f"[CRYPTO] Ошибка: {e}")
        return cached_data if cached_data else {
            'price': 50000.0,
            'change_24h': 0.0,
            'change_1h': 0.0,
            'volume': 0,
            'market_cap': 0
        }

# ===================================================================
# API: КРИПТОВАЛЮТА
# ===================================================================
@app.route('/api/rate', methods=['GET'])
def get_crypto():
    global request_counter
    request_counter += 1

    data = fetch_crypto_price()

    response_data = {
        'request_id': request_counter,
        'server_time': int(time.time()),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
        'asset': COIN_NAME,
        'symbol': COIN_SYMBOL,
        'price_usd': data['price'],
        'change_24h': data['change_24h'],
        'change_1h': data['change_1h'],
        'volume_24h': data['volume'],
        'market_cap': data['market_cap']
    }

    response = jsonify(response_data)
    response.headers['X-Server-Time'] = str(time.time())
    response.headers['X-Request-ID'] = str(request_counter)
    response.headers['X-Response-Size'] = str(len(str(response_data)))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Access-Control-Expose-Headers'] = 'X-Server-Time, X-Request-ID, X-Response-Size'

    return response

# ===================================================================
# API: СБРОС СЧЕТЧИКА
# ===================================================================
@app.route('/api/reset', methods=['POST'])
def reset_counter():
    global request_counter
    request_counter = 0
    print("[RESET] Счётчик сброшен")
    return jsonify({'status': 'reset', 'new_request_id': 0})

# ===================================================================
# API: СТАТУС
# ===================================================================
@app.route('/api/status', methods=['GET'])
def status():
    uptime_seconds = int(time.time() - START_TIME)
    hours = uptime_seconds // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60

    data = fetch_crypto_price()

    return jsonify({
        'status': 'online',
        'uptime': f'{hours:02d}:{minutes:02d}:{seconds:02d}',
        'requests_handled': request_counter,
        'current_price': data['price'],
        'change_24h': data['change_24h']
    })

# ===================================================================
# ЗАПУСК
# ===================================================================
if __name__ == '__main__':
    print("=" * 60)
    print("СЕРВЕР КРИПТОВАЛЮТ (CoinPaprika API)")
    print("=" * 60)
    print(f"Монета: {COIN_NAME} ({COIN_SYMBOL})")
    print("=" * 60)

    # Проверяем API при старте
    try:
        data = fetch_crypto_price()
        print(f"[OK] {COIN_SYMBOL}: ${data['price']:,.2f} (24h: {data['change_24h']:+.2f}%)")
    except Exception as e:
        print(f"[WARN] Ошибка проверки API: {e}")

    print("=" * 60)
    print("API курса:  http://0.0.0.0:5000/api/rate")
    print("Сброс:      POST http://0.0.0.0:5000/api/reset")
    print("Статус:     http://0.0.0.0:5000/api/status")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)