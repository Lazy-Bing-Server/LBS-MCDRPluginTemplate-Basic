import os

from mcdreforged.api.utils import Serializable
from typing import Union, List
from ruamel import yaml

from .utils import gl_server, logger


CONFIG_PATH = os.path.join(gl_server.get_data_folder(), 'config.yml')


class PermissionRequirements(Serializable):
    reload: int = 3


class Configuration(Serializable):
    command_prefix: Union[List[str]] = '!!template'
    permission_requirements: PermissionRequirements = PermissionRequirements.get_default()
    verbosity: bool
    debug_commands: bool

    @property
    def is_verbose(self):
        return self.serialize().get('verbosity', False)

    @property
    def is_debug(self):
        return self.serialize().get('debug_commands', False)

    @property
    def prefix(self) -> List[str]:
        return list(set(self.command_prefix)) if isinstance(self.command_prefix, list) else [self.command_prefix]

    @property
    def primary_prefix(self) -> str:
        return self.prefix[0]

    def get_prem(self, cmd: str) -> int:
        return self.permission_requirements.serialize().get(cmd, 1)

    @classmethod
    def load(cls, echo_in_console: bool = True) -> 'Configuration':
        def log(tr_key: str, *args, **kwargs):
            if gl_server is not None and echo_in_console:
                return logger.info(gl_server.rtr(tr_key, *args, kwargs))

        # file existence check
        if not os.path.isfile(CONFIG_PATH):
            default = cls.get_default()
            default.save()
            log('server_interface.load_config_simple.failed', 'File is not found')
            return default

        # load
        needs_save = False
        try:
            with open(CONFIG_PATH, 'r', encoding='UTF-8') as f:
                raw_ret = yaml.round_trip_load(f)
                cls.deserialize(raw_ret)
        except Exception as e:
            needs_save, ret = True, cls.get_default()
            log('server_interface.load_config_simple.failed', e)
        else:
            # key check
            for key, value in cls.get_default().serialize().items():
                if key not in raw_ret:
                    raw_ret[key], needs_save = value, True
                    log('server_interface.load_config_simple.key_missed', key, value)
            ret = cls.deserialize(raw_ret)

        logger.set_verbose(ret.is_verbose)

        # save file
        if needs_save:
            ret.save()
        log('server_interface.load_config_simple.succeed')
        return ret

    def save(self, keep_fmt=True):
        to_save = self.serialize()
        if os.path.isfile(CONFIG_PATH) and keep_fmt:
            with open(CONFIG_PATH, 'r', encoding='UTF-8') as f:
                fmt = yaml.round_trip_load(f)
                try:
                    self.deserialize(fmt)
                except:
                    pass
                else:
                    fmt.update(to_save)
                    to_save = fmt
        with open(CONFIG_PATH, 'w', encoding='UTF-8') as f:
            logger.debug(to_save)
            yaml.round_trip_dump(to_save, f, allow_unicode=True)


config: Configuration = Configuration.load()
