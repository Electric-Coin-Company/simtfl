class Message:
    def __init__(self, payload):
        self.payload = payload

    def __str__(self):
        return f"{self.__class__.__name__}({self.payload})"

class Ping(Message):
    pass

class Pong(Message):
    pass
