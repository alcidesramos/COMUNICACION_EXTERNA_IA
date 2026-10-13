"""Cliente TCP (puerto 4000, RFC2217 de Wokwi) con widgets para Pot, Temp y Hum.

Espera lineas como:
  Pot: 2048 (1.7%) | Temp: 24.0 C | Hum: 40.0 %
"""
import queue
import re
import socket
import threading
import tkinter as tk
from tkinter import ttk

HOST = "localhost"
PORT = 4000

IAC = 255  # byte de comandos telnet que usa RFC2217
LINE_RE = re.compile(r"Pot:\s*(\d+)")
TEMP_RE = re.compile(r"Temp:\s*(-?[\d.]+)")
HUM_RE = re.compile(r"Hum:\s*([\d.]+)")


def strip_telnet(data: bytes) -> bytes:
    """Elimina secuencias IAC (negociacion telnet/RFC2217) del flujo."""
    out = bytearray()
    i = 0
    while i < len(data):
        if data[i] != IAC:
            out.append(data[i])
            i += 1
        elif i + 1 < len(data) and data[i + 1] == IAC:
            out.append(IAC)
            i += 2
        elif i + 1 < len(data) and data[i + 1] == 250:  # SB ... IAC SE
            end = data.find(bytes([IAC, 240]), i)
            i = len(data) if end == -1 else end + 2
        else:  # IAC + comando + opcion
            i += 3
    return bytes(out)


class Cliente(threading.Thread):
    def __init__(self, q: queue.Queue):
        super().__init__(daemon=True)
        self.q = q
        self.running = True

    def run(self):
        while self.running:
            try:
                self.q.put(("estado", f"Conectando a {HOST}:{PORT}..."))
                with socket.create_connection((HOST, PORT), timeout=3) as s:
                    s.settimeout(1)
                    self.q.put(("estado", f"Conectado a {HOST}:{PORT}"))
                    buf = ""
                    while self.running:
                        try:
                            data = s.recv(1024)
                        except socket.timeout:
                            continue
                        if not data:
                            break
                        buf += strip_telnet(data).decode("utf-8", errors="ignore")
                        while "\n" in buf:
                            linea, buf = buf.split("\n", 1)
                            self.q.put(("linea", linea.strip()))
            except OSError:
                pass
            self.q.put(("estado", "Desconectado - reintentando..."))
            threading.Event().wait(2)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Monitor ESP32")
        self.geometry("420x420")
        self.q = queue.Queue()

        self.estado = tk.StringVar(value="Iniciando...")
        self.pot_raw = tk.StringVar(value="--")
        self.pot_volt = tk.StringVar(value="-- V")
        self.temp = tk.StringVar(value="-- °C")
        self.hum = tk.StringVar(value="-- %")

        pad = {"padx": 12, "pady": 6}

        f_pot = ttk.LabelFrame(self, text="Potenciómetro (GPIO4)")
        f_pot.pack(fill="x", **pad)
        ttk.Label(f_pot, textvariable=self.pot_volt, font=("Segoe UI", 22, "bold")).pack()
        ttk.Label(f_pot, textvariable=self.pot_raw).pack()
        self.bar_pot = ttk.Progressbar(f_pot, maximum=4095)
        self.bar_pot.pack(fill="x", padx=10, pady=6)

        f_t = ttk.LabelFrame(self, text="Temperatura (DHT22)")
        f_t.pack(fill="x", **pad)
        ttk.Label(f_t, textvariable=self.temp, font=("Segoe UI", 22, "bold")).pack()
        self.bar_t = ttk.Progressbar(f_t, maximum=80)  # DHT22: -40..80 °C
        self.bar_t.pack(fill="x", padx=10, pady=6)

        f_h = ttk.LabelFrame(self, text="Humedad (DHT22)")
        f_h.pack(fill="x", **pad)
        ttk.Label(f_h, textvariable=self.hum, font=("Segoe UI", 22, "bold")).pack()
        self.bar_h = ttk.Progressbar(f_h, maximum=100)
        self.bar_h.pack(fill="x", padx=10, pady=6)

        ttk.Label(self, textvariable=self.estado, relief="sunken", anchor="w").pack(
            fill="x", side="bottom"
        )

        self.cliente = Cliente(self.q)
        self.cliente.start()
        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.after(100, self.procesar)

    def procesar(self):
        try:
            while True:
                tipo, valor = self.q.get_nowait()
                if tipo == "estado":
                    self.estado.set(valor)
                else:
                    self.actualizar(valor)
        except queue.Empty:
            pass
        self.after(100, self.procesar)

    def actualizar(self, linea: str):
        m = LINE_RE.search(linea)
        if m:
            raw = int(m.group(1))
            self.pot_raw.set(f"Valor crudo: {raw} / 4095")
            self.pot_volt.set(f"{raw * 3.3 / 4095:.2f} V")
            self.bar_pot["value"] = raw
        m = TEMP_RE.search(linea)
        if m:
            t = float(m.group(1))
            self.temp.set(f"{t:.1f} °C")
            self.bar_t["value"] = max(0, t)
        m = HUM_RE.search(linea)
        if m:
            h = float(m.group(1))
            self.hum.set(f"{h:.1f} %")
            self.bar_h["value"] = h

    def cerrar(self):
        self.cliente.running = False
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
