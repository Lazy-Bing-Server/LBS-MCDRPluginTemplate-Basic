import os
import shutil
from typing import List, Optional, Tuple, get_origin, Type

from mcdreforged.api.types import CommandSource
from mcdreforged.api.utils import Serializable, deserialize
from ruamel import yaml

from my_plugin.utils import file_util
from my_plugin.utils.logger import ConfigSerializeLogger, logger
from my_plugin.utils.misc import psi
from my_plugin.utils.translation import ktr, TRANSLATION_KEY_PREFIX, MessageText


class BlossomSerializable(Serializable):
    @classmethod
    def _fix_data(cls, data: dict, *, father_nodes: Optional[List[str]] = None) -> Tuple[dict, List[str]]:
        needs_save = list()
        annotations = cls.get_field_annotations()
        default_data = cls.get_default().serialize()
        if father_nodes is None:
            father_nodes = []
        fixed_dict = {}

        for key, target_type in annotations.items():
            current_nodes = father_nodes.copy()
            current_nodes.append(key)
            node_name = '.'.join(current_nodes)
            if key not in data.keys():
                if key in default_data.keys():
                    needs_save.append(node_name)
                    fixed_dict[key] = default_data[key]
                continue
            value = data[key]

            def fix_blossom(single_type: Type[BlossomSerializable], single_data: dict):
                nonlocal needs_save
                single_data, save_nodes = single_type._fix_data(single_data, father_nodes=current_nodes)
                needs_save += save_nodes
                return single_data

            if get_origin(target_type) is None and issubclass(target_type, BlossomSerializable):
                value = fix_blossom(target_type, value)
            else:
                try:
                    value = deserialize(value, target_type, error_at_redundancy=True)
                except (ValueError, TypeError):
                    needs_save.append(node_name)
                    if key not in default_data.keys():
                        continue
                    if isinstance(target_type, Serializable):
                        value = target_type.get_default().serialize()
                    else:
                        try:
                            value = target_type(value)
                        except:
                            value = default_data[key]
            fixed_dict[key] = value
        return fixed_dict, needs_save


