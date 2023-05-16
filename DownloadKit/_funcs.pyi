# -*- coding:utf-8 -*-
"""
@Author  :   g1879
@Contact :   g1879@qq.com
"""
from pathlib import Path
from threading import Lock
from typing import Union

from requests import Session, Response


def copy_session(session: Session) -> Session: ...


class BlockSizeSetter(object):
    def __set__(self, block_size, val: Union[str, int]): ...

    def __get__(self, block_size, objtype=None) -> int: ...


class PathSetter(object):
    def __set__(self, goal_path, val: Union[str, Path]): ...

    def __get__(self, goal_path, objtype=None): ...


class FileExistsSetter(object):
    def __set__(self, file_exists, mode: str): ...

    def __get__(self, file_exists, objtype=None): ...


def get_usable_path(path: Union[str, Path]) -> Path: ...


def make_valid_name(full_name: str) -> str: ...


def get_long(txt: str) -> int: ...


def set_charset(response: Response) -> Response: ...


def get_file_info(response: Response,
                  goal_path: str = None,
                  rename: str = None,
                  file_exists: str = None,
                  lock: Lock = None) -> dict: ...
