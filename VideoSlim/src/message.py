from wx.lib.evtmgr import MessageAdapter


class Message:
    pass


class WarningMessage(Message):
    def __init__(self, title: str, message: str):
        self.title = title
        self.message = message


class UpdateMessage(Message):
    def __init__(self):
        pass


class ErrorMessage(Message):
    def __init__(self, title: str, message: str):
        self.title = title
        self.message = message


class ExitMessage(Message):
    def __init__(self):
        pass


class ConfigLoadMessage(Message):
    def __init__(self, config_names: list[str]):
        self.config_names = config_names


class CompressionErrorMessage(Message):
    def __init__(self, title: str, message: str):
        self.title = title
        self.message = message


class CompressionFinishedMessage(Message):
    def __init__(self, total: int):
        self.total = total


class CompressionStartMessage(Message):
    def __init__(self, total: int):
        self.total = total


class CompressionProgressMessage(Message):
    def __init__(self, current: int, total: int, file_name: str):
        self.current = current
        self.total = total
        self.file_name = file_name
