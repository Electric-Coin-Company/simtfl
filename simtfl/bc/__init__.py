"""
Abstractions for best-chain transactions, contexts, and blocks.

The transaction protocol is assumed to have a Bitcoin-like TXO-based
transparent component, and a Zcash-like note-based shielded component.

A block consists of a coinbase transaction which can issue new funds,
and zero or more non-coinbase transactions which cannot issue funds.
Each block chains to its parent block.

A transaction pays a transparent fee. Each block's coinbase transaction
collects the fees paid by the other transactions in the block.

The simulation of the shielded protocol does not attempt to model any
actual privacy properties.
"""
