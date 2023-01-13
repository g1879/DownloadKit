# -*- coding:utf-8 -*-
"""
@Author  :   g1879
@Contact :   g1879@qq.com
@File    :   downloadKit.py
"""
from pathlib import Path
from queue import Queue
from re import sub
from threading import Thread, Lock
from time import sleep, perf_counter
from typing import Union, Tuple
from urllib.parse import quote, urlparse

from DataRecorder import Recorder
from requests import Session, Response
from requests.structures import CaseInsensitiveDict

from ._funcs import FileExistsSetter, PathSetter, BlockSizeSetter, copy_session, _set_charset, _get_file_info, LogMode
from .mission import Task, Mission, MissionData, BaseTask


class DownloadKit(object):
    file_exists = FileExistsSetter()
    goal_path = PathSetter()
    block_size = BlockSizeSetter()

    def __init__(self,
                 goal_path: Union[str, Path] = None,
                 roads: int = 10,
                 session=None,
                 file_exists: str = 'rename'):
        """初始化                                                                         \n
        :param goal_path: 文件保存路径
        :param roads: 可同时运行的线程数
        :param session: 使用的Session对象，或配置对象、页面对象等
        :param file_exists: 有同名文件名时的处理方式，可选 'skip', 'overwrite', 'rename'
        """
        self._roads = roads
        self._missions = {}
        self._threads = {i: None for i in range(self._roads)}
        self._waiting_list: Queue = Queue()
        self._missions_num = 0
        self._stop_printing = False  # 用于控制显示线程停止
        self._lock = Lock()
        self._page = None  # 如果接收页面对象则存放于此
        self._retry = None
        self._interval = None
        self._timeout = None

        self._print_mode = None
        self._log_mode = None
        self._logger = None

        self.goal_path: str = goal_path or '.'
        self.file_exists: str = file_exists
        self.show_errmsg: bool = False
        self.block_size: Union[str, int] = '50M'  # 分块大小
        self.session = session

    def __call__(self,
                 file_url: str,
                 goal_path: Union[str, Path] = None,
                 rename: str = None,
                 file_exists: str = None,
                 post_data: Union[str, dict] = None,
                 show_msg: bool = True,
                 **kwargs) -> tuple:
        """以阻塞的方式下载一个文件并返回结果，主要用于兼容旧版DrissionPage                                     \n
        :param file_url: 文件网址
        :param goal_path: 保存路径
        :param rename: 重命名的文件名
        :param file_exists: 遇到同名文件时的处理方式，可选 'skip', 'overwrite', 'rename'，默认跟随实例属性
        :param post_data: post方式使用的数据
        :param show_msg: 是否打印进度
        :param kwargs: 连接参数
        :return: 任务结果和信息组成的tuple
        """
        return self.add(file_url=file_url,
                        goal_path=goal_path,
                        rename=rename,
                        file_exists=file_exists,
                        post_data=post_data,
                        split=False,
                        **kwargs).wait(show=show_msg)

    def set_print(self) -> LogMode:
        """设置打印到控制台的信息，可选全部、错误任务、不打印"""
        if self._print_mode is None:
            self._print_mode = LogMode()
        return self._print_mode

    def set_log(self, log_path: [str, Path] = None) -> LogMode:
        """设置记录到文件的信息，可选全部、错误任务、不记录   \n
        :param log_path: 记录文件路径
        :return: LogMode对象
        """
        if self._log_mode is None:
            self._log_mode = LogMode()
        if log_path is not None:
            if self._logger is not None:
                self._logger.set_path(log_path)
            else:
                self._logger = Recorder(log_path, 1)
        return self._log_mode

    @property
    def roads(self) -> int:
        """可同时运行的线程数"""
        return self._roads

    @roads.setter
    def roads(self, val: int) -> None:
        """设置可同时运行的线程数"""
        if self.is_running:
            print('有任务未完成时不能改变roads。')
            return
        if val != self._roads:
            self._roads = val
            self._threads = {i: None for i in range(self._roads)}

    @property
    def retry(self) -> int:
        """返回连接失败时重试次数"""
        if self._retry is not None:
            return self._retry
        elif self._page is not None:
            return self._page.retry_times
        else:
            return 3

    @retry.setter
    def retry(self, times: int) -> None:
        """设置连接失败时重试次数"""
        if not isinstance(times, int) or times < 0:
            raise TypeError('times参数只能接受int格式且不能小于0。')
        self._retry = times

    @property
    def interval(self) -> float:
        """返回连接失败时重试间隔"""
        if self._interval is not None:
            return self._interval
        elif self._page is not None:
            return self._page.retry_interval
        else:
            return 5

    @interval.setter
    def interval(self, seconds: Union[int, float]) -> None:
        """设置连接失败时重试间隔"""
        if not isinstance(seconds, (int, float)) or seconds < 0:
            raise TypeError('seconds参数只能接受int或float格式且不能小于0。')
        self._interval = seconds

    @property
    def timeout(self) -> float:
        """返回连接超时时间"""
        if self._timeout is not None:
            return self._timeout
        elif self._page is not None:
            return self._page.timeout
        else:
            return 20

    @timeout.setter
    def timeout(self, seconds: Union[int, float]) -> None:
        """设置连接超时时间"""
        if not isinstance(seconds, (int, float)) or seconds < 0:
            raise TypeError('seconds参数只能接受int或float格式且不能小于0。')
        self._timeout = seconds

    @property
    def waiting_list(self) -> Queue:
        """返回等待队列"""
        return self._waiting_list

    @property
    def session(self) -> Session:
        return self._session

    @session.setter
    def session(self, session) -> None:
        try:
            from DrissionPage import WebPage, MixPage, Drission, SessionPage, SessionOptions

            if isinstance(session, SessionOptions):
                self._session = Drission(driver_or_options=False, session_or_options=session).session
            elif isinstance(session, Drission):
                self._session = session.session
            elif isinstance(session, (SessionPage, WebPage, MixPage)):
                self._session = session.session
                self._page = session
            else:
                self._session = Drission(driver_or_options=False).session

        except ImportError:
            self._session = Session()

    @property
    def is_running(self) -> bool:
        """返回是否有线程还在运行"""
        return any(self._threads.values()) or not self.waiting_list.empty()

    def set_proxies(self, http: str = None, https: str = None) -> None:
        """设置代理地址及端口，例：'http://127.0.0.1:1080'         \n
        :param http: http代理地址及端口
        :param https: https代理地址及端口
        :return: None
        """
        if not http.startswith('http://'):
            http = f'http://{http}'
        if not https.startswith('http'):
            https = f'http://{https}'
        self._session.proxies = {'http': http, 'https': https}

    def add(self,
            file_url: str,
            goal_path: Union[str, Path] = None,
            rename: str = None,
            file_exists: str = None,
            post_data: Union[str, dict] = None,
            split: bool = True,
            **kwargs) -> Mission:
        """添加一个下载任务并将其返回                                                                    \n
        :param file_url: 文件网址
        :param goal_path: 保存路径
        :param rename: 重命名的文件名
        :param file_exists: 遇到同名文件时的处理方式，可选 'skip', 'overwrite', 'rename'，默认跟随实例属性
        :param post_data: post方式使用的数据
        :param split: 是否允许多线程分块下载
        :param kwargs: 连接参数
        :return: 任务对象
        """
        data = MissionData(url=file_url,
                           goal_path=str(goal_path or self.goal_path),
                           rename=rename,
                           file_exists=file_exists or self.file_exists,
                           post_data=post_data,
                           split=split,
                           kwargs=kwargs)
        self._missions_num += 1
        mission = Mission(self._missions_num, data, self)
        self._missions[self._missions_num] = mission
        self._run_or_wait(mission)
        return mission

    def _run_or_wait(self, mission: BaseTask):
        """接收任务，有空线程则运行，没有则进入等待队列"""
        thread_id = self._get_usable_thread()
        if thread_id is not None:
            thread = Thread(target=self._run, args=(thread_id, mission))
            self._threads[thread_id] = {'thread': thread, 'mission': None}
            thread.start()
        else:
            self._waiting_list.put(mission)

    def _run(self, ID: int, mission: BaseTask) -> None:
        """线程函数                                 \n
        :param ID: 线程id
        :param mission: 任务对象，Mission或Task
        :return: None
        """
        while True:
            if not mission:  # 如果没有任务，就从等候列表中取一个
                if not self._waiting_list.empty():
                    try:
                        mission = self._waiting_list.get(True, .5)
                    except Exception:
                        self._waiting_list.task_done()
                        break
                else:
                    break

            self._threads[ID]['mission'] = mission
            self._download(mission, ID)
            mission = None

        self._threads[ID] = None

    def get_mission(self, mission_or_id: Union[int, Mission]) -> Mission:
        """根据id值获取一个任务                 \n
        :param mission_or_id: 任务或任务id
        :return: 任务对象
        """
        return self._missions[mission_or_id] if isinstance(mission_or_id, int) else mission_or_id

    def get_failed_missions(self) -> list:
        """返回失败任务列表"""
        return [i for i in self._missions.values() if i.result is False]

    def wait(self,
             mission: Union[int, Mission] = None,
             show: bool = False,
             timeout: float = None) -> Union[tuple, None]:
        """等待所有或指定任务完成                                    \n
        :param mission: 任务对象或任务id，为None时等待所有任务结束
        :param show: 是否显示进度
        :param timeout: 超时时间，默认为连接超时时间，0为无限
        :return: 任务结果和信息组成的tuple
        """
        timeout = timeout if timeout is not None else self.timeout
        if mission:
            return self.get_mission(mission).wait(show, timeout)

        else:
            if show:
                self.show(False)
            else:
                t1 = perf_counter()
                while self.is_running or (perf_counter() - t1 < timeout or timeout == 0):
                    sleep(0.1)

    def cancel(self):
        """取消所有等待中或执行中的任务"""
        for m in self._missions.values():
            m.cancel()

    def show(self, asyn: bool = True, keep: bool = False) -> None:
        """实时显示所有线程进度                 \n
        :param asyn: 是否以异步方式显示
        :param keep: 任务列表为空时是否保持显示
        :return: None
        """
        if asyn:
            Thread(target=self._show, args=(2, keep)).start()
        else:
            self._show(0.1, keep)

    def _show(self, wait: float, keep: bool = False) -> None:
        """实时显示所有线程进度"""
        self._stop_printing = False

        if keep:
            Thread(target=self._stop_show).start()

        t1 = perf_counter()
        while not self._stop_printing and (keep or self.is_running or perf_counter() - t1 < wait):
            print(f'\033[K', end='')
            print(f'等待任务数：{self._waiting_list.qsize()}')
            for k, v in self._threads.items():
                m = v['mission'] if v else None
                if m:
                    items = (m.mission.rate, m.mid) if isinstance(m, Task) else (m.rate, m.id)
                    path = f'M{items[1]} {items[0]}% {m}'
                else:
                    path = '空闲'
                print(f'\033[K', end='')
                print(f'线程{k}：{path}')

            print(f'\033[{self.roads + 1}A\r', end='')
            sleep(0.4)

        print(f'\033[1B', end='')
        for i in range(self.roads):
            print(f'\033[K', end='')
            print(f'线程{i}：空闲')

        print()

    def _connect(self,
                 url: str,
                 mode: str = 'get',
                 data: Union[dict, str] = None,
                 **kwargs) -> Tuple[Union[Response, None], str]:
        """生成response对象                                                   \n
        :param url: 目标url
        :param mode: 'get', 'post' 中选择
        :param data: post方式要提交的数据
        :param kwargs: 连接参数
        :return: tuple，第一位为Response或None，第二位为出错信息或'Success'
        """
        url = quote(url, safe='/:&?=%;#@+!')
        kwargs = CaseInsensitiveDict(kwargs)
        session = copy_session(self.session)

        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        else:
            kwargs['headers'] = CaseInsensitiveDict(kwargs['headers'])

        # 设置referer、host和timeout值
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        scheme = parsed_url.scheme

        if not ('Referer' in kwargs['headers'] or 'Referer' in self.session.headers):
            kwargs['headers']['Referer'] = self._page.url if self._page is not None else f'{scheme}://{hostname}'
        if 'Host' not in kwargs['headers']:
            kwargs['headers']['Host'] = hostname
        if not ('timeout' in kwargs['headers'] or 'timeout' in self.session.headers):
            kwargs['timeout'] = self.timeout

        # 执行连接
        r = err = None
        for i in range(self.retry + 1):
            try:
                if mode == 'get':
                    r = session.get(url, **kwargs)
                elif mode == 'post':
                    r = session.post(url, data=data, **kwargs)

                if r:
                    return _set_charset(r), 'Success'

            except Exception as e:
                err = e

            if r and r.status_code in (403, 404):
                break
            if i < self.retry:
                sleep(self.interval)

        # 返回失败结果
        if r is None:
            return None, '连接失败' if err is None else err
        if not r.ok:
            return r, f'状态码：{r.status_code}'

    def _get_usable_thread(self) -> Union[int, None]:
        """获取可用线程，没有则返回None"""
        for k, v in self._threads.items():
            if v is None:
                return k

    def _stop_show(self) -> None:
        """设置停止打印的变量"""
        input()
        self._stop_printing = True

    def _when_mission_done(self, mission: Mission) -> None:
        """当任务完成时执行的操作                     \n
        :param mission: 完结的任务
        :return: None
        """
        if self.set_print().log_mode == 'all' or (self.set_print().log_mode == 'fail' and mission.result is False):
            print(f'{mission.data.url}\n{mission.result}\n{mission.info}\n')

        if self.set_log().log_mode == 'all' or (self.set_log().log_mode == 'fail' and mission.result is False):
            data = {'url': mission.data.url,
                    'path': mission.data.goal_path,
                    'rename': mission.data.rename,
                    'post_data': mission.data.post_data,
                    'kwargs': mission.data.kwargs}
            self._logger.add_data(data)

    def _download(self,
                  mission_or_task: Union[Mission, Task],
                  thread_id: int) -> None:
        """此方法是执行下载的线程方法，用于根据任务下载文件     \n
        :param mission_or_task: 下载任务对象
        :param thread_id: 线程号
        :return: None
        """
        if mission_or_task.is_done:
            return
        if mission_or_task.state == 'cancel':
            mission_or_task.state = 'done'
            return

        file_url = mission_or_task.data.url
        post_data = mission_or_task.data.post_data
        kwargs = mission_or_task.data.kwargs

        if isinstance(mission_or_task, Task):
            task = mission_or_task
            kwargs = CaseInsensitiveDict(kwargs)
            if 'headers' not in kwargs:
                kwargs['headers'] = {'Range': f"bytes={task.range[0]}-{task.range[1]}"}
            else:
                kwargs['headers']['Range'] = f"bytes={task.range[0]}-{task.range[1]}"

            mode = 'post' if post_data is not None or kwargs.get('json', None) else 'get'
            r, inf = self._connect(file_url, mode=mode, data=post_data, **kwargs)

            if r:
                _do_download(r, task, False)
            else:
                task.set_done(False, inf)

            return

        # ===================开始处理mission====================
        mission = mission_or_task
        mission.info = '下载中'
        mission.state = 'running'

        rename = mission.data.rename
        goal_path = mission.data.goal_path
        file_exists = mission.data.file_exists
        split = mission.data.split

        goal_Path = Path(goal_path)
        # 按windows规则去除路径中的非法字符
        goal_path = goal_Path.anchor + sub(r'[*:|<>?"]', '', goal_path.lstrip(goal_Path.anchor)).strip()
        goal_Path = Path(goal_path).absolute()
        goal_Path.mkdir(parents=True, exist_ok=True)
        goal_path = str(goal_Path)

        if file_exists == 'skip' and rename and (goal_Path / rename).exists():
            mission.file_name = rename
            mission.path = goal_Path / rename
            mission.set_done('skip', str(mission.path))
            return

        mode = 'post' if post_data is not None or kwargs.get('json', None) else 'get'
        r, inf = self._connect(file_url, mode=mode, data=post_data, **kwargs)

        if mission.is_done:
            return

        if not r:
            mission.break_mission(result=False, info=inf)
            return

        # -------------------获取文件信息-------------------
        file_info = _get_file_info(r, goal_path, rename, file_exists, self._lock)
        file_size = file_info['size']
        full_path = file_info['path']
        mission.path = full_path
        mission.file_name = full_path.name
        mission.size = file_size

        if file_info['skip']:
            mission.set_done('skip', str(mission.path))
            return

        # -------------------设置分块任务-------------------
        first = False
        if split and file_size and file_size > self.block_size and r.headers.get('Accept-Ranges') == 'bytes':
            first = True
            chunks = [[s, min(s + self.block_size, file_size)] for s in range(0, file_size, self.block_size)]
            chunks[-1][-1] = ''
            chunks_len = len(chunks)

            task1 = Task(mission, chunks[0], f'1/{chunks_len}')
            mission.tasks_count = chunks_len
            mission.tasks = []
            mission.tasks.append(task1)

            for ind, chunk in enumerate(chunks[1:], 2):
                task = Task(mission, chunk, f'{ind}/{chunks_len}')
                mission.tasks.append(task)
                self._run_or_wait(task)

        else:  # 不分块
            task1 = Task(mission, None, '1/1')
            mission.tasks.append(task1)

        self._threads[thread_id]['mission'] = task1
        _do_download(r, task1, first)


