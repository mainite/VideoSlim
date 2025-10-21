from typing import Dict, Any

from tools import clamp


def get_default_configs():
    """
    用于生成配置文件的模板
    :return:
    """
    return {
        "comment": "Configuration file for VideoSlim. See README.md for parameter descriptions.",
        "configs": {
            "default": get_default_config(),
            "custom_template": {
                "x264": {
                    "crf": 30,
                    "preset": 8,
                    "I": 600,
                    "r": 4,
                    "b": 3,
                    "opencl_acceleration": False
                }
            },
            "default_gpu": {
                "x264": {
                    "opencl_acceleration": True,
                    "crf": 23.5,
                    "preset": 8,
                    "I": 600,
                    "r": 4,
                    "b": 3
                }
            }
        }
    }


def _get_default_x264_config() -> Dict[str, Any]:
    return {
        "crf": 23.5,
        "preset": 8,
        "I": 600,
        "r": 4,
        "b": 3,
        "opencl_acceleration": False
    }


def get_default_config() -> Dict[str, Any]:
    """
    默认配置
    :return:
    """
    return {
        "x264": _get_default_x264_config()
    }


class _X264Config:
    """
    X264Config类用于管理X264视频编码器的配置参数。
    """

    def __init__(self, config_dict: Dict[str, Any] = None):
        """
        初始化X264Config对象，从配置字典中获取参数，并设置默认值。
        :param config_dict:
        """
        fixed_config_dict = _get_default_x264_config()
        fixed_config_dict.update(config_dict)

        self.crf = fixed_config_dict["crf"]
        self.preset = fixed_config_dict["preset"]

        self.opencl_acceleration = fixed_config_dict.get("opencl_acceleration", False)
        self.I = fixed_config_dict["I"]
        self.r = fixed_config_dict["r"]
        self.b = fixed_config_dict["b"]

    @property
    def crf(self) -> float:
        """
        获取CRF(恒定速率因子)值
        返回:
            float: 当前的CRF值，范围在0-51之间
        """
        return self._crf

    @crf.setter
    def crf(self, value: float):
        self._crf = clamp(value, 0, 51)

    @property
    def preset(self) -> int:
        """
        获取编码预设值
        返回:
            int: 当前的预设值，范围在0-9之间
        """
        return self._preset

    @preset.setter
    def preset(self, value: int):
        self._preset = clamp(value, 0, 9)


class Config:
    """Configuration class for VideoSlim"""

    def __init__(self, config_dict: Dict[str, Any] = None):
        """
        Initialize configuration

        Args:
            config_dict: Dictionary containing configuration parameters
        """

        fixed_config_dict = get_default_config()
        fixed_config_dict.update(config_dict)

        self.name = fixed_config_dict.get("name", "default")

        self.X264 = _X264Config(fixed_config_dict["x264"])
