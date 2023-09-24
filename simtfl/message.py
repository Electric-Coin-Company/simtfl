class PayloadMessage:
    """
    A message with an arbitrary payload.
    """
    def __init__(self, payload):
        """
        Constructs a `PayloadMessage` with the given payload.
        """
        self.payload = payload

    def __str__(self):
        return f"{self.__class__.__name__}({self.payload})"
