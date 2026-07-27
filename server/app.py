import time
import random
import json
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ========== ГЛОБАЛЬНЫЕ ДАННЫЕ ==========
START_TIME = time.time()
current_rate = 75.0
request_counter = 0
rate_history = []

# ========== API: КУРС ВАЛЮТ ==========
@app.route('/api/rate', methods=['GET'])
def get_rate():
    global current_rate, request_counter, rate_history
    
    request_counter += 1
    current_rate += random.uniform(-0.3, 0.3)
    current_rate = max(60, min(90, current_rate))
    
    response_data = {
        'currency': 'USD/RUB',
        'rate': round(current_rate, 2),
        'request_id': request_counter,
        'server_time': int(time.time()),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    }
    
    rate_history.append(response_data.copy())
    if len(rate_history) > 50:
        rate_history.pop(0)
    
    response = jsonify(response_data)
    response.headers['X-Server-Time'] = str(time.time())
    response.headers['X-Request-ID'] = str(request_counter)
    response.headers['X-Response-Size'] = str(len(json.dumps(response_data)))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Access-Control-Expose-Headers'] = 'X-Server-Time, X-Request-ID, X-Response-Size'
    
    return response

# ========== API: СТАТУС СЕРВЕРА ==========
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
        'last_rate': round(current_rate, 2)
    })

# ========== API: ИСТОРИЯ ==========
@app.route('/api/history', methods=['GET'])
def get_history():
    return jsonify({
        'history': rate_history
    })

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    print("=" * 60)
    print("SERVER STARTED (API only)")
    print("=" * 60)
    print(f"Rate API:    http://0.0.0.0:5000/api/rate")
    print(f"Status API:  http://0.0.0.0:5000/api/status")
    print(f"History API: http://0.0.0.0:5000/api/history")
    print("=" * 60)
    print("Client must connect to this computer's IP")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)