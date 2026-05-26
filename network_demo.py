"""
Real Socket P2P Network Demo
-----------------------------
Demonstrates actual TCP socket communication between nodes
on localhost (ports 5001, 5002, 5003).

Run this file directly to see real P2P networking in action.
Course: Parallel and Distributed Computing
"""

import sys
import os
import socket
import threading
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from blockchain       import Block, Blockchain
from miner            import ParallelMiner
from transaction_pool import TransactionPool
from wallet           import Wallet


BASE_PORT = 5001


# -----------------------------------------------------------------------
# TCP Peer Node
# -----------------------------------------------------------------------

class TcpNode(threading.Thread):
    """
    Lightweight blockchain node that communicates via real TCP sockets.
    Listens on `port`, connects to known peer ports.
    """

    def __init__(self, node_id: str, port: int, peer_ports: list,
                 pool: TransactionPool):
        super().__init__(daemon=True, name=f"TcpNode-{node_id}")
        self.node_id     = node_id
        self.port        = port
        self.peer_ports  = peer_ports
        self.pool        = pool
        self.blockchain  = Blockchain()
        self.miner       = ParallelMiner(node_id, num_workers=2)
        self._stop       = threading.Event()

    # ------------------------------------------------------------------
    # Thread entry
    # ------------------------------------------------------------------

    def run(self):
        # Start listener thread
        t = threading.Thread(target=self._listen, daemon=True)
        t.start()

        time.sleep(1)  # Let all nodes start their listeners

        # Mine one block and broadcast
        self._mine_and_broadcast()

    def _listen(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("127.0.0.1", self.port))
            srv.listen(10)
            srv.settimeout(10)
            print(f"  [TcpNode:{self.node_id}] Listening on port {self.port}")
            while not self._stop.is_set():
                try:
                    conn, _ = srv.accept()
                    threading.Thread(
                        target=self._handle_conn,
                        args=(conn,),
                        daemon=True,
                    ).start()
                except socket.timeout:
                    continue

    def _handle_conn(self, conn):
        with conn:
            data = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
            if data:
                msg = json.loads(data.decode())
                self._on_message(msg)

    # ------------------------------------------------------------------
    # Broadcasting
    # ------------------------------------------------------------------

    def _broadcast(self, message: dict):
        payload = json.dumps(message).encode()
        for port in self.peer_ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(3)
                    s.connect(("127.0.0.1", port))
                    s.sendall(payload)
            except Exception:
                pass   # Peer may not be ready yet

    def _on_message(self, msg: dict):
        if msg.get("type") == "NEW_BLOCK":
            bd = msg["payload"]
            block = Block(
                block_id=bd["block_id"],
                transactions=bd["transactions"],
                previous_hash=bd["previous_hash"],
                mined_by=bd["mined_by"],
            )
            block.timestamp    = bd["timestamp"]
            block.nonce        = bd["nonce"]
            block.merkle_root  = bd["merkle_root"]
            block.current_hash = bd["current_hash"]

            if self.blockchain.add_block(block):
                print(f"  [OK] [TcpNode:{self.node_id}] Block #{block.block_id} "
                      f"accepted from {bd['mined_by']}")

    # ------------------------------------------------------------------
    # Mining
    # ------------------------------------------------------------------

    def _mine_and_broadcast(self):
        txs = self.pool.pop_transactions(3)
        if not txs:
            txs = [{"tx_id": f"demo_{self.node_id}", "sender": "SYSTEM",
                    "recipient": self.node_id, "amount": 1}]

        block = Block(
            block_id=len(self.blockchain.chain),
            transactions=txs,
            previous_hash=self.blockchain.last_block.current_hash,
            mined_by=self.node_id,
        )
        mined = self.miner.mine_block(block, Blockchain.DIFFICULTY)
        if mined and self.blockchain.add_block(mined):
            print(f"  [*] [TcpNode:{self.node_id}] Mined block #{mined.block_id} – broadcasting")
            self._broadcast({"type": "NEW_BLOCK", "payload": mined.to_dict()})

    def stop(self):
        self._stop.set()


# -----------------------------------------------------------------------
# Demo runner
# -----------------------------------------------------------------------

def run_socket_demo():
    print("\n" + "=" * 60)
    print("  Real Socket P2P Network Demo")
    print("  NFC IET – Parallel & Distributed Computing")
    print("=" * 60)

    # Shared transaction pool
    pool = TransactionPool()
    alice = Wallet("Alice")
    bob   = Wallet("Bob")
    for _ in range(6):
        pool.add_transaction(alice.create_transaction(bob.address, 2.0))

    ports = [BASE_PORT, BASE_PORT + 1, BASE_PORT + 2]

    nodes = []
    for i, port in enumerate(ports):
        peers = [p for p in ports if p != port]
        n = TcpNode(f"Node-{i+1}", port, peers, pool)
        nodes.append(n)

    for n in nodes:
        n.start()

    time.sleep(8)   # Let the network settle

    for n in nodes:
        n.stop()

    print("\n  Final chain lengths:")
    for n in nodes:
        print(f"    {n.node_id}: {len(n.blockchain.chain)} blocks  "
              f"(valid={n.blockchain.is_chain_valid()})")

    print("\n  Socket demo complete.\n")


if __name__ == "__main__":
    run_socket_demo()
