import time
import requests
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ===================================================================
START_TIME = time.time()
request_counter = 0
CBR_API_URL = 'https://www.cbr-xml-daily.ru/daily_json.js'
CACHE_DURATION = 60
last_cache = None
cached_rate = None
cached_eur = None

# ===================================================================
def fetch_real_rate():
    global last_cache, cached_rate, cached_eur
    if cached_rate and (time.time() - last_cache) < CACHE_DURATION:
        return cached_rate, cached_eur
    try:
        response = requests.get(CBR_API_URL, timeout=5)
        data = response.json()
        cached_rate = round(data['Valute']['USD']['Value'], 2)
        cached_eur = round(data['Valute']['EUR']['Value'], 2)
        last_cache = time.time()
        print(f"[API] USD={cached_rate}, EUR={cached_eur}")
        return cached_rate, cached_eur
    except Exception as e:
        print(f"[API] Ошибка: {e}, используется кеш")
        if cached_rate:
            return cached_rate, cached_eur
        return 75.0, 85.0

# ===================================================================
@app.route('/api/rate', methods=['GET'])
def get_rate():
    global request_counter
    request_counter += 1
    usd_rate, eur_rate = fetch_real_rate()
    response_data = {
        'currency': 'USD/RUB',
        'rate': usd_rate,
        'request_id': request_counter,
        'server_time': int(time.time()),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
        'eur_rate': eur_rate,
        'source': 'Центробанк РФ'
    }
    response = jsonify(response_data)
    response.headers['X-Server-Time'] = str(time.time())
    response.headers['X-Request-ID'] = str(request_counter)
    response.headers['X-Response-Size'] = str(len(str(response_data)))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Access-Control-Expose-Headers'] = 'X-Server-Time, X-Request-ID, X-Response-Size'
    return response

# ===================================================================
@app.route('/api/reset', methods=['POST'])
def reset_counter():
    global request_counter
    request_counter = 0
    print("[RESET] Счётчик сброшен")
    return jsonify({'status': 'reset', 'new_request_id': 0})

# ===================================================================
@app.route('/api/status', methods=['GET'])
def status():
    uptime_seconds = int(time.time() - START_TIME)
    hours = uptime_seconds // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    return jsonify({
        'status': 'online',
        'uptime': f'{hours:02d}:{minutes:02d}:{seconds:02d}',
        'requests_handled': request_counter,
        'last_rate': fetch_real_rate()[0],
        'source': 'Центробанк РФ'
    })

# ===================================================================
@app.route('/api/history', methods=['GET'])
def get_history():
    usd_rate, eur_rate = fetch_real_rate()
    return jsonify({
        'history': [{'rate': usd_rate, 'timestamp': datetime.now().isoformat()}]
    })

# ===================================================================
if __name__ == '__main__':
    print("=" * 60)
    print("СЕРВЕР С ДАННЫМИ (Центробанк РФ)")
    print("=" * 60)
    print("API курса:    http://0.0.0.0:5000/api/rate")
    print("Сброс:        POST http://0.0.0.0:5000/api/reset")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)