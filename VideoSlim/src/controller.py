import json
import logging
import threading

from .config import *
from .message import *
from .logic import *


class Controller:
    def __init__(self, meta_info: dict[str, Any]):
        self.queue = Queue()
        self.configs_name_list = []
        self.meta_info = meta_info
        self.configs_dict = {}

        self._read_config()

        threading.Thread(target=check_for_updates(self.queue, self.meta_info["VERSION"]), daemon=True).start()

    def _read_config(self):
        """Read configuration from file or create default configuration"""
        logging.info(f"开始读取配置文件: {self.meta_info['CONFIG_FILE']}")
        try:
            # Create default config if file doesn't exist
            if not os.path.exists(self.meta_info["CONFIG_FILE"]):
                logging.warning(f"配置文件不存在: {self.meta_info['CONFIG_FILE']}，将创建默认配置文件")
                send_message(self.queue, WarningMessage("警告", "没有检测到配置文件，将生成一个配置文件"))
                with open(self.meta_info["CONFIG_FILE"], "w", encoding="utf-8") as f:
                    json.dump(get_default_configs(), f, indent=2, ensure_ascii=False)
                logging.info(f"已创建默认配置文件: {self.meta_info['CONFIG_FILE']}")

                # Load configs from default config
                configs = get_default_configs()["configs"]
            else:
                # Load configs from file
                logging.info(f"正在从配置文件加载配置: {self.meta_info['CONFIG_FILE']}")
                with open(self.meta_info["CONFIG_FILE"], encoding="utf-8") as f:
                    configs = json.load(f)["configs"]
                logging.info(f"成功从配置文件加载了 {len(configs)} 个配置")

            # Process each config
            for name, params in configs.items():
                logging.info(f"正在处理配置: {name}")
                # Validate config values
                if name in self.configs_name_list or name in self.configs_dict:
                    logging.warning(f"发现重复的配置名称: {name}，将跳过此配置")
                    send_message(self.queue, WarningMessage("警告", f"读取到重名的配置文件 {name}\n将仅读取最前的配置"))
                    continue

                # Register valid config
                params["name"] = name
                self.configs_dict[name] = Config(params)
                self.configs_name_list.append(name)
                logging.info(f"成功注册配置: {name}")

            # Update combobox values
            if self.configs_name_list:
                logging.info(f"配置加载完成，共加载 {len(self.configs_name_list)} 个有效配置")
                send_message(self.queue, ConfigLoadMessage(self.configs_name_list))
                # self.config_combobox.config(values=self.configs_name_list)
                # self.select_config_name.set(self.configs_name_list[0])
            else:
                logging.exception("没有加载到任何有效配置，应用程序将退出")
                send_message(self.queue, ErrorMessage("错误", "没有有效的配置，应用将退出"))
                send_message(self.queue, ExitMessage())

        except Exception as e:
            logging.exception(f"读取配置文件失败: {e}")
            send_message(self.queue, ErrorMessage("错误", f"读取配置文件失败: {e}"))
            send_message(self.queue, ExitMessage())

    def compression(self, config_name: str, delete_audio: bool, delete_source: bool, file_paths: list[str],
                    recurse: bool):
        """Start video compression process"""
        if not config_name in self.configs_name_list:
            send_message(self.queue, WarningMessage("错误", f"配置文件 {config_name} 不存在"))
            return

        logging.info(f"加载了配置：{self.configs_dict[config_name]}")

        config = self.configs_dict[config_name]

        threading.Thread(target=compression_files,
                         args=(self.queue, config, delete_audio, delete_source, file_paths, recurse,
                               self.meta_info["VIDEO_EXTENSIONS"], self.meta_info["TEMP_FILES"]),
                         daemon=True).start()
