# ⛓️ Blockchain Transaction Processing System

> A fully functional Python blockchain simulation featuring parallel Proof-of-Work mining, a distributed P2P node network, cryptographic wallets, and a real-time Flask web dashboard.
>
> **NFC Institute of Engineering and Technology** — Parallel and Distributed Computing

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Running the Simulation](#running-the-simulation)
- [Web Dashboard](#web-dashboard)
- [Simulation Phases](#simulation-phases)
- [Architecture](#architecture)
- [Security](#security)

---

## Overview

This project implements a blockchain from scratch in Python, demonstrating core concepts of **parallel computing** (multi-threaded Proof-of-Work) and **distributed systems** (P2P node synchronisation, consensus). It includes two interfaces:

- **CLI Simulation** (`main.py`) — a five-phase walkthrough of the complete transaction lifecycle
- **Flask Web Dashboard** (`backend/app.py`) — a real-time browser UI with WebSocket updates

---

## Features

- 🔐 **Cryptographic Wallets** — OS-entropy key generation, Ethereum-style addresses, SHA-256 transaction signing
- ⛏️ **Parallel Proof-of-Work** — multi-threaded miner splits nonce space across CPU cores; first valid hash wins
- 📡 **P2P Node Network** — threaded nodes broadcast mined blocks via a shared MessageBus; chains sync automatically
- 🌲 **Merkle Root Verification** — any tampered transaction is detected immediately on chain validation
- 🔄 **Double-Spend Prevention** — spent transaction IDs are tracked and rejected at block-append time
- 📊 **Performance Benchmark** — sequential vs. parallel mining comparison with speedup factor
- 🌐 **Real-time Web Dashboard** — Flask + SocketIO with live mining animation and TPS tracking
- 🛡️ **Tamper Detection Demo** — Phase 5 proves chain immutability by modifying a block and re-validating

---

## Project Structure

```
blockchain_project/
│
├── main.py                  # CLI entry point — runs all 5 simulation phases
├── network_demo.py          # Standalone network demonstration script
├── requirements.txt         # Python dependencies
│
├── src/
│   ├── blockchain.py        # Block & Blockchain data structures, Merkle root, validation
│   ├── miner.py             # ParallelMiner — threaded PoW engine
│   ├── node.py              # Node & MessageBus — simulated P2P network
│   ├── transaction_pool.py  # Thread-safe mempool with deduplication
│   └── wallet.py            # Key generation, address derivation, signing
│
├── backend/
│   ├── app.py               # Flask REST API + SocketIO dashboard server
│   ├── templates/           # HTML dashboard template
│   └── static/              # CSS and JavaScript for the frontend
│
├── gui/
│   └── gui.py               # Desktop GUI wrapper
│
└── tests/
    └── test_all.py          # Automated test suite
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Core Logic | Python 3.10+ | Blockchain, mining, wallet |
| Concurrency | `threading` | Parallel PoW workers |
| Cryptography | `hashlib` (SHA-256) | Hashing, signatures, addresses |
| Web Backend | Flask + Flask-SocketIO | REST API & real-time dashboard |
| Serialisation | `json` | Block data encoding |
| Messaging | In-process MessageBus | Simulated P2P networking |

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip

### Install Dependencies

```bash
pip install flask flask-socketio requests python-socketio matplotlib
```

> **Note:** The core blockchain simulation (`main.py`) uses only Python standard library modules (`hashlib`, `threading`, `json`, `time`, `multiprocessing`) and requires no pip installs. External packages are only needed for the web dashboard.

---

## Running the Simulation

```bash
# From the project root
python main.py
```

This runs all **five phases** sequentially and prints results to the console. See [Simulation Phases](#simulation-phases) for details.

---

## Web Dashboard

```bash
cd backend
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

The dashboard provides:
- Live mining animation via WebSocket
- Transaction creation between pre-funded wallets (Alice, Bob, Charlie — 100 coins each)
- Full chain inspection
- TPS (Transactions Per Second) history via `/tps` endpoint

### REST Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/wallets` | List all wallets and balances |
| `POST` | `/transaction` | Submit a new signed transaction |
| `POST` | `/mine` | Trigger PoW mining for pending transactions |
| `GET` | `/chain` | Return the full blockchain as JSON |
| `GET` | `/tps` | Return TPS history across all mining operations |

---

## Simulation Phases

| Phase | Title | What Happens |
|---|---|---|
| **1** | Wallets & Transactions | Creates 6 wallets, funds 3, and signs 5 transactions into the shared pool |
| **2** | Parallel vs Sequential Benchmark | Mines the same block twice — once single-threaded, once multi-threaded — then prints elapsed times and speedup factor |
| **3** | Distributed Node Network | Launches 3 threaded nodes that compete to mine blocks, broadcast solutions, and sync chains over 8 seconds |
| **4** | Ledger State Display | Prints per-node chain stats and the full contents of the longest chain |
| **5** | Tamper Detection | Modifies a transaction amount in Block #1 and re-validates the chain, confirming Merkle root fraud detection |

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              Application Layer               │
│         main.py  /  backend/app.py           │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│               Source Layer (src/)            │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │blockchain│  │  miner   │  │   node    │  │
│  │  .py     │  │  .py     │  │   .py     │  │
│  └──────────┘  └──────────┘  └───────────┘  │
│  ┌──────────────────┐  ┌──────────────────┐  │
│  │transaction_pool  │  │    wallet.py     │  │
│  │     .py          │  │                  │  │
│  └──────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────┘
```

### Parallel Mining Flow

```
mine(block, difficulty=3)
       │
       ├── Worker Thread 0  →  nonces [0 .. 200k)
       ├── Worker Thread 1  →  nonces [200k .. 400k)
       ├── Worker Thread 2  →  nonces [400k .. 600k)
       └── Worker Thread N  →  nonces [N×200k ..)
              │
              └─ First valid hash found → sets stop_event → all others exit
```

### P2P Block Propagation

```
Node A mines block
       │
       └──► MessageBus.broadcast(NEW_BLOCK)
                   │
            ┌──────┴──────┐
            ▼             ▼
         Node B        Node C
      validates      validates
      appends        appends
      removes txs    removes txs
      from pool      from pool
```

---

## Security

| Mechanism | Implementation |
|---|---|
| **Hash Chaining** | Each block stores SHA-256 hash of its predecessor |
| **Merkle Root** | Recomputed on every validation pass; any tx mutation is caught |
| **Proof-of-Work** | Hash must start with `difficulty` leading zeros |
| **Double-Spend Prevention** | `spent_tx_ids` set rejects previously confirmed transaction IDs |
| **Signature Verification** | Pool rejects any transaction without a valid 64-char SHA-256 signature |

---

## License

Academic project — NFC Institute of Engineering and Technology. For educational use only.
