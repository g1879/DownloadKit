# -*- coding:utf-8 -*-
from pathlib import Path
from time import sleep, perf_counter
from typing import Union, List

from DataRecorder import ByteRecorder


class MissionData(object):
    """保存任务数据的对象"""

    def __init__(self, url: str,
                 goal_path: Union[str, Path],
                 rename: Union[str, None],
                 file_exists: str,
                 post_data: Union[str, dict, None],
                 split: bool,
                 kwargs: dict):
        self.url = url
        self.goal_path = goal_path
        self.rename = rename
        self.file_exists = file_exists
        self.post_data = post_data
        self.split = split
        self.kwargs = kwargs


class BaseTask(object):
    """任务类基类"""
    _DONE = 'done'

    def __init__(self, ID: Union[int, str]):
        """初始化                   \n
        :param ID: 任务id
        """
        self._id = ID
        self.state = 'waiting'  # 状态：'waiting'、'running'、'done'
        self.result = None  # 结果：'success'、'skip'、'cancel'、False、None
        self.info = '等待下载'  # 信息

    @property
    def id(self) -> Union[int, str]:
        """返回任务或子任务id"""
        return self._id

    @property
    def data(self):
        """返回任务数据"""
        return

    @property
    def is_done(self) -> bool:
        """返回任务是否结束"""
        return self.state == self._DONE

    def set_states(self,
                   result: Union[bool, None, str] = None,
                   info: str = None,
                   state: str = 'done') -> None:
        """设置任务结果值                                                  \n
        :param result: 结果：'success'、'skip'、'cancel'、False、None
        :param info: 任务信息
        :param state: 任务状态：'waiting'、'running'、'done'
        :return: None
        """
        self.result = result
        self.info = info
        self.state = state


class Mission(BaseTask):
    """任务类"""

    def __init__(self, ID: int, data: MissionData, download_kit):
        """初始化                               \n
        :param ID: 任务id
        :param data: 任务数据
        """
        super().__init__(ID)
        self.download_kit = download_kit
        self._data: MissionData = data
        self.size = None

        self.tasks: List[Task] = []  # 多线程下载单个文件时的子任务
        self.tasks_count = 1
        self.done_tasks_count = 0

        self.file_name = None
        self._path: Union[Path, None] = None  # 文件完整路径，Path对象
        self._recorder = None

    def __repr__(self) -> str:
        return f'<Mission {self.id} {self.info} {self.file_name}>'

    @property
    def data(self) -> MissionData:
        """返回任务数据"""
        return self._data

    @property
    def path(self) -> Union[str, Path]:
        """返回文件保存路径"""
        return self._path

    @path.setter
    def path(self, path: Union[str, Path, None]) -> None:
        """设置文件保存路径"""
        if isinstance(path, (Path, str)):
            path = Path(path)
            self.file_name = path.name

        self._path = path
        self.recorder.set_path(path)

    @property
    def recorder(self) -> ByteRecorder:
        """返回记录器对象"""
        if self._recorder is None:
            self._recorder = ByteRecorder(cache_size=100)
            self._recorder.show_msg = False
        return self._recorder

    @property
    def rate(self) -> Union[float, None]:
        """返回下载进度百分比"""
        if self.path and self.path.exists():
            return round((self.path.stat().st_size / self.size) * 100, 2) if self.size else None
        else:
            return

    def set_done(self, result: Union[bool, None, str], info: str) -> None:
        """设置一个任务为done状态                                          \n
        :param result: 结果：'success'、'skip'、'cancel'、False、None
        :param info: 任务信息
        :return: None
        """
        if result == 'skip':
            self.set_states(result=result, info=info, state=self._DONE)

        elif result == 'cancel' or result is False:
            self.recorder.clear()
            self.set_states(result=result, info=info, state=self._DONE)

        elif result == 'success':
            self.recorder.record()
            if self.size and self.path.stat().st_size < self.size:
                self.del_file()
                self.set_states(False, '下载失败', self._DONE)
            else:
                self.set_states('success', info, self._DONE)

        self.download_kit._when_mission_done(self)

    def a_task_done(self, is_success: bool, info: str) -> None:
        """当一个task完成时调用                 \n
        :param is_success: 该task是否成功
        :param info: 该task传入的信息
        :return: None
        """
        if self.is_done:
            return

        if is_success is False:
            self.break_mission(False, info)
            return

        self.done_tasks_count += 1
        if self.done_tasks_count == self.tasks_count:
            self.set_done('success', info)

    def break_mission(self, result: Union[bool, None, str], info: str) -> None:
        """中止该任务，停止未下载完的task                                  \n
        :param result: 结果：'success'、'skip'、'cancel'、False、None
        :param info: 任务信息
        :return: None
        """
        if self.is_done:
            return

        for task in self.tasks:
            if not task.is_done:
                task.set_states(result=result, info=info, state='cancel')

        while any((not i.is_done for i in self.tasks)):
            sleep(.1)

        self.set_done(result, info)
        self.del_file()

    def cancel(self) -> None:
        """取消该任务，停止未下载完的task"""
        self.break_mission('cancel', '已取消')

    def del_file(self):
        """删除下载的文件"""
        if self.path and self.path.exists():
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
            print(f'url：{self.data.url}')
            t2 = perf_counter()
            while self.file_name is None and perf_counter() - t2 < 4:
                sleep(0.01)
            print(f'文件名：{self.file_name}')
            print(f'目标路径：{self.path}')
            if not self.size:
                print('未知大小 ', end='')

        t1 = perf_counter()
        while not self.is_done and (perf_counter() - t1 < timeout or timeout == 0):
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


class Task(BaseTask):
    """子任务类"""

    def __init__(self, mission: Mission, range_: Union[list, None], ID: str):
        """初始化                               \n
        :param mission: 父任务对象
        :param range_: 读取文件数据范围
        :param ID: 任务id
        """
        super().__init__(ID)
        self.mission = mission  # 父任务
        self.range = range_  # 分块范围

    def __repr__(self) -> str:
        return f'<Task M{self.mid} T{self._id}  {self.info} {self.file_name}>'

    @property
    def mid(self) -> int:
        """返回父任务id"""
        return self.mission.id

    @property
    def data(self) -> MissionData:
        """返回任务数据对象"""
        return self.mission.data

    @property
    def path(self) -> str:
        """返回文件保存路径"""
        return self.mission.path

    @property
    def file_name(self) -> str:
        """返回文件名"""
        return self.mission.file_name

    def add_data(self, data: bytes, seek: int = None) -> None:
        """把数据输入到记录器                           \n
        :param data: 文件字节数据
        :param seek: 在文件中的位置，None表示最后
        :return: None
        """
        self.mission.recorder.add_data(data, seek)

    def set_done(self, result: Union[bool, None, str], info: str) -> None:
        """设置一个子任务为done状态                                          \n
        :param result: 结果：'success'、'skip'、'cancel'、False、None
        :param info: 任务信息
        :return: None
        """
        self.set_states(result=result, info=info, state=self._DONE)
        self.mission.a_task_done(result, info)
