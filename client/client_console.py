import requests
import time
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import os

# ========== SETTINGS ==========
SERVER_IP = '127.0.0.1'
SERVER_PORT = 5000
SERVER_URL = f'http://{SERVER_IP}:{SERVER_PORT}/api/rate'

REQUESTS_COUNT = 100
INTERVAL_SEC = 1
TIMEOUT_SEC = 5

# ========== CREATE LOGS DIRECTORY ==========
def ensure_log_dir():
    if not os.path.exists('logs'):
        os.makedirs('logs')
        print("Created 'logs/' directory for log files")

def get_log_path(prefix='rtt_log'):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join('logs', f'{prefix}_{timestamp}.csv')

# ========== MEASURE RTT ==========
def measure_rtt():
    ensure_log_dir()
    
    print("=" * 60)
    print("RTT STATISTICS COLLECTION (100 requests)")
    print("=" * 60)
    print(f"Server: {SERVER_IP}")
    print(f"Logs saved to: logs/")
    print("=" * 60 + "\n")
    
    rtt_values = []
    timestamps = []
    rate_values = []
    errors = 0
    
    log_file = get_log_path('rtt_log')
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write('timestamp,rtt_ms,rate,request_id,status\n')
    
    for i in range(REQUESTS_COUNT):
        start_time = time.perf_counter()
        
        try:
            response = requests.get(SERVER_URL, timeout=TIMEOUT_SEC)
            end_time = time.perf_counter()
            
            rtt_ms = (end_time - start_time) * 1000
            data = response.json()
            
            rtt_values.append(rtt_ms)
            timestamps.append(i)
            rate_values.append(data['rate'])
            
            print(f"[OK] #{i+1:3d} | RTT: {rtt_ms:6.2f} ms | Rate: {data['rate']:6.2f}")
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()},{rtt_ms:.2f},{data['rate']:.2f},{data['request_id']},OK\n")
            
        except Exception as e:
            errors += 1
            rtt_values.append(None)
            timestamps.append(i)
            rate_values.append(None)
            print(f"[ERR] #{i+1:3d} | ERROR: {e}")
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()},ERROR,ERROR,ERROR,{str(e)}\n")
        
        if i < REQUESTS_COUNT - 1:
            time.sleep(INTERVAL_SEC)
    
    print("\n" + "=" * 60)
    print("STATISTICS")
    print("=" * 60)
    valid_rtt = [v for v in rtt_values if v is not None]
    
    if valid_rtt:
        print(f"Successful requests:   {len(valid_rtt)}/{REQUESTS_COUNT}")
        print(f"Packet loss:           {((REQUESTS_COUNT - len(valid_rtt))/REQUESTS_COUNT)*100:.1f}%")
        print(f"Minimum RTT:           {np.min(valid_rtt):.2f} ms")
        print(f"Maximum RTT:           {np.max(valid_rtt):.2f} ms")
        print(f"Average RTT:           {np.mean(valid_rtt):.2f} ms")
        print(f"Median RTT:            {np.median(valid_rtt):.2f} ms")
        print(f"Std Deviation:         {np.std(valid_rtt):.2f} ms")
        
        jitter = np.mean([abs(valid_rtt[i] - valid_rtt[i-1]) for i in range(1, len(valid_rtt))])
        print(f"Average Jitter:        {jitter:.2f} ms")
    else:
        print("No data for statistics")
    
    print("=" * 60)
    print(f"Log saved to: {log_file}")
    print("=" * 60)
    
    if valid_rtt:
        plot_results(rtt_values, rate_values, timestamps, log_file)
    
    return rtt_values, rate_values, timestamps

# ========== PLOT RESULTS ==========
def plot_results(rtt_values, rate_values, timestamps, log_file):
    valid_idx = [i for i, v in enumerate(rtt_values) if v is not None]
    valid_rtt = [rtt_values[i] for i in valid_idx]
    valid_rates = [rate_values[i] for i in valid_idx]
    valid_times = [timestamps[i] for i in valid_idx]
    
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    
    axes[0].plot(valid_times, valid_rtt, 'b-o', markersize=4, linewidth=1.5)
    axes[0].axhline(y=np.mean(valid_rtt), color='r', linestyle='--', 
                   label=f'Average: {np.mean(valid_rtt):.2f} ms')
    axes[0].set_title('RTT Dynamics', fontsize=14)
    axes[0].set_xlabel('Request number')
    axes[0].set_ylabel('RTT (ms)')
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()
    
    axes[1].plot(valid_times, valid_rates, 'g-o', markersize=4, linewidth=1.5)
    axes[1].set_title('USD/RUB Rate Dynamics', fontsize=14)
    axes[1].set_xlabel('Request number')
    axes[1].set_ylabel('Rate')
    axes[1].grid(True, alpha=0.3)
    
    axes[2].hist(valid_rtt, bins=20, color='skyblue', edgecolor='black', alpha=0.7)
    axes[2].axvline(x=np.mean(valid_rtt), color='r', linestyle='--', 
                   label=f'Average: {np.mean(valid_rtt):.2f} ms')
    axes[2].set_title('RTT Distribution', fontsize=14)
    axes[2].set_xlabel('RTT (ms)')
    axes[2].set_ylabel('Frequency')
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()
    
    plt.tight_layout()
    
    plot_file = log_file.replace('.csv', '.png')
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {plot_file}")
    
    plt.show()

# ========== RUN ==========
if __name__ == '__main__':
    measure_rtt()