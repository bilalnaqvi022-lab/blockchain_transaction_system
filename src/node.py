"""
Node Module
-----------
Simulates a distributed P2P blockchain node.
Each node maintains its own copy of the ledger and communicates
with peers via a shared in-process message bus (simulating sockets).

This is the core DISTRIBUTED COMPUTING component of the project.
Course: Parallel and Distributed Computing
"""

import threading
import time
from typing import List, Dict, Optional

from blockchain import Block, Blockchain
from miner import ParallelMiner
from transaction_pool import TransactionPool


# -----------------------------------------------------------------------
# Simple in-process message bus (simulates P2P sockets)
# -----------------------------------------------------------------------

class MessageBus:
    """
    Central hub that forwards broadcast messages to all subscribed nodes.
    In a real deployment this would be replaced by TCP sockets / Flask.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._nodes: Dict[str, "Node"] = {}
            cls._instance._lock = threading.Lock()
        return cls._instance

    def register(self, node: "Node"):
        with self._lock:
            self._nodes[node.node_id] = node

    def broadcast(self, sender_id: str, message_type: str, payload: dict):
        """Deliver a message to all nodes except the sender."""
        with self._lock:
            recipients = [n for nid, n in self._nodes.items() if nid != sender_id]
        for node in recipients:
            node.receive_message(sender_id, message_type, payload)

    def reset(self):
        with self._lock:
            self._nodes.clear()


# -----------------------------------------------------------------------
# Node
# -----------------------------------------------------------------------

class Node(threading.Thread):
    """
    A blockchain network node.

    Each node:
      - Runs as a background thread.
      - Maintains its own Blockchain copy.
      - Shares a common TransactionPool.
      - Competes to mine blocks using ParallelMiner.
      - Broadcasts winning blocks to peers via MessageBus.
      - Validates and appends blocks received from peers.
    """

    def __init__(
        self,
        node_id:          str,
        transaction_pool: TransactionPool,
        bus:              MessageBus,
        mining_workers:   int = 2,
    ):
        super().__init__(daemon=True, name=f"Node-{node_id}")
        self.node_id          = node_id
        self.pool             = transaction_pool
        self.bus              = bus
        self.blockchain       = Blockchain()
        self.miner            = ParallelMiner(node_id, num_workers=mining_workers)
        self._stop_event      = threading.Event()
        self._inbox: List[Dict] = []
        self._inbox_lock      = threading.Lock()

        bus.register(self)

    # ------------------------------------------------------------------
    # Thread lifecycle
    # ------------------------------------------------------------------

    def run(self):
        print(f"  [Node:{self.node_id}] Started – listening on network.")
        while not self._stop_event.is_set():
            self._process_inbox()

            # If there are pending transactions, try to mine a block
            if self.pool.size >= 1:
                self._attempt_mining()

            time.sleep(0.2)   # Polling interval

    def stop(self):
        self._stop_event.set()
        print(f"  [Node:{self.node_id}] Stopped.")

    # ------------------------------------------------------------------
    # P2P messaging
    # ------------------------------------------------------------------

    def receive_message(self, sender_id: str, msg_type: str, payload: dict):
        """Called by the MessageBus (may be from another thread)."""
        with self._inbox_lock:
            self._inbox.append({
                "sender":  sender_id,
                "type":    msg_type,
                "payload": payload,
            })

    def _process_inbox(self):
        with self._inbox_lock:
            messages = list(self._inbox)
            self._inbox.clear()

        for msg in messages:
            if msg["type"] == "NEW_BLOCK":
                self._handle_new_block(msg["sender"], msg["payload"])
            elif msg["type"] == "NEW_TRANSACTION":
                self.pool.add_transaction(msg["payload"])

    def _broadcast_block(self, block: Block):
        self.bus.broadcast(self.node_id, "NEW_BLOCK", block.to_dict())

    # ------------------------------------------------------------------
    # Mining
    # ------------------------------------------------------------------

    def _attempt_mining(self):
        # Take a batch of pending transactions
        transactions = self.pool.pop_transactions(count=5)
        if not transactions:
            return

        # Add mining reward transaction
        reward_tx = {
            "tx_id":     f"reward_{self.node_id}_{int(time.time())}",
            "sender":    "SYSTEM",
            "recipient": f"miner_{self.node_id}",
            "amount":    Blockchain.REWARD,
            "signature": "system_reward",
        }
        transactions.append(reward_tx)

        # Build new block
        new_block = Block(
            block_id=len(self.blockchain.chain),
            transactions=transactions,
            previous_hash=self.blockchain.last_block.current_hash,
            mined_by=self.node_id,
        )

        # Mine it (parallel)
        mined = self.miner.mine_block(new_block, Blockchain.DIFFICULTY)
        if mined is None:
            # Return transactions to pool
            for tx in transactions[:-1]:   # exclude reward
                self.pool.add_transaction(tx)
            return

        # Verify integrity before adding
        if self.blockchain.add_block(mined):
            print(f"\n  [*] [Node:{self.node_id}] Block #{mined.block_id} added to own chain.")
            self._broadcast_block(mined)
        else:
            print(f"  [Node:{self.node_id}] Own mined block rejected – possible race condition.")

    # ------------------------------------------------------------------
    # Handling incoming blocks
    # ------------------------------------------------------------------

    def _handle_new_block(self, sender_id: str, block_dict: dict):
        """Validate and append a block received from a peer."""
        # Check if we already have this block
        if block_dict["block_id"] < len(self.blockchain.chain):
            return

        # Reconstruct the block
        block = Block(
            block_id=block_dict["block_id"],
            transactions=block_dict["transactions"],
            previous_hash=block_dict["previous_hash"],
            mined_by=block_dict["mined_by"],
        )
        block.timestamp    = block_dict["timestamp"]
        block.nonce        = block_dict["nonce"]
        block.merkle_root  = block_dict["merkle_root"]
        block.current_hash = block_dict["current_hash"]

        if self.blockchain.add_block(block):
            # Remove confirmed transactions from pool
            confirmed_ids = [tx.get("tx_id") for tx in block.transactions]
            self.pool.remove_confirmed(confirmed_ids)
            print(f"  [OK] [Node:{self.node_id}] Accepted Block #{block.block_id} from {sender_id}")
        else:
            print(f"  [!!] [Node:{self.node_id}] Rejected Block #{block.block_id} from {sender_id}")

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def display_chain(self):
        print(f"\n  {'=' * 50}")
        print(f"  Node: {self.node_id}  |  Chain length: {len(self.blockchain.chain)}")
        self.blockchain.display_chain()

    def __repr__(self):
        return f"Node(id={self.node_id}, blocks={len(self.blockchain.chain)})"
