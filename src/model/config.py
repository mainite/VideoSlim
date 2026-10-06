from typing import Literal

from pydantic import BaseModel, Field

type X264Preset = Literal[
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
]

type HWAccel = Literal[
    "none",
    "auto",
    "d3d11va",
    "dxva2",
    "cuda",
    "qsv",
    "vaapi",
]

type Encoder = Literal[
    "auto",
    "libx264",
    "h264_nvenc",
    "h264_qsv",
    "h264_amf",
    "h264_mf",
]


class X264ConfigModel(BaseModel):
    """
    X264编码器配置模型类，用于定义X264视频编码器的参数

    该类封装了X264编码器的核心配置参数，包括质量控制、编码速度、关键帧间隔等。
    """

    crf: float = Field(
        default=23.5, gt=0, lt=51, description="CRF值，范围在0-51之间，值越小质量越高"
    )
    preset: X264Preset = Field(
        default="slower",
        description="x264编码预设",
    )
    I: int = Field(default=600, description="关键帧间隔，影响视频的可编辑性和压缩率")
    r: int = Field(default=4, description="B帧参考数，影响视频质量和编码速度")
    b: int = Field(default=3, description="B帧数量，影响视频质量和压缩率")
    opencl_acceleration: bool = Field(
        default=False,
        description="是否启用 x264 的 OpenCL lookahead 加速（需 ffmpeg 构建支持 OpenCL）",
    )
    hwaccel: HWAccel = Field(
        default="auto",
        description=(
            "硬件解码方式，作用于输入文件。none 表示不启用硬件解码；"
            "auto/d3d11va/dxva2/cuda/qsv/vaapi 等值会以 -hwaccel <值> 传入，"
            "解码失败时 ffmpeg 会自动回退到软件解码"
        ),
    )
    encoder: Encoder = Field(
        default="auto",
        description=(
            "视频编码器。auto 会按 h264_nvenc/h264_qsv/h264_amf 顺序自动选择可用的"
            "硬件编码器，均不可用时回退到 libx264；libx264 为软件编码；"
            "h264_nvenc/h264_qsv/h264_amf/h264_mf 为硬件编码器"
        ),
    )
    fallback_to_cpu: bool = Field(
        default=True,
        description="当指定的硬件编码器不可用时，是否自动回退到 libx264 软件编码",
    )


class ConfigModel(BaseModel):
    """
    视频压缩配置模型类，用于定义完整的视频压缩配置

    该类包含配置名称和X264编码器配置，用于完整描述一组视频压缩参数。
    """

    name: str = Field(default="default", description="配置名称，用于标识不同的压缩配置")
    # TODO: 把编码器抽象出来成为接口，后面支持x265
    x264: X264ConfigModel = Field(
        default_factory=X264ConfigModel, description="X264编码器配置参数"
    )


def _fast_config(name: str, encoder: Encoder) -> ConfigModel:
    """
    构建使用硬件编码的快速配置

    硬件不可用时由 fallback_to_cpu 自动回退到 libx264 软件编码。

    Args:
        name: 配置名称
        encoder: 硬件编码器名称

    Returns:
        ConfigModel: 快速配置对象
    """
    return ConfigModel(
        name=name,
        x264=X264ConfigModel(
            crf=26,
            preset="fast",
            opencl_acceleration=True,
            hwaccel="auto",
            encoder=encoder,
        ),
    )


def _default_configs() -> list[ConfigModel]:
    """
    生成程序首次启动时写入的默认配置列表

    包含一个自动选择硬件编码器的 default 配置（均不可用时回退软件编码），
    以及分别强制使用 NVIDIA、AMD、Intel 硬件编码的三套快速配置。

    Returns:
        list[ConfigModel]: 默认配置列表
    """
    return [
        # 默认配置：自动选择可用的硬件编码器，适用于大多数场景
        ConfigModel(),
        # 分别强制使用 NVIDIA / AMD / Intel 硬件编码的快速配置
        _fast_config("fast_nvidia", "h264_nvenc"),
        _fast_config("fast_amd", "h264_amf"),
        _fast_config("fast_intel", "h264_qsv"),
    ]


class ConfigsModel(BaseModel):
    """
    配置集合模型类，用于管理多个视频压缩配置

    该类包含一个配置列表，用于存储和管理应用程序支持的所有视频压缩配置。
    """

    configs: list[ConfigModel] = Field(
        default_factory=_default_configs, description="视频压缩配置列表"
    )