class ConfigurationBase(BlossomSerializable):
    __rt_yaml = yaml.YAML(typ='rt')
    __safe_yaml = yaml.YAML(typ='safe')
    for item in (__rt_yaml, __safe_yaml):  # type: yaml.YAML
        item.width = 1048576
        item.indent(2, 2, 2)

    def __init__(self, **kwargs):
        self.__file_path = None
        self.__bundled_template_path = None
        self.__logger: Optional["ConfigSerializeLogger"] = None
        self.__reloader: Optional[CommandSource] = None
        super().__init__(**kwargs)

    @staticmethod
    def tr(
        translation_key: str, *args, default_fallback: Optional[MessageText] = None,
        log_error_message: bool = False, prefix: str = f"{TRANSLATION_KEY_PREFIX}config.", **kwargs
    ):
        return ktr(
            translation_key, *args, default_fallback=default_fallback,
            log_error_message=log_error_message, prefix=prefix, **kwargs
        )

    def set_reloader(self, source: Optional[CommandSource] = None):
        self.__reloader = source

    @property
    def reloader(self):
        return self.__reloader

    @property
    def logger(self):
        if self.__logger is None:
            self.__logger = ConfigSerializeLogger()
        return self.__logger

    def get_template(self) -> yaml.CommentedMap:
        try:
            with psi.open_bundled_file(self.__bundled_template_path) as f:
                return self.__rt_yaml.load(f)
        except Exception as e:
            logger.warning("Template not found, is plugin modified?", exc_info=e)
            return yaml.CommentedMap()

    @staticmethod
    def get_data_folder():
        if psi is not None:
            return psi.get_data_folder()
        return '.'

    def after_load(self):
        pass

    def set_config_path(self, file_path: str, bundled_template_path: Optional[str] = None):
        self.__file_path = file_path
        self.__bundled_template_path = bundled_template_path

    def set_logger(self, logger_: ConfigSerializeLogger):
        self.__logger = logger_

    @classmethod
    def load(
            cls,
            file_path: str = 'config.yml',
            bundled_template_path: str = os.path.join("resources", "default_cfg.yml"),
            in_data_folder: bool = True,
            print_to_console: bool = True,
            source_to_reply: Optional[CommandSource] = None,
            encoding: str = 'utf8'
    ):
        serialize_logger = ConfigSerializeLogger()
        with serialize_logger.record_context(verbose=print_to_console, source=source_to_reply):
            default_config = cls.get_default().serialize()
            needs_save = False
            if in_data_folder:
                file_path = os.path.join(cls.get_data_folder(), file_path)

            # Load & Fix data
            try:
                string = file_util.lf_read(file_path, encoding=encoding)
                read_data: dict = cls.__safe_yaml.load(string)
            except Exception as e:
                # Reading failed, remove current file
                file_util.delete(file_path)
                result_config = default_config.copy()
                needs_save = True
                serialize_logger.warn(cls.tr("Fail to read config file, using default config"), exc_info=e)
            else:
                # Reading file succeeded, fix data
                result_config, nodes_require_save = cls._fix_data(read_data)
                if len(nodes_require_save) > 0:
                    needs_save = True
                    serialize_logger.warn(cls.tr("Fixed invalid config keys with default values, please confirm these values: "))
                    serialize_logger.warn(', '.join(nodes_require_save))
            try:
                # Deserialize into configuration instance, should have raise no exception in theory
                result_config = cls.deserialize(result_config)
            except Exception as e:
                # But if exception is raised, that indicates config definition error
                result_config = cls.get_default()
                needs_save = True
                serialize_logger.warn(cls.tr("Fail to read config file, using default config"), exc_info=e)

            result_config.set_logger(logger_=serialize_logger)
            result_config.set_config_path(file_path=file_path, bundled_template_path=bundled_template_path)

            if needs_save:
                # Saving config
                result_config.save(encoding=encoding, print_to_console=print_to_console, source_to_reply=source_to_reply)

            result_config.after_load()
            serialize_logger.info(cls.tr("Config loaded"))
            return result_config

    def save(
            self,
            encoding: str = 'utf8',
            print_to_console: bool = True,
            source_to_reply: Optional[CommandSource] = None
    ):
        file_path = self.__file_path
        config_temp_path = os.path.join(os.path.dirname(file_path), f"temp_{os.path.basename(file_path)}")

        if os.path.isdir(file_path):
            shutil.rmtree(file_path)

        def _save(safe_dump: bool = False):
            with self.logger.reply_to_source_context(verbose=print_to_console, source=source_to_reply):
                if os.path.exists(config_temp_path):
                    file_util.delete(config_temp_path)

                config_content = self.serialize()
                if safe_dump:
                    with file_util.safe_write(file_path, encoding=encoding) as f:
                        self.__safe_yaml.dump(config_content, f)
                    self.logger.warn(self.tr("Validation during config file saving failed, saved without original format"))
                else:
                    formatted_config: yaml.CommentedMap
                    if os.path.isfile(file_path):
                        formatted_config = self.__rt_yaml.load(file_util.lf_read(file_path, encoding=encoding))
                    else:
                        formatted_config = self.get_template()
                    for key, value in config_content.items():
                        formatted_config[key] = value
                    with file_util.safe_write(config_temp_path, encoding=encoding) as f:
                        self.__rt_yaml.dump(formatted_config, f)
                    try:
                        self.deserialize(self.__safe_yaml.load(file_util.lf_read(config_temp_path, encoding=encoding)))
                    except (TypeError, ValueError) as e:
                        self.logger.warn(self.tr("Attempting saving config with original file format due to validation failure while attempting saving config and keep local config file format"), exc_info=e)
                        self.logger.warn(self.tr("There may be mistakes in original config file format, please contact plugin maintainer"))
                        _save(safe_dump=True)
                    else:
                        os.replace(config_temp_path, file_path)
        _save()


"""
    @classmethod
    def load(
            cls,
            file_path: str = 'config.yml',
            bundled_template_path: str = os.path.join("resources", "default_cfg.yml"),
            in_data_folder: bool = True,
            print_to_console: bool = True,
            source_to_reply: Optional[CommandSource] = None,
            encoding: str = 'utf8'
    ):
        serialize_logger = ConfigSerializeLogger(verbose=print_to_console, source_to_reply=source_to_reply)
        default_config = cls.get_default().serialize()
        needs_save = False
        if in_data_folder:
            file_path = os.path.join(psi.get_data_folder(), file_path)
        try:
            with open(file_path, encoding='utf8') as file_handler:
                read_data: dict = yaml.YAML(typ='safe').load(file_handler)
        except Exception as e:
            result_config = default_config.copy()
            needs_save = True
            cls.log('server_interface.load_config_simple.failed', e)
        else:
            result_config = read_data
            if default_config is not None:
                # constructing the result config based on the given default config
                for key, value in default_config.items():
                    if key not in read_data:
                        result_config[key] = value
                        cls.log('server_interface.load_config_simple.key_missed', key, value)
                        needs_save = True
            cls.log('server_interface.load_config_simple.succeed')

        try:
            result_config = cls.deserialize(result_config)
        except Exception as e:
            result_config = cls.get_default()
            needs_save = True
            cls.log('server_interface.load_config_simple.failed', e)

        if needs_save:
            result_config.save()

        logger.set_verbose(result_config.is_verbose)
        return result_config
"""