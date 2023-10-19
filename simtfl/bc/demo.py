from . import BCBlock, BCContext, BCTransaction

def run():
    """
    Runs the demo.
    """
    ctx = BCContext()
    issuance_tx0 = BCTransaction([], [10], 0, issuance=10)
    assert ctx.add_if_valid(issuance_tx0)
    genesis = BCBlock(None, 1, [issuance_tx0])
    assert genesis.score == 1

    issuance_tx1 = BCTransaction([], [6], -1, issuance=5)
    spend_tx = BCTransaction([issuance_tx0.output(0)], [9], 1)
    assert ctx.add_if_valid(issuance_tx1)
    assert ctx.add_if_valid(spend_tx)
    block1 = BCBlock(genesis, 1, [issuance_tx1, spend_tx])
    assert block1.score == 2
