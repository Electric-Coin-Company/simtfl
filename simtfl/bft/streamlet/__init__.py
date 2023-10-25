"""
An implementation of adapted-Streamlet ([CS2020] as modified in [Crosslink]).

[CS2020] https://eprint.iacr.org/2020/088.pdf
[Crosslink] https://hackmd.io/JqENg--qSmyqRt_RqY7Whw?view
"""


from .. import PermissionedBFTBase, PermissionedBFTBlock, PermissionedBFTProposal, \
    two_thirds_threshold


class StreamletGenesis(PermissionedBFTBase):
    """An adapted-Streamlet genesis block."""

    def __init__(self, n):
        """Constructs a genesis block for adapted-Streamlet with `n` nodes."""
        super().__init__(n, two_thirds_threshold(n))


class StreamletBlock(PermissionedBFTBlock):
    """
    An adapted-Streamlet block. Each non-genesis Streamlet block is based on a
    notarized `StreamletProposal`.

    `StreamletBlock`s are taken to be notarized, and therefore valid, by definition.
    """
    pass


class StreamletProposal(PermissionedBFTProposal):
    """An adapted-Streamlet proposal."""

    def __init__(self, parent, epoch):
        """
        Constructs a `StreamletProposal` with the given parent `StreamletBlock`,
        for the given `epoch`. The parameters are determined by the parent block.
        """
        super.__init__(parent)
        self.epoch = epoch
