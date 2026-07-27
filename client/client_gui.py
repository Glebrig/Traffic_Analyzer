import tkinter as tk
from tkinter import ttk, messagebox
import requests
import time
import threading
from datetime import datetime
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

# ========== SETTINGS ==========
SERVER_IP = '192.168.0.102'  #'127.0.0.1'
SERVER_PORT = 5000
SERVER_URL = f'http://{SERVER_IP}:{SERVER_PORT}/api/rate'
HISTORY_URL = f'http://{SERVER_IP}:{SERVER_PORT}/api/history'

# ========== CREATE LOGS DIRECTORY ==========
def ensure_log_dir():
    if not os.path.exists('logs'):
        os.makedirs('logs')
        print("Created 'logs/' directory for log files")

def get_log_path(prefix='rtt_test'):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join('logs', f'{prefix}_{timestamp}.csv')

# ========== MAIN WINDOW ==========
class RateMonitor:
    def __init__(self, root):
        ensure_log_dir()
        
        self.root = root
        self.root.title("Rate Monitor + RTT Analysis")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Data variables
        self.current_rate = 0
        self.current_rtt = 0
        self.current_size = 0
        self.current_req_id = 0
        self.is_running = True
        self.rtt_history = []
        self.rate_history = []
        self.time_history = []
        
        # Test flag
        self.test_running = False
        
        # Create UI
        self.create_widgets()
        
        # Start threads
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()
        
        self.plot_thread = threading.Thread(target=self.plot_update_loop, daemon=True)
        self.plot_thread.start()
    
    def create_widgets(self):
        # ===== Top panel =====
        top_frame = tk.Frame(self.root, bg='#f0f0f0', padx=10, pady=10)
        top_frame.pack(fill=tk.X)
        
        tk.Label(top_frame, text="Server:", font=('Arial', 10)).pack(side=tk.LEFT)
        self.server_label = tk.Label(top_frame, text=SERVER_IP, font=('Arial', 10, 'bold'), fg='blue')
        self.server_label.pack(side=tk.LEFT, padx=(0, 20))
        
        self.status_dot = tk.Label(top_frame, text="o", font=('Arial', 16), fg='green')
        self.status_dot.pack(side=tk.LEFT)
        self.status_label = tk.Label(top_frame, text="Connected", font=('Arial', 10), fg='green')
        self.status_label.pack(side=tk.LEFT, padx=(0, 20))
        
        self.btn_update = tk.Button(top_frame, text="Update", command=self.manual_update, 
                                   font=('Arial', 10), bg='#4CAF50', fg='white', padx=15)
        self.btn_update.pack(side=tk.RIGHT)
        
        self.btn_stats = tk.Button(top_frame, text="Run Test (100 requests)", 
                                   command=self.run_full_test, font=('Arial', 10), 
                                   bg='#2196F3', fg='white', padx=15)
        self.btn_stats.pack(side=tk.RIGHT, padx=5)
        
        # ===== Main block =====
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Rate
        rate_frame = tk.Frame(main_frame, bg='#f8f9fa', relief=tk.RIDGE, bd=2)
        rate_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(rate_frame, text="USD / RUB", font=('Arial', 14), bg='#f8f9fa').pack(pady=(10, 0))
        
        self.rate_label = tk.Label(rate_frame, text="--", font=('Arial', 48, 'bold'), 
                                   fg='#2d3748', bg='#f8f9fa')
        self.rate_label.pack(pady=(5, 10))
        
        # Metrics
        metrics_frame = tk.Frame(main_frame)
        metrics_frame.pack(fill=tk.X, pady=(0, 20))
        
        # RTT
        rtt_frame = tk.Frame(metrics_frame, bg='#e3f2fd', relief=tk.RIDGE, bd=1)
        rtt_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        tk.Label(rtt_frame, text="RTT (ms)", font=('Arial', 10), bg='#e3f2fd').pack(pady=(5, 0))
        self.rtt_label = tk.Label(rtt_frame, text="-- ms", font=('Arial', 16, 'bold'), 
                                  fg='#1565c0', bg='#e3f2fd')
        self.rtt_label.pack(pady=(0, 5))
        
        # Size
        size_frame = tk.Frame(metrics_frame, bg='#e8f5e9', relief=tk.RIDGE, bd=1)
        size_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        tk.Label(size_frame, text="Response Size", font=('Arial', 10), bg='#e8f5e9').pack(pady=(5, 0))
        self.size_label = tk.Label(size_frame, text="-- bytes", font=('Arial', 16, 'bold'), 
                                   fg='#2e7d32', bg='#e8f5e9')
        self.size_label.pack(pady=(0, 5))
        
        # ID
        id_frame = tk.Frame(metrics_frame, bg='#fff3e0', relief=tk.RIDGE, bd=1)
        id_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        tk.Label(id_frame, text="Request ID", font=('Arial', 10), bg='#fff3e0').pack(pady=(5, 0))
        self.id_label = tk.Label(id_frame, text="#--", font=('Arial', 16, 'bold'), 
                                 fg='#e65100', bg='#fff3e0')
        self.id_label.pack(pady=(0, 5))
        
        # Plot
        plot_frame = tk.Frame(main_frame)
        plot_frame.pack(fill=tk.BOTH, expand=True)
        
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(8, 6))
        self.fig.subplots_adjust(hspace=0.4)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        status_bar = tk.Frame(self.root, bg='#e0e0e0', padx=10, pady=5)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.timestamp_label = tk.Label(status_bar, text="Last update: --", 
                                        font=('Arial', 9), bg='#e0e0e0')
        self.timestamp_label.pack(side=tk.LEFT)
        
        self.counter_label = tk.Label(status_bar, text="Requests: 0", 
                                      font=('Arial', 9), bg='#e0e0e0')
        self.counter_label.pack(side=tk.RIGHT)
    
    # ========== MAIN METHODS ==========
    def fetch_data(self):
        start_time = time.perf_counter()
        
        try:
            response = requests.get(SERVER_URL, timeout=3)
            end_time = time.perf_counter()
            
            rtt_ms = (end_time - start_time) * 1000
            data = response.json()
            
            self.current_rate = data['rate']
            self.current_rtt = rtt_ms
            self.current_size = int(response.headers.get('X-Response-Size', 0))
            self.current_req_id = data['request_id']
            
            self.rtt_history.append(rtt_ms)
            self.rate_history.append(data['rate'])
            self.time_history.append(len(self.rtt_history))
            
            if len(self.rtt_history) > 50:
                self.rtt_history.pop(0)
                self.rate_history.pop(0)
                self.time_history.pop(0)
            
            self.root.after(0, self.update_ui, True, data['timestamp'])
            return True
            
        except Exception as e:
            print(f"Error: {e}")
            self.root.after(0, self.update_ui, False, None)
            return False
    
    def update_ui(self, success, timestamp):
        if success:
            self.rate_label.config(text=f"{self.current_rate:.2f}")
            
            rtt_text = f"{self.current_rtt:.1f} ms"
            if self.current_rtt < 10:
                self.rtt_label.config(text=rtt_text, fg='#2e7d32')
            elif self.current_rtt < 50:
                self.rtt_label.config(text=rtt_text, fg='#ed8936')
            else:
                self.rtt_label.config(text=rtt_text, fg='#fc8181')
            
            self.size_label.config(text=f"{self.current_size} bytes")
            self.id_label.config(text=f"#{self.current_req_id}")
            
            self.status_dot.config(fg='green')
            self.status_label.config(text="Connected", fg='green')
            
            if timestamp:
                self.timestamp_label.config(text=f"Last update: {timestamp}")
            
            self.counter_label.config(text=f"Requests: {self.current_req_id}")
            
        else:
            self.status_dot.config(fg='red')
            self.status_label.config(text="Connection error", fg='red')
            self.rate_label.config(text="ERR")
    
    def manual_update(self):
        self.btn_update.config(state=tk.DISABLED, text="Loading...")
        threading.Thread(target=self._manual_update_thread, daemon=True).start()
    
    def _manual_update_thread(self):
        self.fetch_data()
        self.root.after(0, lambda: self.btn_update.config(state=tk.NORMAL, text="Update"))
    
    def update_loop(self):
        while self.is_running:
            self.fetch_data()
            time.sleep(2)
    
    def plot_update_loop(self):
        while self.is_running:
            self.update_plot()
            time.sleep(3)
    
    def update_plot(self):
        if len(self.rtt_history) < 2:
            return
        
        self.ax1.clear()
        self.ax2.clear()
        
        self.ax1.plot(self.time_history, self.rtt_history, 'b-o', markersize=3, linewidth=1.5)
        self.ax1.axhline(y=np.mean(self.rtt_history), color='r', linestyle='--', 
                        label=f'Average: {np.mean(self.rtt_history):.1f} ms')
        self.ax1.set_title('RTT Dynamics', fontsize=10)
        self.ax1.set_xlabel('Request')
        self.ax1.set_ylabel('RTT (ms)')
        self.ax1.grid(True, alpha=0.3)
        self.ax1.legend(fontsize=8)
        
        self.ax2.plot(self.time_history, self.rate_history, 'g-o', markersize=3, linewidth=1.5)
        self.ax2.set_title('USD/RUB Rate', fontsize=10)
        self.ax2.set_xlabel('Request')
        self.ax2.set_ylabel('Rate')
        self.ax2.grid(True, alpha=0.3)
        
        self.fig.tight_layout()
        self.canvas.draw()
    
    # ========== TEST (FIXED VERSION) ==========
    def run_full_test(self):
        if self.test_running:
            messagebox.showwarning("Test already running", "Please wait for current test to finish")
            return
        
        self.test_running = True
        self.btn_stats.config(state=tk.DISABLED, text="Test running...")
        
        threading.Thread(target=self._run_test_thread, daemon=True).start()
    
    def _run_test_thread(self):
        rtt_values = []
        timestamps = []
        rate_values = []
        errors = 0
        
        log_file = get_log_path('rtt_test')
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write('timestamp,rtt_ms,rate,request_id\n')
        
        for i in range(100):
            start_time = time.perf_counter()
            
            try:
                response = requests.get(SERVER_URL, timeout=3)
                end_time = time.perf_counter()
                
                rtt_ms = (end_time - start_time) * 1000
                data = response.json()
                
                rtt_values.append(rtt_ms)
                timestamps.append(i)
                rate_values.append(data['rate'])
                
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"{datetime.now().isoformat()},{rtt_ms:.2f},{data['rate']:.2f},{data['request_id']}\n")
                
                print(f"[OK] #{i+1:3d} | RTT: {rtt_ms:.2f} ms | Rate: {data['rate']:.2f}")
                
            except Exception as e:
                errors += 1
                rtt_values.append(None)
                timestamps.append(i)
                rate_values.append(None)
                print(f"[ERR] #{i+1:3d} | Error: {e}")
            
            time.sleep(1)
        
        self.test_results = {
            'rtt_values': rtt_values,
            'timestamps': timestamps,
            'log_file': log_file,
            'errors': errors
        }
        
        self.root.after(0, self._test_finished)
    
    def _test_finished(self):
        self.btn_stats.config(state=tk.NORMAL, text="Run Test (100 requests)")
        self.test_running = False
        
        rtt_values = self.test_results['rtt_values']
        timestamps = self.test_results['timestamps']
        log_file = self.test_results['log_file']
        errors = self.test_results['errors']
        
        self._plot_test_results(rtt_values, timestamps, log_file, errors)
        
        success_count = 100 - errors
        messagebox.showinfo(
            "Test Finished",
            f"Successful requests: {success_count}\n"
            f"Errors: {errors}\n"
            f"Log saved to: {log_file}\n"
            f"Plot saved to: {log_file.replace('.csv', '.png')}"
        )
    
    def _plot_test_results(self, rtt_values, timestamps, log_file, errors):
        valid_rtt = [v for v in rtt_values if v is not None]
        valid_times = [timestamps[i] for i in range(len(timestamps)) if rtt_values[i] is not None]
        
        if len(valid_rtt) == 0:
            return
        
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        
        axes[0].plot(valid_times, valid_rtt, 'b-o', markersize=4, linewidth=1.5)
        axes[0].axhline(y=np.mean(valid_rtt), color='r', linestyle='--', 
                       label=f'Average: {np.mean(valid_rtt):.2f} ms')
        axes[0].set_title('RTT for 100 requests', fontsize=14)
        axes[0].set_xlabel('Request number')
        axes[0].set_ylabel('RTT (ms)')
        axes[0].grid(True, alpha=0.3)
        axes[0].legend()
        
        axes[1].hist(valid_rtt, bins=20, color='skyblue', edgecolor='black', alpha=0.7)
        axes[1].axvline(x=np.mean(valid_rtt), color='r', linestyle='--', 
                       label=f'Average: {np.mean(valid_rtt):.2f} ms')
        axes[1].set_title('RTT Distribution', fontsize=14)
        axes[1].set_xlabel('RTT (ms)')
        axes[1].set_ylabel('Frequency')
        axes[1].grid(True, alpha=0.3)
        axes[1].legend()
        
        plt.figtext(0.02, 0.02, f'Errors: {errors} out of 100', fontsize=10, color='red')
        
        plt.tight_layout()
        
        plot_file = log_file.replace('.csv', '.png')
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved to: {plot_file}")
        
        plt.show()
    
    def on_closing(self):
        self.is_running = False
        self.root.destroy()

# ========== RUN ==========
if __name__ == '__main__':
    print("=" * 60)
    print("STARTING CLIENT WITH GUI")
    print("=" * 60)
    print(f"Server: {SERVER_URL}")
    print(f"Logs will be saved to: logs/")
    print("=" * 60)
    
    try:
        response = requests.get(SERVER_URL, timeout=2)
        print("Server available!")
    except:
        print("WARNING: Server unavailable!")
        print(f"   Check IP: {SERVER_IP}")
        print("=" * 60)
    
    root = tk.Tk()
    app = RateMonitor(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()