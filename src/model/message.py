from abc import ABC

type ProgressType = float | int


class IMessage(ABC):
    """
    消息接口类，所有消息类的抽象基类

    定义了应用程序中所有消息的共同接口，确保消息系统的一致性。
    """

    pass


class WarningMessage(IMessage):
    """
    警告消息类，用于传递警告信息

    Attributes:
        title: 警告标题
        message: 警告详细内容
    """

    def __init__(self, title: str, message: str):
        """
        初始化警告消息

        Args:
            title: 警告标题
            message: 警告详细内容
        """
        self.title = title
        self.message = message


class UpdateMessage(IMessage):
    """
    更新消息类，用于通知有新版本可用

    当检测到新版本时，发送此消息触发更新提示。
    """

    def __init__(self):
        """
        初始化更新消息
        """
        pass


class ErrorMessage(IMessage):
    """
    错误消息类，用于传递错误信息

    Attributes:
        title: 错误标题
        message: 错误详细内容
    """

    def __init__(self, title: str, message: str):
        """
        初始化错误消息

        Args:
            title: 错误标题
            message: 错误详细内容
        """
        self.title = title
        self.message = message


class ExitMessage(IMessage):
    """
    退出消息类，用于通知应用程序退出

    当需要退出应用程序时，发送此消息。
    """

    def __init__(self):
        """
        初始化退出消息
        """
        pass


class ConfigLoadMessage(IMessage):
    """
    配置加载消息类，用于传递加载的配置名称列表

    Attributes:
        config_names: 加载的配置名称列表
    """

    def __init__(self, config_names: list[str]):
        """
        初始化配置加载消息

        Args:
            config_names: 加载的配置名称列表
        """
        self.config_names = config_names


class CompressionErrorMessage(IMessage):
    """
    压缩错误消息类，用于传递视频压缩过程中的错误信息

    Attributes:
        title: 错误标题
        message: 错误详细内容
    """

    def __init__(self, title: str, message: str):
        """
        初始化压缩错误消息

        Args:
            title: 错误标题
            message: 错误详细内容
        """
        self.title = title
        self.message = message


class CompressionFinishedMessage(IMessage):
    """
    压缩完成消息类，用于通知视频压缩任务完成

    Attributes:
        total: 完成的视频文件总数
    """

    def __init__(self, total: int):
        """
        初始化压缩完成消息

        Args:
            total: 完成的视频文件总数
        """
        self.total = total


class CompressionStoppedMessage(IMessage):
    """
    压缩终止消息类，用于通知用户主动终止了视频压缩任务

    与"压缩完成"不同，收到此消息表示任务是被终止的，界面应恢复可用状态并如实提示，
    而不是显示"转换结束".
    """

    def __init__(self) -> None:
        """
        初始化压缩终止消息
        """
        pass


class CompressionStartMessage(IMessage):
    """
    压缩开始消息类，用于通知视频压缩任务开始

    Attributes:
        total: 待处理的视频文件总数
    """

    def __init__(self, total: int):
        """
        初始化压缩开始消息

        Args:
            total: 待处理的视频文件总数
        """
        self.total = total


class CompressionCurrentProgressMessage(IMessage):
    """
    当前文件压缩进度
    """

    def __init__(
        self, file_name: str, current: ProgressType, total: ProgressType
    ) -> None:
        self.file_name = file_name
        self.current = current
        self.total = total


class CompressionTotalProgressMessage(IMessage):
    """
    压缩进度消息类，用于传递视频压缩任务的进度信息

    Attributes:
        current: 当前正在处理的文件索引
        total: 待处理的文件总数
        file_name: 当前正在处理的文件名
    """

    def __init__(
        self,
        current: int,
        total: int,
        file_name: str,
    ):
        """
        初始化压缩进度消息

        Args:
            current: 当前正在处理的文件索引（从1开始）
            total: 待处理的文件总数
            file_name: 当前正在处理的文件名（包含路径）
            progress: 当前文件的压缩进度（0-1之间的浮点数）
        """
        self.current = current
        self.total = total
        self.file_name = file_name
