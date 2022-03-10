# -*- coding:utf-8 -*-
from pathlib import Path
from time import sleep, perf_counter


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
        self.result = None  # True表示成功，False表示失败，None表示跳过

        self.tasks = []  # 多线程下载单个文件时的子任务

        self.file_name = None
        self.path: Path = None  # 文件完整路径，Path对象

    def __repr__(self) -> str:
        return f'<Mission {self.state} {self.info}>'

    @property
    def id(self) -> int:
        return self._id

    def __check(self):
        """检查下载是否成功"""
        if self.size:
            return self.path.stat().st_size == self.size

    def wait(self, show: bool = True,
             timeout: float = 0
             ) -> tuple:
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
            elif self.result is True:
                print('\r100% ', end='')
                print(f'下载完成 {self.info}')
            else:
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
        return f'<Task {self.state} {self.info}>'
