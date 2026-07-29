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

# ===================================================================
# НАСТРОЙКИ ПО УМОЛЧАНИЮ
# ===================================================================
DEFAULT_SERVER_IP = '127.0.0.1'
DEFAULT_SERVER_PORT = 5000

# ===================================================================
# СОЗДАНИЕ ПАПКИ ДЛЯ ЛОГОВ
# ===================================================================
def ensure_log_dir():
    if not os.path.exists('logs'):
        os.makedirs('logs')
        print("Создана папка 'logs/' для хранения логов")

def get_log_path(prefix='rtt_test'):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join('logs', f'{prefix}_{timestamp}.csv')

# ===================================================================
# ГЛАВНЫЙ КЛАСС
# ===================================================================
class RateMonitor:
    def __init__(self, root):
        ensure_log_dir()
        
        self.root = root
        self.root.title("Монитор курса валют + анализ RTT")
        self.root.geometry("800x720")
        self.root.resizable(True, True)
        
        # Переменные для данных
        self.current_rate = 0
        self.current_rtt = 0
        self.current_size = 0
        self.current_req_id = 0
        self.is_running = True
        self.rtt_history = []
        self.rate_history = []
        self.time_history = []
        
        # Флаг для теста
        self.test_running = False
        
        # URL сервера
        self.server_url = None
        
        # Флаг для предотвращения одновременного обновления графика
        self.plot_updating = False
        
        # Создаем интерфейс
        self.create_widgets()
        
        # Автоматическое подключение к серверу по умолчанию
        self.root.after(500, lambda: self.connect_to_server(DEFAULT_SERVER_IP, DEFAULT_SERVER_PORT))
    
    # ===================================================================
    # СОЗДАНИЕ ИНТЕРФЕЙСА
    # ===================================================================
    def create_widgets(self):
        # ===== ВЕРХНЯЯ ПАНЕЛЬ (подключение) =====
        connection_frame = tk.Frame(self.root, bg='#f0f0f0', padx=10, pady=8)
        connection_frame.pack(fill=tk.X)
        
        tk.Label(connection_frame, text="Адрес сервера:", font=('Arial', 10), 
                 bg='#f0f0f0').pack(side=tk.LEFT)
        
        self.ip_entry = tk.Entry(connection_frame, width=15, font=('Arial', 10))
        self.ip_entry.insert(0, DEFAULT_SERVER_IP)
        self.ip_entry.pack(side=tk.LEFT, padx=(5, 5))
        
        tk.Label(connection_frame, text="Порт:", font=('Arial', 10), 
                 bg='#f0f0f0').pack(side=tk.LEFT)
        
        self.port_entry = tk.Entry(connection_frame, width=6, font=('Arial', 10))
        self.port_entry.insert(0, str(DEFAULT_SERVER_PORT))
        self.port_entry.pack(side=tk.LEFT, padx=(5, 10))
        
        self.btn_connect = tk.Button(connection_frame, text="Подключиться", 
                                     command=self.on_connect_click,
                                     font=('Arial', 10), bg='#4CAF50', fg='white', padx=15)
        self.btn_connect.pack(side=tk.LEFT)
        
        # Статус подключения
        self.status_dot = tk.Label(connection_frame, text="●", font=('Arial', 16), 
                                   fg='gray', bg='#f0f0f0')
        self.status_dot.pack(side=tk.LEFT, padx=(15, 5))
        self.status_label = tk.Label(connection_frame, text="Не подключено", 
                                     font=('Arial', 10), fg='gray', bg='#f0f0f0')
        self.status_label.pack(side=tk.LEFT)
        
        # ===== ПАНЕЛЬ УПРАВЛЕНИЯ =====
        control_frame = tk.Frame(self.root, bg='#f0f0f0', padx=10, pady=8)
        control_frame.pack(fill=tk.X)
        
        self.btn_update = tk.Button(control_frame, text="Обновить вручную", 
                                    command=self.manual_update,
                                    font=('Arial', 10), bg='#4CAF50', fg='white', padx=15)
        self.btn_update.pack(side=tk.LEFT)
        self.btn_update.config(state=tk.DISABLED)
        
        self.btn_stats = tk.Button(control_frame, text="Запустить тест (100 запросов)", 
                                   command=self.run_full_test, font=('Arial', 10), 
                                   bg='#2196F3', fg='white', padx=15)
        self.btn_stats.pack(side=tk.LEFT, padx=10)
        self.btn_stats.config(state=tk.DISABLED)
        
        # Кнопка сброса счетчика (светло-желтый фон)
        self.btn_reset = tk.Button(control_frame, text="Сбросить счетчик запросов", 
                                   command=self.reset_counter,
                                   font=('Arial', 10), bg='#FFF9C4', fg='#333333', padx=15)
        self.btn_reset.pack(side=tk.LEFT)
        self.btn_reset.config(state=tk.DISABLED)
        
        # ===== ОСНОВНОЙ БЛОК =====
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Курс
        rate_frame = tk.Frame(main_frame, bg='#f8f9fa', relief=tk.RIDGE, bd=2)
        rate_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(rate_frame, text="USD / RUB", font=('Arial', 14), bg='#f8f9fa').pack(pady=(10, 0))
        
        self.rate_label = tk.Label(rate_frame, text="--", font=('Arial', 48, 'bold'), 
                                   fg='#2d3748', bg='#f8f9fa')
        self.rate_label.pack(pady=(5, 10))
        
        # Метрики
        metrics_frame = tk.Frame(main_frame)
        metrics_frame.pack(fill=tk.X, pady=(0, 20))
        
        # RTT
        rtt_frame = tk.Frame(metrics_frame, bg='#e3f2fd', relief=tk.RIDGE, bd=1)
        rtt_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        tk.Label(rtt_frame, text="Задержка (RTT)", font=('Arial', 10), bg='#e3f2fd').pack(pady=(5, 0))
        self.rtt_label = tk.Label(rtt_frame, text="-- мс", font=('Arial', 16, 'bold'), 
                                  fg='#1565c0', bg='#e3f2fd')
        self.rtt_label.pack(pady=(0, 5))
        
        # Размер
        size_frame = tk.Frame(metrics_frame, bg='#e8f5e9', relief=tk.RIDGE, bd=1)
        size_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        tk.Label(size_frame, text="Размер ответа", font=('Arial', 10), bg='#e8f5e9').pack(pady=(5, 0))
        self.size_label = tk.Label(size_frame, text="-- байт", font=('Arial', 16, 'bold'), 
                                   fg='#2e7d32', bg='#e8f5e9')
        self.size_label.pack(pady=(0, 5))
        
        # ID
        id_frame = tk.Frame(metrics_frame, bg='#fff3e0', relief=tk.RIDGE, bd=1)
        id_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        tk.Label(id_frame, text="ID запроса", font=('Arial', 10), bg='#fff3e0').pack(pady=(5, 0))
        self.id_label = tk.Label(id_frame, text="#--", font=('Arial', 16, 'bold'), 
                                 fg='#e65100', bg='#fff3e0')
        self.id_label.pack(pady=(0, 5))
        
        # График
        plot_frame = tk.Frame(main_frame)
        plot_frame.pack(fill=tk.BOTH, expand=True)
        
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(8, 6))
        self.fig.subplots_adjust(hspace=0.4)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Начальное состояние графиков
        self.show_placeholder()
        
        # Статус-бар
        status_bar = tk.Frame(self.root, bg='#e0e0e0', padx=10, pady=5)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.timestamp_label = tk.Label(status_bar, text="Последнее обновление: --", 
                                        font=('Arial', 9), bg='#e0e0e0')
        self.timestamp_label.pack(side=tk.LEFT)
        
        self.counter_label = tk.Label(status_bar, text="Запросов: 0", 
                                      font=('Arial', 9), bg='#e0e0e0')
        self.counter_label.pack(side=tk.RIGHT)
    
    # ===================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ДЛЯ ГРАФИКОВ
    # ===================================================================
    def show_placeholder(self):
        """Показывает заглушку на графиках"""
        self.ax1.clear()
        self.ax2.clear()
        self.ax1.text(0.5, 0.5, "Ожидание подключения...", 
                     horizontalalignment='center', verticalalignment='center', 
                     transform=self.ax1.transAxes, fontsize=14, color='gray')
        self.ax2.text(0.5, 0.5, "Ожидание подключения...", 
                     horizontalalignment='center', verticalalignment='center', 
                     transform=self.ax2.transAxes, fontsize=14, color='gray')
        # Используем draw вместо tight_layout, чтобы избежать ошибок
        self.canvas.draw()
    
    def show_reset_placeholder(self):
        """Показывает заглушку после сброса"""
        self.ax1.clear()
        self.ax2.clear()
        self.ax1.text(0.5, 0.5, "Счетчик сброшен. Ожидание данных...",
                     horizontalalignment='center', verticalalignment='center',
                     transform=self.ax1.transAxes, fontsize=14, color='gray')
        self.ax2.text(0.5, 0.5, "Счетчик сброшен. Ожидание данных...",
                     horizontalalignment='center', verticalalignment='center',
                     transform=self.ax2.transAxes, fontsize=14, color='gray')
        self.canvas.draw()
    
    # ===================================================================
    # ПОДКЛЮЧЕНИЕ К СЕРВЕРУ
    # ===================================================================
    def connect_to_server(self, ip, port):
        self.btn_connect.config(state=tk.DISABLED, text="Проверка...")
        self.status_dot.config(fg='orange', bg='#f0f0f0')
        self.status_label.config(text="Проверка подключения...", fg='orange')
        
        threading.Thread(target=self._check_connection, args=(ip, port), daemon=True).start()
    
    def _check_connection(self, ip, port):
        url = f'http://{ip}:{port}/api/rate'
        
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                self.server_url = url
                self.root.after(0, self._connection_success, ip, port)
                return
        except:
            pass
        
        self.root.after(0, self._connection_failed)
    
    def _connection_success(self, ip, port):
        self.status_dot.config(fg='green', bg='#f0f0f0')
        self.status_label.config(text=f"Подключено к {ip}:{port}", fg='green')
        self.btn_connect.config(state=tk.NORMAL, text="Подключиться")
        
        self.btn_stats.config(state=tk.NORMAL)
        self.btn_update.config(state=tk.NORMAL)
        self.btn_reset.config(state=tk.NORMAL)
        
        self.start_monitoring()
        print(f"Подключено к серверу: {self.server_url}")
    
    def _connection_failed(self):
        self.status_dot.config(fg='red', bg='#f0f0f0')
        self.status_label.config(text="Ошибка подключения", fg='red')
        self.btn_connect.config(state=tk.NORMAL, text="Подключиться")
        self.btn_stats.config(state=tk.DISABLED)
        self.btn_reset.config(state=tk.DISABLED)
        
        messagebox.showerror("Ошибка подключения", 
                            f"Не удалось подключиться к серверу {self.ip_entry.get()}:{self.port_entry.get()}\n"
                            "Проверьте, что сервер запущен и IP-адрес введен верно.")
    
    def on_connect_click(self):
        ip = self.ip_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Ошибка", "Порт должен быть числом")
            return
        
        if not ip:
            messagebox.showerror("Ошибка", "Введите IP-адрес сервера")
            return
        
        self.connect_to_server(ip, port)
    
    # ===================================================================
    # СБРОС СЧЕТЧИКА + ОЧИСТКА ГРАФИКОВ
    # ===================================================================
    def reset_counter(self):
        if not self.server_url:
            messagebox.showwarning("Нет подключения", "Сначала подключитесь к серверу")
            return
        
        if not messagebox.askyesno("Подтверждение", "Сбросить счетчик запросов и очистить графики?"):
            return
        
        self.btn_reset.config(state=tk.DISABLED, text="Сброс...")
        threading.Thread(target=self._reset_counter_thread, daemon=True).start()
    
    def _reset_counter_thread(self):
        try:
            reset_url = self.server_url.replace('/api/rate', '/api/reset')
            response = requests.post(reset_url, timeout=3)
            if response.status_code == 200:
                self.root.after(0, self._reset_counter_success)
            else:
                self.root.after(0, self._reset_counter_failed)
        except Exception as e:
            print(f"Ошибка сброса: {e}")
            self.root.after(0, self._reset_counter_failed)
    
    def _reset_counter_success(self):
        """Сброс счетчика на сервере и очистка графиков"""
        # Очищаем историю данных
        self.rtt_history.clear()
        self.rate_history.clear()
        self.time_history.clear()
        
        # Сбрасываем отображение ID и счетчика
        self.id_label.config(text="#0")
        self.counter_label.config(text="Запросов: 0")
        
        # Очищаем графики и показываем сообщение
        self.show_reset_placeholder()
        
        self.btn_reset.config(state=tk.NORMAL, text="Сбросить счетчик запросов")
        messagebox.showinfo("Сброс выполнен", "Счетчик сброшен, графики очищены.\nСледующий запрос получит ID = 1.")
        
        # Принудительно обновляем данные (чтобы получить новый ID = 1)
        self.fetch_data()
    
    def _reset_counter_failed(self):
        self.btn_reset.config(state=tk.NORMAL, text="Сбросить счетчик запросов")
        messagebox.showerror("Ошибка", "Не удалось сбросить счетчик на сервере")
    
    # ===================================================================
    # МОНИТОРИНГ
    # ===================================================================
    def start_monitoring(self):
        self.is_running = False
        time.sleep(0.1)
        self.is_running = True
        
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()
        
        self.plot_thread = threading.Thread(target=self.plot_update_loop, daemon=True)
        self.plot_thread.start()
    
    def fetch_data(self):
        if not self.server_url:
            return False
        
        start_time = time.perf_counter()
        
        try:
            response = requests.get(self.server_url, timeout=3)
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
            print(f"Ошибка: {e}")
            self.root.after(0, self.update_ui, False, None)
            return False
    
    def update_ui(self, success, timestamp):
        if success:
            self.rate_label.config(text=f"{self.current_rate:.2f}")
            
            rtt_text = f"{self.current_rtt:.1f} мс"
            if self.current_rtt < 10:
                self.rtt_label.config(text=rtt_text, fg='#2e7d32')
            elif self.current_rtt < 50:
                self.rtt_label.config(text=rtt_text, fg='#ed8936')
            else:
                self.rtt_label.config(text=rtt_text, fg='#fc8181')
            
            self.size_label.config(text=f"{self.current_size} байт")
            self.id_label.config(text=f"#{self.current_req_id}")
            
            self.status_dot.config(fg='green', bg='#f0f0f0')
            self.status_label.config(text="Подключено", fg='green')
            
            if timestamp:
                self.timestamp_label.config(text=f"Последнее обновление: {timestamp}")
            
            self.counter_label.config(text=f"Запросов: {self.current_req_id}")
            
        else:
            self.status_dot.config(fg='red', bg='#f0f0f0')
            self.status_label.config(text="Ошибка", fg='red')
            self.rate_label.config(text="ОШИБКА")
    
    def manual_update(self):
        if not self.server_url:
            messagebox.showwarning("Нет подключения", "Сначала подключитесь к серверу")
            return
        
        self.btn_update.config(state=tk.DISABLED, text="Загрузка...")
        threading.Thread(target=self._manual_update_thread, daemon=True).start()
    
    def _manual_update_thread(self):
        self.fetch_data()
        self.root.after(0, lambda: self.btn_update.config(state=tk.NORMAL, text="Обновить вручную"))
    
    def update_loop(self):
        while self.is_running:
            self.fetch_data()
            time.sleep(2)
    
    def plot_update_loop(self):
        while self.is_running:
            try:
                self.update_plot()
            except Exception as e:
                # Подавляем ошибки matplotlib, чтобы не крашить поток
                print(f"Ошибка обновления графика: {e}")
            time.sleep(3)
    
    def update_plot(self):
        # Защита от одновременного обновления
        if self.plot_updating:
            return
        self.plot_updating = True
        
        try:
            if len(self.rtt_history) < 2:
                # Если данных мало, показываем заглушку
                self.show_placeholder()
                self.plot_updating = False
                return
            
            # Проверяем, что оси существуют
            if self.ax1 is None or self.ax2 is None:
                self.plot_updating = False
                return
            
            self.ax1.clear()
            self.ax2.clear()
            
            # График 1: RTT (без подписи оси X)
            self.ax1.plot(self.time_history, self.rtt_history, 'b-o', markersize=3, linewidth=1.5)
            self.ax1.axhline(y=np.mean(self.rtt_history), color='r', linestyle='--', 
                            label=f'Среднее: {np.mean(self.rtt_history):.1f} мс')
            self.ax1.set_title('Динамика задержки (RTT)', fontsize=10)
            self.ax1.set_ylabel('Задержка (мс)')
            self.ax1.grid(True, alpha=0.3)
            self.ax1.legend(fontsize=8)
            
            # График 2: Курс валют (без подписи оси X)
            self.ax2.plot(self.time_history, self.rate_history, 'g-o', markersize=3, linewidth=1.5)
            self.ax2.set_title('Курс USD/RUB', fontsize=10)
            self.ax2.set_ylabel('Курс')
            self.ax2.grid(True, alpha=0.3)
            
            # Используем try/except для tight_layout
            try:
                self.fig.tight_layout()
            except Exception as e:
                # Если tight_layout не работает, просто рисуем без него
                print(f"tight_layout warning: {e}")
                pass
            
            self.canvas.draw()
            
        except Exception as e:
            print(f"Ошибка в update_plot: {e}")
            # Восстанавливаем оси при ошибке
            try:
                self.show_placeholder()
            except:
                pass
        
        finally:
            self.plot_updating = False
    
    # ===================================================================
    # ТЕСТ НА 100 ЗАПРОСОВ
    # ===================================================================
    def run_full_test(self):
        if not self.server_url:
            messagebox.showwarning("Нет подключения", "Сначала подключитесь к серверу")
            return
        
        if self.test_running:
            messagebox.showwarning("Тест уже запущен", "Дождитесь завершения текущего теста")
            return
        
        self.test_running = True
        self.btn_stats.config(state=tk.DISABLED, text="Тест выполняется...")
        
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
                response = requests.get(self.server_url, timeout=3)
                end_time = time.perf_counter()
                
                rtt_ms = (end_time - start_time) * 1000
                data = response.json()
                
                rtt_values.append(rtt_ms)
                timestamps.append(i)
                rate_values.append(data['rate'])
                
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"{datetime.now().isoformat()},{rtt_ms:.2f},{data['rate']:.2f},{data['request_id']}\n")
                
                print(f"[OK] #{i+1:3d} | RTT: {rtt_ms:.2f} мс | Курс: {data['rate']:.2f}")
                
            except Exception as e:
                errors += 1
                rtt_values.append(None)
                timestamps.append(i)
                rate_values.append(None)
                print(f"[ERR] #{i+1:3d} | Ошибка: {e}")
            
            time.sleep(1)
        
        self.test_results = {
            'rtt_values': rtt_values,
            'timestamps': timestamps,
            'log_file': log_file,
            'errors': errors
        }
        
        self.root.after(0, self._test_finished)
    
    def _test_finished(self):
        self.btn_stats.config(state=tk.NORMAL, text="Запустить тест (100 запросов)")
        self.test_running = False
        
        rtt_values = self.test_results['rtt_values']
        timestamps = self.test_results['timestamps']
        log_file = self.test_results['log_file']
        errors = self.test_results['errors']
        
        self._plot_test_results(rtt_values, timestamps, log_file, errors)
        
        success_count = 100 - errors
        messagebox.showinfo(
            "Тест завершен",
            f"Успешных запросов: {success_count}\n"
            f"Ошибок: {errors}\n"
            f"Лог сохранен в: {log_file}\n"
            f"График сохранен в: {log_file.replace('.csv', '.png')}"
        )
    
    def _plot_test_results(self, rtt_values, timestamps, log_file, errors):
        valid_rtt = [v for v in rtt_values if v is not None]
        valid_times = [timestamps[i] for i in range(len(timestamps)) if rtt_values[i] is not None]
        
        if len(valid_rtt) == 0:
            return
        
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        
        # График RTT (без подписи оси X)
        axes[0].plot(valid_times, valid_rtt, 'b-o', markersize=4, linewidth=1.5)
        axes[0].axhline(y=np.mean(valid_rtt), color='r', linestyle='--', 
                       label=f'Среднее: {np.mean(valid_rtt):.2f} мс')
        axes[0].set_title('Задержка (RTT) при 100 запросах', fontsize=14)
        axes[0].set_ylabel('Задержка (мс)')
        axes[0].grid(True, alpha=0.3)
        axes[0].legend()
        
        # Гистограмма (без подписи оси X)
        axes[1].hist(valid_rtt, bins=20, color='skyblue', edgecolor='black', alpha=0.7)
        axes[1].axvline(x=np.mean(valid_rtt), color='r', linestyle='--', 
                       label=f'Среднее: {np.mean(valid_rtt):.2f} мс')
        axes[1].set_title('Распределение задержек', fontsize=14)
        axes[1].set_ylabel('Частота')
        axes[1].grid(True, alpha=0.3)
        axes[1].legend()
        
        plt.tight_layout()
        
        plot_file = log_file.replace('.csv', '.png')
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        print(f"График сохранен: {plot_file}")
        
        plt.show()
    
    # ===================================================================
    # ЗАКРЫТИЕ
    # ===================================================================
    def on_closing(self):
        self.is_running = False
        self.root.destroy()

# ===================================================================
# ЗАПУСК
# ===================================================================
if __name__ == '__main__':
    print("=" * 60)
    print("ЗАПУСК КЛИЕНТА С ГРАФИЧЕСКИМ ИНТЕРФЕЙСОМ")
    print("=" * 60)
    print(f"Логи сохраняются в папку: logs/")
    print("=" * 60)
    
    root = tk.Tk()
    app = RateMonitor(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()