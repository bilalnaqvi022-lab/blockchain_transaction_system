"""
Main Simulation
===============
Blockchain Transaction Processing System
NFC Institute of Engineering and Technology
Course: Parallel and Distributed Computing

Demonstrates:
  1. Wallet creation and transaction signing
  2. Distributed P2P node network
  3. Parallel Proof-of-Work mining
  4. Consensus and chain synchronisation
  5. Sequential vs. Parallel mining benchmark
"""

import sys
import os
import time
import multiprocessing

# Windows fix: force stdout to UTF-8 so print() never raises
# UnicodeEncodeError on cp1252/cp850 terminals in VS Code / CMD.
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add src/ to path when running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from wallet           import Wallet
from transaction_pool import TransactionPool
from blockchain       import Blockchain, Block
from miner            import ParallelMiner
from node             import Node, MessageBus


# =====================================================================
# Helpers
# =====================================================================

def banner(title: str):
    w = 60
    print("\n" + "=" * w)
    print(f"  {title}")
    print("=" * w)


def section(title: str):
    print(f"\n{'-' * 55}")
    print(f"  {title}")
    print("-" * 55)


# =====================================================================
# Phase 1 – Create wallets & transactions
# =====================================================================

def phase_wallets_and_transactions(pool: TransactionPool):
    section("Phase 1: Wallets & Transactions")

    # Create wallets
    alice = Wallet("Alice")
    bob   = Wallet("Bob")
    sam   = Wallet("Sam")
    alex  = Wallet("Alex")
    tom   = Wallet("Tom")
    jane  = Wallet("Jane")

    wallets = [alice, bob, sam, alex, tom, jane]
    for w in wallets:
        print(f"  Wallet: {w.owner:6s}  Address: {w.address[:20]}...")

    # Fund wallets (genesis coins – just set balance for display)
    alice.balance = 100.0
    sam.balance   = 80.0
    tom.balance   = 60.0

    print()

    # Create transactions
    transactions_to_create = [
        (alice, bob.address,  10.0),
        (sam,   alex.address,  5.0),
        (tom,   jane.address,  8.0),
        (alice, tom.address,  15.0),
        (sam,   bob.address,   3.0),
    ]

    for sender, recipient, amount in transactions_to_create:
        tx = sender.create_transaction(recipient, amount)
        pool.add_transaction(tx)

    pool.display()
    return wallets


# =====================================================================
# Phase 2 – Parallel Mining Benchmark
# =====================================================================

def phase_benchmark():
    section("Phase 2: Parallel vs Sequential Mining Benchmark")

    # Use a higher difficulty so hashing takes measurable time
    BENCH_DIFFICULTY = 5
    num_workers      = multiprocessing.cpu_count()

    base_block = Block(
        block_id=1,
        transactions=[{"tx_id": "bench_tx", "amount": 5}],
        previous_hash="0" * 64,
    )

    miner = ParallelMiner("Benchmark", num_workers=num_workers)

    # Sequential
    print(f"\n  -> Sequential mining (1 worker, difficulty={BENCH_DIFFICULTY}):")
    b_seq = Block(1, [{"tx_id": "bench_seq"}], "0"*64)
    b_seq.timestamp = base_block.timestamp
    t0 = time.time()
    miner.mine_sequential(b_seq, BENCH_DIFFICULTY)
    seq_time = time.time() - t0

    # Parallel (threads – GIL limits true CPU parallelism in CPython)
    print(f"\n  -> Parallel mining ({num_workers} threads, difficulty={BENCH_DIFFICULTY}):")
    b_par = Block(1, [{"tx_id": "bench_par"}], "0"*64)
    b_par.timestamp = base_block.timestamp
    t0 = time.time()
    miner.mine_block(b_par, BENCH_DIFFICULTY)
    par_time = time.time() - t0

    speedup = seq_time / par_time if par_time > 0 else float("inf")

    print(f"\n  {'-'*44}")
    print(f"  Sequential time : {seq_time:.4f} s")
    print(f"  Parallel time   : {par_time:.4f} s  ({num_workers} threads)")
    print(f"  Speed-up        : {speedup:.2f}×")
    print(f"  {'-'*44}")
    print(f"  NOTE: Python threads share one GIL, so CPU-bound tasks do")
    print(f"  not scale linearly with core count. The benefit here is")
    print(f"  that workers search DIFFERENT nonce ranges simultaneously —")
    print(f"  the first valid hash wins, reducing average search depth.")
    print(f"  For true multi-core speedup see: multiprocessing variant.")
    print(f"  {'-'*44}")


