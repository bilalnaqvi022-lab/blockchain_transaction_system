import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "src")
    )
)
from flask import Flask, jsonify, request
from flask_socketio import SocketIO
import threading
import time
from flask import render_template
# Import YOUR existing files
from blockchain import Blockchain
from transaction_pool import TransactionPool
from wallet import Wallet
from miner import ParallelMiner

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# =====================================================
# Existing System
# =====================================================

blockchain = Blockchain()
tx_pool = TransactionPool()

wallets = {
    "Alice": Wallet("Alice"),
    "Bob": Wallet("Bob"),
    "Charlie": Wallet("Charlie")
}

# Give demo balances
for w in wallets.values():
    w.balance = 100

# TPS tracking
tps_history = []

# =====================================================
# Wallets
# =====================================================

@app.route("/wallets")
def get_wallets():

    data = {}

    for name, wallet in wallets.items():

        data[name] = {
            "balance": wallet.balance
        }

    return jsonify(data)


@app.route("/")
def home():
    return render_template("index.html")
# =====================================================
# Transaction
# =====================================================

@app.route("/transaction", methods=["POST"])
def create_transaction():

    data = request.json

    sender = data["sender"]
    receiver = data["receiver"]
    amount = float(data["amount"])

    if sender == receiver:
        return jsonify({"error": "same wallet"})

    sender_wallet = wallets[sender]
    receiver_wallet = wallets[receiver]

    if sender_wallet.balance < amount:
        return jsonify({"error": "insufficient balance"})

    # Deduct/add balance
    sender_wallet.balance -= amount
    receiver_wallet.balance += amount

    # Create tx using your wallet class
    tx = sender_wallet.create_transaction(
        receiver_wallet.address,
        amount
    )

    tx_pool.add_transaction(tx)

    socketio.emit("wallet_update", {
        "sender": sender,
        "receiver": receiver
    })

    socketio.emit("transaction_update", {
        "sender": sender,
        "receiver": receiver,
        "amount": amount
    })

    return jsonify({
        "message": "transaction created"
    })

# =====================================================
# Mining
# =====================================================

@app.route("/mine")
def mine():

    if tx_pool.size == 0:

        return jsonify({
            "message": "no transactions"
        })

    # Store tx count BEFORE mining clears pool
    tx_count = tx_pool.size

    # =================================================
    # Mining animation
    # =================================================

    def animation():

        frames = [
            "⛏ Mining",
            "⛏ Mining.",
            "⛏ Mining..",
            "⛏ Mining...",
            "🔨 Solving Hash",
            "⚡ Processing Block",
            "🚀 Finalizing"
        ]

        for i in range(35):

            socketio.emit(
                "mining_status",
                {
                    "status": frames[i % len(frames)]
                }
            )

            time.sleep(0.12)

    threading.Thread(
        target=animation,
        daemon=True
    ).start()

    # =================================================
    # Actual mining
    # =================================================

    start = time.time()

    miner = ParallelMiner(
        "GUI Miner",
        num_workers=4
    )

    result = blockchain.mine_pending_transactions(
        tx_pool,
        miner
    )

    elapsed = time.time() - start

    # =================================================
    # TPS
    # =================================================

    tps = round(
        tx_count / elapsed,
        2
    ) if elapsed > 0 else 0

    tps_history.append(tps)

    # =================================================
    # WebSocket updates
    # =================================================

    socketio.emit(
        "new_block",
        {
            "block": result.block_id,
            "tps": tps
        }
    )

    socketio.emit(
        "mining_status",
        {
            "status": "✅ Block Successfully Mined"
        }
    )

    return jsonify({
        "message": "block mined",
        "tps": tps
    })
# =====================================================
# Blockchain
# =====================================================

@app.route("/chain")
def chain():

    blocks = []

    for block in blockchain.chain:

        blocks.append({
            "block": block.block_id,
            "hash": block.current_hash,
            "nonce": block.nonce,
            "transactions": len(block.transactions)
        })

    return jsonify(blocks)

# =====================================================
# TPS Graph Data
# =====================================================

@app.route("/tps")
def tps():
    return jsonify(tps_history)

# =====================================================

if __name__ == "__main__":
    socketio.run(app, debug=True)