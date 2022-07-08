# -*- coding:utf-8 -*-
"""
@Author  :   g1879
@Contact :   g1879@qq.com
@File    :   _funcs.py
"""
from copy import copy
from os import path as os_PATH
from pathlib import Path
from random import randint
from re import search, sub
from threading import Lock
from time import time
from typing import Union
from urllib.parse import unquote

from requests import Session, Response


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


class FileExistsSetter(object):
    def __set__(self, file_exists, mode):
        mode = mode.lower()
        if mode not in ('skip', 'overwrite', 'rename'):
            raise ValueError("file_exists参数只能传入'skip', 'overwrite', 'rename'")
        file_exists._file_exists = mode

    def __get__(self, file_exists, objtype=None):
        return file_exists._file_exists


class LogMode(object):
    """设置记录或打印哪些任务信息"""

    def __init__(self):
        self.log_mode = None

    def all(self):
        """全部"""
        self.log_mode = 'all'

    def none(self):
        """不记录或打印"""
        self.log_mode = None

    def fail(self):
        """只记录或打印失败任务"""
        self.log_mode = 'fail'


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


def _set_charset(response) -> Response:
    """设置Response对象的编码"""
    # 在headers中获取编码
    content_type = response.headers.get('content-type', '').lower()
    charset = search(r'charset[=: ]*(.*)?[;]', content_type)

    if charset:
        response.encoding = charset.group(1)

    # 在headers中获取不到编码，且如果是网页
    elif content_type.replace(' ', '').startswith('text/html'):
        re_result = search(b'<meta.*?charset=[ \\\'"]*([^"\\\' />]+).*?>', response.content)

        if re_result:
            charset = re_result.group(1).decode()
        else:
            charset = response.apparent_encoding

        response.encoding = charset

    return response


def _get_file_info(response,
                   goal_path: str = None,
                   rename: str = None,
                   file_exists: str = None,
                   lock: Lock = None) -> dict:
    """获取文件信息，大小单位为byte                   \n
    包括：size、path、skip
    :param response: Response对象
    :param goal_path: 目标文件夹
    :param rename: 重命名
    :param file_exists: 存在重名文件时的处理方式
    :param lock: 线程锁
    :return: 文件名、文件大小、保存路径、是否跳过
    """
    # ------------获取文件大小------------
    file_size = response.headers.get('Content-Length', None)
    file_size = None if file_size is None else int(file_size)

    # ------------获取网络文件名------------
    file_name = _get_file_name(response)

    # ------------获取保存路径------------
    goal_Path = Path(goal_path)
    # 按windows规则去除路径中的非法字符
    goal_path = goal_Path.anchor + sub(r'[*:|<>?"]', '', goal_path.lstrip(goal_Path.anchor)).strip()
    goal_Path = Path(goal_path).absolute()
    goal_Path.mkdir(parents=True, exist_ok=True)

    # ------------获取保存文件名------------
    # -------------------重命名，不改变扩展名-------------------
    if rename:
        ext_name = file_name.split('.')[-1]
        if '.' in rename or ext_name == file_name:  # 新文件名带后缀或原文件名没有后缀
            full_name = rename
        else:
            full_name = f'{rename}.{ext_name}'
    else:
        full_name = file_name

    full_name = make_valid_name(full_name)

    # -------------------生成路径-------------------
    skip = False
    full_path = goal_Path / full_name

    with lock:
        if full_path.exists():
            if file_exists == 'rename':
                full_path = get_usable_path(full_path)

            elif file_exists == 'skip':
                skip = True

            elif file_exists == 'overwrite':
                full_path.unlink()

        if not skip:
            with open(full_path, 'wb'):
                pass

    return {'size': file_size,
            'path': full_path,
            'skip': skip}


def _get_file_name(response) -> str:
    """从headers或url中获取文件名，如果获取不到，生成一个随机文件名
    :param response: 返回的response
    :return: 下载文件的文件名
    """
    file_name = ''
    charset = ''
    content_disposition = response.headers.get('content-disposition', '').replace(' ', '')

    # 使用header里的文件名
    if content_disposition:
        txt = search(r'filename\*="?([^";]+)', content_disposition)
        if txt:  # 文件名自带编码方式
            txt = txt.group(1).split("''", 1)
            if len(txt) == 2:
                charset, file_name = txt
            else:
                file_name = txt[0]

        else:  # 文件名没带编码方式
            txt = search(r'filename="?([^";]+)', content_disposition)
            if txt:
                file_name = txt.group(1)

                # 获取编码（如有）
                charset = response.encoding

        file_name = file_name.strip("'")

    # 在url里获取文件名
    if not file_name and os_PATH.basename(response.url):
        file_name = os_PATH.basename(response.url).split("?")[0]

    # 找不到则用时间和随机数生成文件名
    if not file_name:
        file_name = f'untitled_{time()}_{randint(0, 100)}'

    # 去除非法字符
    charset = charset or 'utf-8'
    return unquote(file_name, charset)
