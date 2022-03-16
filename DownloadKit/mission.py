# -*- coding:utf-8 -*-
from pathlib import Path
from time import sleep, perf_counter
from typing import Union


class Mission(object):
    """任务对象"""

    def __init__(self, ID: int, data: dict):
        """初始化                               \n
        :param ID: 任务id
        :param data: 任务数据
        """
        self._id = ID
        self.data = data
        self.state = 'waiting'  # 'waiting'、'running'、'done'
        self.size = None
        self.info = '等待下载'
        self.result = None  # 'success'、'skip'、False和None四种情况

        self.tasks = []  # 多线程下载单个文件时的子任务

        self.file_name = None
        self.path: Union[Path, None] = None  # 文件完整路径，Path对象

    def __repr__(self) -> str:
        return f'<Mission {self.id} {self.state} {self.result} {self.info}>'

    @property
    def id(self) -> int:
        return self._id

    def is_success(self) -> Union[bool, None]:
        """检查下载是否成功"""
        if self.result is not None:  # 已有结果，直接返回
            return self.result

        if not self.is_done:  # 未完成，返回None表示未知
            return None

        result = None
        if self.size:  # 有size，可返回True或False
            if self.path.stat().st_size == self.size:
                self.info = str(self.path)
                result = 'success'
            else:
                self.info = '下载失败'
                result = False

        else:  # 无size，返回None或False
            if any((i.result is False for i in self.tasks)):
                self.info = '下载失败'
                result = False

        self.result = result
        return result

    def is_done(self) -> bool:
        """检查任务是否完成"""
        if self.state == 'done':  # 已有结果，直接返回
            return True

        if not any((i.state != 'done' for i in self.tasks)):
            if not self.size:
                self.info = str(self.path)
            self.state = 'done'
            return True

        return False

    @property
    def rate(self) -> Union[float, None]:
        """返回下载进度百分比"""
        return round((self.path.stat().st_size / self.size) * 100, 2) if self.size else None

    def cancel(self):
        """停止所有task"""
        for task in self.tasks:
            if task.state == 'running':
                task.state = 'cancel'
                task.result = 'canceled'
                task.info = '已取消'

            elif task.state == 'waiting':
                task.state = 'done'
                task.result = 'canceled'
                task.info = '已取消'

        self.result = 'canceled'
        self.info = '已取消'

        while not self.is_done():
            sleep(.3)

        self.del_file()

    def del_file(self):
        """删除下载的文件"""
        if self.path.exists():
            try:
                self.path.unlink()
            except Exception:
                pass

    def wait(self, show: bool = True, timeout: float = 0) -> tuple:
        """等待当前任务完成                  \n
        :param show: 是否显示下载进度
        :param timeout: 超时时间
        :return: 任务结果和信息组成的tuple
        """
        if show:
            print(f'url：{self.data["file_url"]}')
            t2 = perf_counter()
            while self.file_name is None and perf_counter() - t2 < 4:
                sleep(0.01)
            print(f'文件名：{self.file_name}')
            print(f'目标路径：{self.path}')
            if not self.size:
                print('未知大小 ', end='')

        t1 = perf_counter()
        while self.state != 'done' and (perf_counter() - t1 < timeout or timeout == 0):
            if show and self.size:
                try:
                    rate = round((self.path.stat().st_size / self.size) * 100, 2)
                    print(f'\r{rate}% ', end='')
                except FileNotFoundError:
                    pass

            sleep(0.1)

        if show:
            if self.result is False:
                print(f'下载失败 {self.info}')
            elif self.result == 'success':
                print('\r100% ', end='')
                print(f'下载完成 {self.info}')
            elif self.result == 'skip':
                print(f'已跳过 {self.info}')
            print()

        return self.result, self.info


class Task(Mission):
    def __init__(self, mission: Mission, range_: tuple):
        super().__init__(0, mission.data)
        self.parent = mission  # 父任务
        self.range = range_  # 分块范围
        self.path = mission.path
        self.file_name = mission.file_name

    def __repr__(self) -> str:
        return f'<Task M{self.id} {self.state} {self.result} {self.info}>'

    @property
    def is_done(self) -> bool:
        return self.state == 'done'

    @property
    def is_success(self):
        return True if self.result else False

    @property
    def id(self) -> int:
        return self.parent.id
