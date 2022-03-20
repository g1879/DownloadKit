# -*- coding:utf-8 -*-
"""
@Author  :   g1879
@Contact :   g1879@qq.com
@File    :   downloadKit.py
"""
from os import path as os_PATH
from pathlib import Path
from queue import Queue
from random import randint
from re import search, sub
from threading import Thread, Lock
from time import time, sleep, perf_counter
from typing import Union
from urllib.parse import quote, urlparse, unquote

from DataRecorder import Recorder
from requests import Session, Response
from requests.structures import CaseInsensitiveDict

from .common import make_valid_name, get_usable_path, SessionSetter, FileExistsSetter, PathSetter, BlockSizeSetter
from .mission import Task, Mission


class DownloadKit(object):
    session = SessionSetter()
    file_exists = FileExistsSetter()
    goal_path = PathSetter()
    block_size = BlockSizeSetter()

    def __init__(self,
                 goal_path: Union[str, Path] = None,
                 roads: int = 10,
                 session=None,
                 timeout: float = None,
                 file_exists: str = 'rename'):
        """初始化                                                                         \n
        :param goal_path: 文件保存路径
        :param roads: 可同时运行的线程数
        :param session: 使用的Session对象，或配置对象等
        :param timeout: 连接超时时间
        :param file_exists: 有同名文件名时的处理方式，可选 'skip', 'overwrite', 'rename'
        """
        self._roads = roads
        self._missions = {}
        self._threads = {i: None for i in range(self._roads)}
        self._waiting_list: Queue = Queue()
        self._missions_num = 0
        self._stop_printing = False
        self._lock = Lock()

        self.goal_path: str = goal_path or '.'
        self.retry: int = 3
        self.interval: float = 5
        self.timeout: float = timeout if timeout is not None else 20
        self.file_exists: str = file_exists
        self.show_errmsg: bool = False
        self.block_size: Union[str, int] = '20M'  # 分块大小

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
        :param session: 用于下载的Session对象，默认使用实例属性的
        :param rename: 重命名的文件名
        :param file_exists: 遇到同名文件时的处理方式，可选 'skip', 'overwrite', 'rename'，默认跟随实例属性
        :param post_data: post方式使用的数据
        :param show_msg: 是否打印进度
        :param kwargs: 连接参数
        :return: 任务结果和信息组成的tuple
        """
        mission = self.add(file_url=file_url,
                           goal_path=goal_path,
                           rename=rename,
                           file_exists=file_exists,
                           post_data=post_data,
                           split=False,
                           **kwargs)
        return self.wait(mission, show=show_msg)

    @property
    def roads(self) -> int:
        """可同时运行的线程数"""
        return self._roads

    @roads.setter
    def roads(self, val: int) -> None:
        """设置roads值"""
        if self.is_running():
            print('有任务未完成时不能改变roads。')
            return
        if val != self._roads:
            self._roads = val
            self._threads = {i: None for i in range(self._roads)}

    @property
    def waiting_list(self) -> Queue:
        """返回等待队列"""
        return self._waiting_list

    def is_running(self) -> bool:
        """检查是否有线程还在运行中"""
        return any(self._threads.values())

    def add(self,
            file_url: str,
            goal_path: Union[str, Path] = None,
            session: Session = None,
            rename: str = None,
            file_exists: str = None,
            post_data: Union[str, dict] = None,
            split: bool = True,
            **kwargs) -> Mission:
        """添加一个下载任务并将其返回                                                                    \n
        :param file_url: 文件网址
        :param goal_path: 保存路径
        :param session: 用于下载的Session对象，默认使用实例属性的
        :param rename: 重命名的文件名
        :param file_exists: 遇到同名文件时的处理方式，可选 'skip', 'overwrite', 'rename'，默认跟随实例属性
        :param post_data: post方式使用的数据
        :param split: 是否允许多线程分块下载
        :param kwargs: 连接参数
        :return: 任务对象
        """
        data = {'file_url': file_url,
                'goal_path': str(goal_path or self.goal_path),
                'session': session or self.session,
                'rename': rename,
                'file_exists': file_exists or self.file_exists,
                'post_data': post_data,
                'split': split,
                'kwargs': kwargs}
        self._missions_num += 1
        mission = Mission(self._missions_num, data)
        self._missions[self._missions_num] = mission
        self._run_or_wait(mission)
        return mission

    def _run_or_wait(self, mission: Mission):
        """接收任务，有空线程则运行，没有则进入等待队列"""
        thread_id = self._get_usable_thread()
        if thread_id is not None:
            thread = Thread(target=self._run, args=(thread_id, mission))
            self._threads[thread_id] = {'thread': thread, 'mission': None}
            thread.start()
        else:
            self._waiting_list.put(mission)

    def _run(self, ID: int, mission: Mission) -> None:
        """
        :param ID: 线程id
        :param mission: 任务对象，Mission或Task
        :return:
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

    def get_failed_missions(self, save_to: Union[str, Path] = None) -> list:
        lst = [i for i in self._missions.values() if i.result is False]
        if save_to:
            lst = [{'url': i.data['file_url'],
                    'path': i.data['goal_path'],
                    'rename': i.data['rename'],
                    'post_data': i.data['post_data'],
                    'kwargs': i.data['kwargs']}
                   for i in lst]
            r = Recorder(save_to, cache_size=0)
            r.add_data(lst)
            r.record()
        return lst

    def wait(self,
             mission: Union[int, Mission] = None,
             show: bool = True,
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
                while self.is_running() and (perf_counter() - t1 < timeout or timeout == 0):
                    sleep(0.1)

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
        while not self._stop_printing and (keep or self.is_running() or perf_counter() - t1 < wait):
            print(f'\033[K', end='')
            print(f'等待任务数：{self._waiting_list.qsize()}')
            for k, v in self._threads.items():
                m = v['mission'] if v else None
                if m:
                    rate = m.parent.rate if isinstance(m, Task) else m.rate if m else ''
                    path = f'M{m.mid} {rate}% {m}'
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

    def _download(self, mission: Mission, thread_id: int) -> None:
        """此方法是执行下载的线程方法，用于根据任务下载文件     \n
        :param mission: 下载任务对象
        :param thread_id: 线程号
        :return: None
        """
        if mission.state in ('cancel', 'done'):
            mission.state = 'done'
            return

        file_url = mission.data['file_url']
        session = mission.data['session']
        post_data = mission.data['post_data']
        kwargs = mission.data['kwargs']

        if isinstance(mission, Task):
            kwargs = CaseInsensitiveDict(kwargs)
            if 'headers' not in kwargs:
                kwargs['headers'] = {'Range': f"bytes={mission.range[0]}-{mission.range[1]}"}
            else:
                kwargs['headers']['Range'] = f"bytes={mission.range[0]}-{mission.range[1]}"

            mode = 'post' if post_data is not None or kwargs.get('json', None) else 'get'
            r, inf = self._make_response(file_url, session=session, mode=mode, data=post_data, **kwargs)
            _do_download(r, mission, False, self._lock)

            return

        # ===================开始处理mission====================
        mission.info = '下载中'
        mission.state = 'running'

        rename = mission.data['rename']
        goal_path = mission.data['goal_path']
        file_exists = mission.data['file_exists']
        split = mission.data['split']

        goal_Path = Path(goal_path)
        # 按windows规则去除路径中的非法字符
        goal_path = goal_Path.anchor + sub(r'[*:|<>?"]', '', goal_path.lstrip(goal_Path.anchor)).strip()
        goal_Path = Path(goal_path).absolute()
        goal_Path.mkdir(parents=True, exist_ok=True)
        goal_path = str(goal_Path)

        if file_exists == 'skip' and rename and (goal_Path / rename).exists():
            mission.file_name = rename
            mission.path = goal_Path / rename
            _set_result(mission, 'skip', str(mission.path), 'done')
            return

        mode = 'post' if post_data is not None or kwargs.get('json', None) else 'get'
        # r, inf = self._make_response(file_url, session=session, mode=mode, data=post_data, **kwargs)
        with self._lock:
            r, inf = self._make_response(file_url, session=session, mode=mode, data=post_data, **kwargs)

        # -------------------获取文件信息-------------------
        file_info = _get_file_info(r, goal_path, rename, file_exists, self._lock)
        file_size = file_info['size']
        full_path = file_info['path']
        mission.path = full_path
        mission.file_name = full_path.name
        mission.size = file_size

        if file_info['skip']:
            _set_result(mission, 'skip', full_path, 'done')
            return

        if not r:
            _set_result(mission, False, inf, 'done')
            return

        # -------------------设置分块任务-------------------
        first = False
        if split and file_size and file_size > self.block_size and r.headers.get('Accept-Ranges') == 'bytes':
            first = True
            chunks = [[s, min(s + self.block_size, file_size)] for s in range(0, file_size, self.block_size)]
            chunks[-1][-1] = ''

            task1 = Task(mission, chunks[0])

            mission.tasks = []
            mission.tasks.append(task1)

            for chunk in chunks[1:]:
                task = Task(mission, chunk)
                mission.tasks.append(task)
                self._run_or_wait(task)

        else:  # 不分块
            task1 = Task(mission, None)

        self._threads[thread_id]['mission'] = task1
        _do_download(r, task1, first, self._lock)

    def _make_response(self,
                       url: str,
                       session: Session,
                       mode: str = 'get',
                       data: Union[dict, str] = None,
                       **kwargs) -> tuple:
        """生成response对象                                                   \n
        :param url: 目标url
        :param mode: 'get', 'post' 中选择
        :param data: post方式要提交的数据
        :param kwargs: 连接参数
        :return: tuple，第一位为Response或None，第二位为出错信息或'Success'
        """
        if not url:
            if self.show_errmsg:
                raise ValueError('URL为空。')
            return None, 'URL为空。'

        if mode not in ('get', 'post', 'head'):
            raise ValueError("mode参数只能是'get'、'post' 或 'head'。")

        url = quote(url, safe='/:&?=%;#@+!')

        # 设置referer和host值
        kwargs_set = set(x.lower() for x in kwargs)

        hostname = urlparse(url).hostname
        if 'headers' in kwargs_set:
            header_set = set(x.lower() for x in kwargs['headers'])

            if 'referer' not in header_set:
                kwargs['headers']['Referer'] = hostname

            if 'host' not in header_set:
                kwargs['headers']['Host'] = hostname

        else:
            kwargs['headers'] = session.headers
            kwargs['headers']['Host'] = hostname
            kwargs['headers']['Referer'] = hostname

        kwargs['stream'] = True
        if 'timeout' not in kwargs_set:
            kwargs['timeout'] = self.timeout

        r = e = None
        for i in range(self.retry + 1):
            try:
                if mode == 'get':
                    r = session.get(url, **kwargs)
                elif mode == 'post':
                    r = session.post(url, data=data, **kwargs)
                elif mode == 'head':
                    r = session.head(url, **kwargs)

                if r:
                    e = 'Success'
                    r = _set_charset(r)
                    return r, e

            except Exception as e:
                if self.show_errmsg:
                    raise e

            if i < self.retry:
                sleep(self.interval)

        if r is None:
            return None, e

        if not r.ok:
            return r, f'状态码：{r.status_code}'

    def _get_usable_thread(self) -> Union[int, None]:
        """获取可用线程，没有则返回None"""
        for k, v in self._threads.items():
            if v is None:
                return k

    def _stop_show(self):
        input()
        self._stop_printing = True


def _do_download(r: Response, task: Task, first: bool = False, lock: Lock = None):
    """执行下载任务                                    \n
    :param r: Response对象
    :param task: 任务
    :param first: 是否第一个分块
    :param lock: 线程锁
    :return: None
    """
    if task.state in ('cancel', 'done'):
        task.state = 'done'
        return

    task.state = 'running'
    task.info = '下载中'

    while True:  # 争夺文件读写权限
        try:
            f = open(task.path, 'rb+')
            break
        except PermissionError:
            sleep(.2)

    try:
        if first:  # 分块时第一块
            f.write(next(r.iter_content(chunk_size=task.range[1])))

        else:
            if task.range:
                f.seek(task.range[0])
            for chunk in r.iter_content(chunk_size=65536):
                if task.state in ('cancel', 'done'):
                    break
                if chunk:
                    f.write(chunk)

    except Exception as e:
        success, info = False, f'下载失败。{e}'

    else:
        success, info = 'success', str(task.path)

    finally:
        f.close()
        r.close()

    task.state = 'done'
    task.result = success
    task.info = info
    mission = task.parent

    if not success:
        mission.cancel()
        mission.result = success
        mission.info = info

    if mission.is_done() and mission.is_success() is False:
        with lock:
            mission.del_file()


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


def _set_result(mission, res, info, state):
    mission.result = res
    mission.info = info
    mission.state = state
