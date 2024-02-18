import enum
import os
import contextlib
import shutil

from zipfile import ZipFile
from typing import ContextManager, TextIO, Optional, List
from mcdreforged.api.types import ServerInterface, PluginServerInterface

from my_plugin.utils.util_abc import AbstractUtil
from my_plugin.constants import PACKAGE_PATH

class FileUtils(AbstractUtil):
    class LineBreak(enum.Enum):
        LF = '\n'
        CRLF = '\r\n'
        CR = '\r'


    @staticmethod
    def delete(target_file_path: str):
        if os.path.isfile(target_file_path):
            os.remove(target_file_path)
        elif os.path.isdir(target_file_path):
            shutil.rmtree(target_file_path)


    @classmethod
    @contextlib.contextmanager
    def safe_write(cls, target_file_path: str, *, encoding: str = 'utf8') -> ContextManager[TextIO]:
        temp_file_path = target_file_path + '.tmp'
        cls.delete(temp_file_path)
        with open(temp_file_path, 'w', encoding=encoding) as file:
            yield file
        os.replace(temp_file_path, target_file_path)

    @classmethod
    def lf_read(cls, target_file_path: str, *, is_bundled: bool = False, encoding: str = 'utf8') -> str:
        if is_bundled:
            with cls._plugin_inst.server.open_bundled_file(target_file_path) as f:
                file_string = f.read()
        else:
            with open(target_file_path, 'r', encoding=encoding) as f:
                file_string = f.read()
        return file_string.replace(cls.LineBreak.CRLF.value, cls.LineBreak.LF.value).replace(cls.LineBreak.CR.value, cls.LineBreak.LF.value)


    @staticmethod
    def ensure_dir(folder: str) -> None:
        if os.path.isfile(folder):
            raise FileExistsError('Data folder structure is occupied by existing file')
        if not os.path.isdir(folder):
            os.makedirs(folder)

    @classmethod
    def list_bundled_file(cls, directory_name: str):
        server = cls._plugin_inst.server
        package = PACKAGE_PATH
        if server is not None:
            return server.get_plugin_file_path(server.get_self_metadata().id)
        if os.path.isdir(package):
            return os.listdir(os.path.join(package, directory_name))
        with ZipFile(package, 'r') as zip_file:
            result = []
            directory_name = directory_name.replace('\\', '/').rstrip('/\\') + '/'
            for file_info in zip_file.infolist():
                # is inside the dir and is directly inside
                if file_info.filename.startswith(directory_name):
                    file_name = file_info.filename.replace(directory_name, '', 1)
                    if len(file_name) > 0 and '/' not in file_name.rstrip('/'):
                        result.append(file_name)
        return result
