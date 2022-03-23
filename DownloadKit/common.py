# -*- coding:utf-8 -*-
"""
@Author  :   g1879
@Contact :   g1879@qq.com
@File    :   common.py
"""
from copy import copy
from pathlib import Path
from re import search, sub
from typing import Union

from requests import Session


def copy_session(s: Session):
    """复制输入Session对象，返回一个新的"""
    new = Session()
    new.headers = s.headers.copy()
    new.cookies = s.cookies.copy()
    new.stream = True
    new.auth = s.auth
    new.proxies = dict(s.proxies).copy()
    new.params = copy(s.params)  #
    new.cert = s.cert
    new.max_redirects = s.max_redirects
    new.trust_env = s.trust_env
    new.verify = s.verify

    return new


class BlockSizeSetter(object):
    def __set__(self, block_size, val):
        if isinstance(val, int) and val > 0:
            size = val
        elif isinstance(val, str):
            units = {'b': 1, 'k': 1024, 'm': 1048576, 'g': 21474836480}
            num = int(val[:-1])
            unit = units.get(val[-1].lower(), None)
            if unit and num > 0:
                size = num * unit
            else:
                raise ValueError('单位只支持B、K、M、G，数字必须为大于0的整数。')
        else:
            raise TypeError('split_size只能传入int或str，数字必须为大于0的整数。')

        block_size._block_size = size

    def __get__(self, block_size, objtype=None) -> int:
        return block_size._block_size


class PathSetter(object):
    def __set__(self, goal_path, val):
        if val is not None and not isinstance(val, (str, Path)):
            raise TypeError('goal_path只能是str或Path类型。')
        goal_path._goal_path = str(val) if isinstance(val, Path) else val

    def __get__(self, goal_path, objtype=None):
        return goal_path._goal_path


class SessionSetter(object):
    def __set__(self, session, value):
        if isinstance(value, Session):
            session._session = value

        else:
            try:
                from DrissionPage import Drission, MixPage
                from DrissionPage.config import SessionOptions

                if isinstance(value, SessionOptions):
                    session._session = Drission(driver_or_options=False, session_or_options=value).session
                elif isinstance(value, (Drission, MixPage)):
                    session._session = value.session
                else:
                    session._session = Drission(driver_or_options=False).session

            except ImportError:
                session._session = Session()

    def __get__(self, session, objtype=None):
        return session._session


class FileExistsSetter(object):
    def __set__(self, file_exists, mode):
        if mode not in ('skip', 'overwrite', 'rename'):
            raise ValueError("file_exists参数只能传入'skip', 'overwrite', 'rename'")
        file_exists._file_exists = mode

    def __get__(self, file_exists, objtype=None):
        return file_exists._file_exists


def get_usable_path(path: Union[str, Path]) -> Path:
    """检查文件或文件夹是否有重名，并返回可以使用的路径           \n
    :param path: 文件或文件夹路径
    :return: 可用的路径，Path对象
    """
    path = Path(path)
    parent = path.parent
    path = parent / make_valid_name(path.name)
    name = path.stem if path.is_file() else path.name
    ext = path.suffix if path.is_file() else ''

    first_time = True

    while path.exists():
        r = search(r'(.*)_(\d+)$', name)

        if not r or (r and first_time):
            src_name, num = name, '1'
        else:
            src_name, num = r.group(1), int(r.group(2)) + 1

        name = f'{src_name}_{num}'
        path = parent / f'{name}{ext}'
        first_time = None

    return path


def make_valid_name(full_name: str) -> str:
    """获取有效的文件名                  \n
    :param full_name: 文件名
    :return: 可用的文件名
    """
    # ----------------去除前后空格----------------
    full_name = full_name.strip()

    # ----------------使总长度不大于255个字符（一个汉字是2个字符）----------------
    r = search(r'(.*)(\.[^.]+$)', full_name)  # 拆分文件名和后缀名
    if r:
        name, ext = r.group(1), r.group(2)
        ext_long = len(ext)
    else:
        name, ext = full_name, ''
        ext_long = 0

    while get_long(name) > 255 - ext_long:
        name = name[:-1]

    full_name = f'{name}{ext}'

    # ----------------去除不允许存在的字符----------------
    return sub(r'[<>/\\|:*?\n]', '', full_name)


def get_long(txt) -> int:
    """返回字符串中字符个数（一个汉字是2个字符）          \n
    :param txt: 字符串
    :return: 字符个数
    """
    txt_len = len(txt)
    return int((len(txt.encode('utf-8')) - txt_len) / 2 + txt_len)
