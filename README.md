

<h1 align="center" style="font-size:50px;font-weight:bold">VideoSlim</h1>
<p align="center">简洁易用的 Windows 视频压缩工具（x264 + NeroAAC + MP4Box）</p>

<p align="center">
  <img src="./img/interface.jpg" width="520" style="display:block;margin:auto;" />
  <br/>
  <img src="./img/readme.jpg" width="820" style="display:block;margin:auto;" />
  <br/>
  <a href="https://github.com/mainite/VideoSlim">GitHub</a>
  ·
  <a href="#%E4%B8%8B%E8%BD%BD%E4%B8%8E%E5%AE%89%E8%A3%85">下载与安装</a>
  ·
  <a href="#%E5%BF%AB%E9%80%9F%E4%BD%BF%E7%94%A8">快速使用</a>
  ·
  <a href="#%E9%85%8D%E7%BD%AEconfigjson">配置</a>
</p>

---

## 功能特性
- **拖拽即用**: 将文件或文件夹拖入窗口，一键开始压缩
- **批量处理与递归扫描**: 可递归扫描子文件夹中的视频
- **多配置切换**: `config.json` 中可定义多套 x264 参数方案
- **可选删除音频轨道** 与 **完成后删除源文件**
- **自动修正旋转信息**: 若视频存在旋转元数据，自动预处理
- **日志与版本检查**: 生成 `log.txt`，并检查 GitHub 新版本

## 支持平台与依赖
- 操作系统: Windows 10/11（内置二进制工具，Windows 专用）
- Python: 3.9+（含 `tkinter`）
- Python 依赖: `requests`, `pymediainfo`, `windnd`
- 外部二进制已内置于 `VideoSlim/tools/`:
  - `ffmpeg.exe`, `x264_64-8bit.exe`, `neroAacEnc.exe`, `MP4Box.exe` 及必要 DLL

> 提示: `pymediainfo` 依赖 MediaInfo 库。一般可直接使用；若解析失败，请安装 MediaInfo（如桌面版或对应 DLL）。

## 下载与安装
1. 克隆或下载本仓库。
2. 安装 Python 依赖（推荐虚拟环境）：

```bash
pip install requests pymediainfo windnd
```

3. 直接运行应用：

```bash
python VideoSlim/main.py
```

首次运行会在 `VideoSlim/config.json` 生成默认配置。

## 快速使用
1. 启动程序后，将视频文件或包含视频的文件夹拖入窗口。
2. 选择配置（右下拉框）。
3. 视需要勾选：
   - 递归(至最深深度)子文件夹里面的视频
   - 完成后删除旧文件
   - 删除音频轨道
4. 点击“压缩”。

处理完成后，将在源文件同目录生成 `*_x264.mp4` 文件。

## 配置（`config.json`）
应用启动时读取 `VideoSlim/config.json`。若不存在，将按模板创建，结构示例：

```json
{
  "comment": "Configuration file for VideoSlim. See README.md for parameter descriptions.",
  "configs": {
    "default": {
      "x264": { "crf": 23.5, "preset": 8, "I": 600, "r": 4, "b": 3, "opencl_acceleration": false }
    },
    "default_gpu": {
      "x264": { "crf": 23.5, "preset": 8, "I": 600, "r": 4, "b": 3, "opencl_acceleration": true }
    },
    "custom_template": {
      "x264": { "crf": 30, "preset": 8, "I": 600, "r": 4, "b": 3, "opencl_acceleration": false }
    }
  }
}
```

### 参数说明（x264）
- **crf (0–51, 越小越清晰)**: 目标质量控制，常用 18–28。23.5 为默认。
- **preset (0–9)**: 编码速度/压缩效率的平衡，数字越小越快（质量略差）。
- **I**: 关键帧间隔（GOP）。示例为 600。
- **r**: 参考帧数量（x264 的 `-r` 为 reference frames）。
- **b**: B 帧数量（x264 的 `-b` 为 B-frames）。
- **opencl_acceleration**: 是否尝试开启 OpenCL 加速（`--opencl`）。

> 注意: 本项目对 x264 的其他参数使用了一组固定且通用的配置（如 `--me umh --scenecut 60 --qcomp 0.5 --psy-rd 0.3:0 --aq-mode 2 --aq-strength 0.8` 等），只暴露了常用、可安全调整的项以简化使用。

## 工作流程概览
- 若视频含旋转元信息，先用 `ffmpeg` 预处理为中间文件。
- 若保留音频：
  1. `ffmpeg` 提取 WAV（PCM 16-bit）
  2. `neroAacEnc` 编为 AAC LC 128kbps
  3. `x264` 压制视频流
  4. `MP4Box` 混流为 MP4
- 若删除音频：直接用 `x264` 输出 MP4。

## 输出与临时文件
- 输出命名: `原文件名_x264.mp4`
- 临时文件（在每次处理前后清理）:
  - `./pre_temp.mp4`, `./old_atemp.wav`, `./old_atemp.mp4`, `./old_vtemp.mp4`
- 可选项：完成后删除旧文件（源文件）。

## 日志与更新
- 日志: 程序运行会生成 `log.txt`（UTF-8）。
- 更新: 启动后会检查 GitHub Release，若发现新版本会弹窗提示。

## 常见问题
- 无法拖拽/窗口不响应：确认已安装 `windnd`，并以常规权限运行。
- 无法解析媒体信息：安装/更新 MediaInfo；或确保视频文件未被占用。
- 编码失败/报错窗口：查看 `log.txt` 获取具体命令与错误输出。
- 过于模糊或体积过大：调整 `crf`（小=清晰=大体积；大=模糊=小体积）。
- 编码过慢：提高 `preset` 数值或开启 `opencl_acceleration`（视硬件支持）。

## 目录结构
```
VideoSlim/
  main.py                # 启动入口（Tkinter GUI）
  config.json            # 配置文件（首次运行自动生成）
  src/
    view.py              # UI 与交互
    controller.py        # 配置读取、任务调度
    logic.py             # 实际处理流程与子进程命令
    config.py            # 配置模型与默认值
    message.py           # UI 与后台之间的消息类型
  tools/                 # 内置二进制（ffmpeg / x264 / neroAacEnc / MP4Box ...）
img/                     # 截图
```

## 许可证
本项目采用开源许可证，详见 `LICENSE`。第三方工具按其各自许可证使用与分发。

## 致谢
- x264, FFmpeg, MP4Box (GPAC), NeroAAC
- MediaInfo / pymediainfo

—— 祝使用愉快 🎬
