from . import BCBlock, BCContext, BCTransaction

def run():
    """
    Runs the demo.
    """
    ctx = BCContext()
    issuance_tx = BCTransaction([], [10], 0, issuance=10)
    assert ctx.add_if_valid(issuance_tx)
    genesis = BCBlock(None, 1, [issuance_tx])
    assert genesis.score == 1
    spend_tx = BCTransaction([issuance_tx.output(0)], [9], 1)
    assert ctx.add_if_valid(spend_tx)
    block1 = BCBlock(genesis, 1, [spend_tx])
    del block1
