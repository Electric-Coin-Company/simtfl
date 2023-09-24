class Message:
    """
    A message with an arbitrary payload.
    """
    def __init__(self, payload):
        """
        Constructs a `Message` with the given payload.
        """
        self.payload = payload

    def __str__(self):
        return f"{self.__class__.__name__}({self.payload})"

class Ping(Message):
    pass

class Pong(Message):
    pass
