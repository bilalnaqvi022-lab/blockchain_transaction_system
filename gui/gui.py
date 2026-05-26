import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from tkinter import messagebox

import requests
import socketio
import threading

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

API = "http://127.0.0.1:5000"

# =====================================================
# Socket
# =====================================================

sio = socketio.Client()

# =====================================================
# GUI
# =====================================================

root = tk.Tk()

root.title("Blockchain Dashboard")
root.geometry("1200x750")

# =====================================================
# LEFT PANEL
# =====================================================

left = tk.Frame(root)
left.pack(side="left", fill="y", padx=10, pady=10)

# Wallets
wallet_frame = tk.LabelFrame(left, text="Wallets")
wallet_frame.pack(fill="x", pady=5)

wallet_box = ScrolledText(
    wallet_frame,
    width=35,
    height=10
)

wallet_box.pack()

# Transaction
tx_frame = tk.LabelFrame(left, text="Create Transaction")
tx_frame.pack(fill="x", pady=5)

sender_combo = ttk.Combobox(tx_frame)
sender_combo.pack(fill="x", pady=2)

receiver_combo = ttk.Combobox(tx_frame)
receiver_combo.pack(fill="x", pady=2)

amount_entry = tk.Entry(tx_frame)
amount_entry.pack(fill="x", pady=2)

# =====================================================
# RIGHT PANEL
# =====================================================

right = tk.Frame(root)
right.pack(side="right", fill="both", expand=True)

# Logs
log_frame = tk.LabelFrame(right, text="Logs")
log_frame.pack(fill="both", expand=True, pady=5)

log_box = ScrolledText(log_frame)
log_box.pack(fill="both", expand=True)

# Mining status
mining_label = tk.Label(
    right,
    text="Idle",
    font=("Arial", 16)
)

mining_label.pack(pady=5)

# =====================================================
# TPS GRAPH
# =====================================================

fig = Figure(figsize=(6, 3), dpi=100)

ax = fig.add_subplot(111)

canvas = FigureCanvasTkAgg(fig, master=right)
canvas.get_tk_widget().pack(fill="x")

# =====================================================
# FUNCTIONS
# =====================================================

def log(text):

    log_box.insert(
        tk.END,
        text + "\\n"
    )

    log_box.see(tk.END)

# =====================================================

def refresh_wallets():

    r = requests.get(API + "/wallets")

    data = r.json()

    wallet_box.delete("1.0", tk.END)

    names = list(data.keys())

    sender_combo["values"] = names
    receiver_combo["values"] = names

    for name, info in data.items():

        wallet_box.insert(
            tk.END,
            f"{name}: ${info['balance']}\\n"
        )

    root.after(2000, refresh_wallets)

# =====================================================

def create_transaction():

    sender = sender_combo.get()
    receiver = receiver_combo.get()
    amount = amount_entry.get()

    r = requests.post(
        API + "/transaction",
        json={
            "sender": sender,
            "receiver": receiver,
            "amount": amount
        }
    )

    data = r.json()

    if "error" in data:
        messagebox.showerror(
            "Error",
            data["error"]
        )
        return

    log("Transaction created")

# =====================================================

def mine():

    r = requests.get(API + "/mine")

    data = r.json()

    log(str(data))

# =====================================================

def update_graph():

    r = requests.get(API + "/tps")

    tps = r.json()

    ax.clear()

    ax.plot(tps)

    ax.set_title("TPS Performance")

    canvas.draw()

    root.after(3000, update_graph)

# =====================================================
# BUTTONS
# =====================================================

ttk.Button(
    tx_frame,
    text="Send Transaction",
    command=create_transaction
).pack(fill="x", pady=3)

ttk.Button(
    tx_frame,
    text="Mine Block",
    command=mine
).pack(fill="x", pady=3)

# =====================================================
# SOCKET EVENTS
# =====================================================

@sio.on("transaction_update")
def on_tx(data):

    log(
        f"TX: {data['sender']} -> {data['receiver']} : {data['amount']}"
    )

@sio.on("new_block")
def on_block(data):

    log(
        f"Block {data['block']} mined | TPS: {data['tps']}"
    )

@sio.on("mining_status")
def on_status(data):

    mining_label.config(
        text=data["status"]
    )

# =====================================================

def socket_thread():
    sio.connect(API)
    sio.wait()

threading.Thread(
    target=socket_thread,
    daemon=True
).start()

# =====================================================

refresh_wallets()

update_graph()

root.mainloop()