def _do_download(r: Response, task: Task, first: bool = False):
    """执行下载任务                                    \n
    :param r: Response对象
    :param task: 任务
    :param first: 是否第一个分块
    :return: None
    """
    if task.is_done or task.mission.is_done:
        return

    task.set_states(result=None, info='下载中', state='running')
    block_size = 65536  # 64k
    result = None

    try:
        if first:  # 分块时第一块
            r_content = r.iter_content(chunk_size=task.range[1])
            task.add_data(next(r_content), 0)

        else:
            if task.range is None:  # 不分块
                for chunk in r.iter_content(chunk_size=block_size):
                    if task.state in ('cancel', 'done'):
                        result = 'cancel'
                        break
                    if chunk:
                        task.add_data(chunk, None)

            elif task.range[1] == '':  # 结尾的数据块
                begin = task.range[0]
                for chunk in r.iter_content(chunk_size=block_size):
                    if task.state in ('cancel', 'done'):
                        result = 'cancel'
                        break
                    if chunk:
                        task.add_data(chunk, seek=begin)
                        begin += len(chunk)

            else:  # 有始末数字的数据块
                begin, end = task.range
                num = (end - begin) // block_size
                for ind, chunk in enumerate(r.iter_content(chunk_size=block_size), 1):
                    if task.state in ('cancel', 'done'):
                        result = 'cancel'
                        break
                    if chunk:
                        task.add_data(chunk, seek=begin)
                        if ind <= num:
                            begin += block_size

    except Exception as e:
        result, info = False, f'下载失败。{r.status_code} {e}'

    else:
        result = 'success' if result is None else result
        info = str(task.path)

    finally:
        r.close()

    task.set_done(result=result, info=info)