# =====================================================================
# Phase 3 – Distributed Node Network
# =====================================================================

def phase_distributed_network(pool: TransactionPool):
    section("Phase 3: Distributed Node Network")

    # Reset bus singleton for a clean run
    bus = MessageBus()
    bus.reset()

    num_nodes = 3
    workers_per_node = max(1, multiprocessing.cpu_count() // num_nodes)

    print(f"\n  Launching {num_nodes} nodes  ({workers_per_node} miner workers each)...")
    nodes = []
    for i in range(1, num_nodes + 1):
        n = Node(
            node_id=f"Node-{i}",
            transaction_pool=pool,
            bus=bus,
            mining_workers=workers_per_node,
        )
        nodes.append(n)

    # Start all nodes
    for n in nodes:
        n.start()

    # Let the network process for a few seconds
    print("\n  Network running – processing transactions...")
    time.sleep(8)

    # Stop all nodes
    for n in nodes:
        n.stop()
    time.sleep(0.5)

    return nodes


# =====================================================================
# Phase 4 – Display Results
# =====================================================================

def phase_display_results(nodes: list):
    section("Phase 4: Blockchain Ledger State")

    for node in nodes:
        print(f"\n  Node: {node.node_id}  |  "
              f"Chain length: {len(node.blockchain.chain)}  |  "
              f"Valid: {node.blockchain.is_chain_valid()}")

        stats = node.blockchain.get_stats()
        print(f"    Blocks: {stats['total_blocks']}   "
              f"Transactions: {stats['total_transactions']}   "
              f"Difficulty: {stats['difficulty']}")

    # Show the longest chain in detail
    longest = max(nodes, key=lambda n: len(n.blockchain.chain))
    print(f"\n  Displaying longest chain ({longest.node_id}):")
    longest.blockchain.display_chain()


# =====================================================================
# Phase 5 – Tamper Detection
# =====================================================================

def phase_tamper_detection(nodes: list):
    section("Phase 5: Tamper Detection (Immutability Test)")

    node = nodes[0]
    chain = node.blockchain.chain

    if len(chain) < 2:
        print("  (Not enough blocks to tamper – skipping)")
        return

    target_block = chain[1]
    print(f"\n  Tampering with Block #{target_block.block_id}...")
    original_hash = target_block.current_hash

    # Modify a transaction amount
    if target_block.transactions:
        target_block.transactions[0]["amount"] = 9999  # Fraudulent change

    is_valid = node.blockchain.is_chain_valid()
    print(f"  Original hash  : {original_hash[:32]}...")
    print(f"  Chain valid?   : {is_valid}")
    if not is_valid:
        print("  [OK] Tamper DETECTED – chain is now invalid (expected).")
        print("  [OK] Immutability confirmed – blockchain rejects altered data.")
    else:
        print("  [!!] Tamper NOT detected – check Merkle root logic.")


# =====================================================================
# Entry Point
# =====================================================================

if __name__ == "__main__":
    banner("Blockchain Transaction Processing System")
    print("  NFC Institute of Engineering and Technology")
    print("  Course : Parallel and Distributed Computing")
    print(f"  CPUs   : {multiprocessing.cpu_count()}")

    # Shared transaction pool
    pool = TransactionPool(max_size=50)

    # Run all phases
    phase_wallets_and_transactions(pool)
    phase_benchmark()
    nodes = phase_distributed_network(pool)
    phase_display_results(nodes)
    phase_tamper_detection(nodes)

    banner("Simulation Complete")
    print("  All phases executed successfully.\n")
