# -*- coding:utf-8 -*-
"""
@Author  :   g1879
@Contact :   g1879@qq.com
@File    :   downloadKit.py
"""
from os import path as os_PATH, sep
from pathlib import Path
from queue import Queue
from random import randint
from re import search, sub
from threading import Thread
from time import time, sleep, perf_counter
from typing import Union
from urllib.parse import quote, urlparse, unquote

from requests import Session, Response
from DataRecorder import Recorder
from requests.structures import CaseInsensitiveDict

from .common import make_valid_name, get_usable_path, SessionSetter, FileExistsSetter, PathSetter


class DownloadKit(object):
    session = SessionSetter()
    file_exists = FileExistsSetter()
    goal_path = PathSetter()

    def __init__(self,
                 goal_path: Union[str, Path] = None,
                 size: int = 10,
                 session: Union[Session, 'SessionOptions', 'MixPage', 'Drission'] = None,
                 timeout: float = None,
                 file_exists: str = 'rename'):
        """初始化                                                                         \n
        :param goal_path: 文件保存路径
        :param size: 可同时运行的线程数
        :param session: 使用的Session对象，或配置对象等
        :param timeout: 连接超时时间
        :param file_exists: 有同名文件名时的处理方式，可选 'skip', 'overwrite', 'rename'
        """
        self._size = size
        self._missions = {}
        self._threads = {i: None for i in range(self._size)}
        self._waiting_list: Queue = Queue()
        self._missions_num = 0
        self._stop_printing = False

        self.goal_path = str(goal_path)
        self.retry: int = 3
        self.interval: float = 5
        self.timeout: float = timeout if timeout is not None else 20
        self.file_exists: str = file_exists
        self.show_errmsg = False
        self.split_size = 20480  # 分块大小（20M）

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
    def size(self) -> int:
        """可同时运行的线程数"""
        return self._size

    @size.setter
    def size(self, val: int) -> None:
        """设置size值"""
        if self.is_running():
            raise RuntimeError('有任务未完成时不能改变size。')
        if val != self._size:
            self._size = val
            self._threads = {i: None for i in range(self._size)}

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
            **kwargs) -> 'Mission':
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
                'goal_path': str(goal_path or self.goal_path or '.'),
                'session': session or self.session,
                'rename': rename,
                'file_exists': file_exists or self.file_exists,
                'post_data': post_data,
                'split': split,
                'kwargs': kwargs}
        self._missions_num += 1
        mission = Mission(self._missions_num, data, self)
        self._missions[self._missions_num] = mission
        self._run_or_wait(mission)
        return mission

    def _run_or_wait(self, mission: 'Mission'):
        """接收任务，有空线程则运行，没有则进入等待队列"""
        thread_id = self._get_usable_thread()
        if thread_id is not None:
            thread = Thread(target=self._run, args=(thread_id, mission))
            self._threads[thread_id] = {'thread': thread, 'mission': None}
            thread.start()
        else:
            self._waiting_list.put(mission)

    def _run(self, ID: int, mission: 'Mission') -> None:
        """
        :param ID: 线程id
        :param mission: 任务对象
        :return:
        """
        while True:
            if not mission:
                if not self._waiting_list.empty():
                    mission = self._waiting_list.get()
                else:
                    break

            mission.info = '下载中'
            mission.state = 'running'
            self._threads[ID]['mission'] = mission
            self._download(mission)
            mission.state = 'done'
            mission = None

        self._threads[ID] = None

    def get_mission(self, mission_or_id: Union[int, 'Mission']) -> 'Mission':
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
             mission: Union[int, 'Mission'] = None,
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
            mission = self.get_mission(mission)
            if show:
                print(f'url：{mission.data["file_url"]}')
                t2 = perf_counter()
                while mission.file_name is None and perf_counter() - t2 < 4:
                    sleep(0.01)
                print(f'文件名：{mission.file_name}')
                print(f'目标路径：{mission.path}')
                if not mission.size:
                    print('未知大小 ', end='')
            t1 = perf_counter()
            while mission.state != 'done' and (perf_counter() - t1 < timeout or timeout == 0):
                if show and mission.size:
                    try:
                        rate = round((mission.path.stat().st_size / mission.size) * 100, 2)
                        print(f'\r{rate}% ', end='')
                    except FileNotFoundError:
                        pass

                sleep(0.1)

            if show:
                if mission.result is False:
                    print(f'下载失败 {mission.info}')
                elif mission.result is True:
                    print('\r100% ', end='')
                    print(f'下载完成 {mission.info}')
                else:
                    print(f'已跳过 {mission.info}')
                print()

            return mission.result, mission.info

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
                if m and m.path:
                    rate = f'{round((m.path.stat().st_size / m.size) * 100, 2)}%' if m.size else '未知大小'
                    path = f'{m.path}{sep}{m.file_name}'
                else:
                    rate = '空闲'
                    path = ''
                print(f'\033[K', end='')
                print(f'线程{k}：{rate} {path}')

            print(f'\033[{self.size + 1}A\r', end='')
            sleep(0.4)

        print(f'\033[1B', end='')
        for i in range(self.size):
            print(f'\033[K', end='')
            print(f'线程{i}：空闲')

        print()

    def _download(self, mission: 'Mission') -> None:
        """此方法是执行下载的线程方法，用于根据任务下载文件     \n
        :param mission: 下载任务对象
        :return: None
        """

        def set_result(res, info):
            mission.result = res
            mission.info = info

        file_url = mission.data['file_url']
        goal_path = mission.data['goal_path']
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

            result = _do_download(r, mission)
            set_result(*result)

            return

        rename = mission.data['rename']
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
            set_result(None, '已跳过')
            return

        mode = 'post' if post_data is not None or kwargs.get('json', None) else 'get'
        r, inf = self._make_response(file_url, session=session, mode=mode, data=post_data, **kwargs)

        # -------------------获取文件信息-------------------
        file_info = self._get_file_info(r, goal_path, rename, file_exists)
        file_size = file_info['size']
        full_path = file_info['path']
        mission.path = full_path
        mission.file_name = full_path.name
        mission.size = file_size

        if file_info['skip']:
            set_result(None, '已跳过')
            return

        if not r:
            set_result(False, inf)
            return

        # -------------------设置分块任务-------------------
        block = None
        if split and file_size and file_size > self.split_size and r.headers.get('Accept-Ranges') == 'bytes':
            block = self.split_size
            # chunks = [(s+1, min(s + self.split_size, file_size)) for s in range(-1, file_size, self.split_size)]
            chunks = [(s, min(s + self.split_size, file_size)) for s in range(0, file_size, self.split_size)]
            for chunk in chunks[1:]:
                self._run_or_wait(Task(mission, chunk))

        with open(full_path, 'wb') as f:
            pass
        result = _do_download(r, mission, block)
        set_result(*result)

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

    def _get_file_info(self,
                       response,
                       goal_path: str = None,
                       rename: str = None,
                       file_exists: str = None) -> dict:
        """获取文件信息，大小单位为byte                   \n
        包括：size、path、skip
        :param response: Response对象
        :param goal_path: 目标文件夹
        :param rename: 重命名
        :param file_exists: 存在重名文件时的处理方式
        :return: 文件名、文件大小、保存路径、是否跳过
        """
        goal_path = goal_path or self.goal_path or '.'
        file_exists = file_exists or self.file_exists

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

        if full_path.exists():
            if file_exists == 'rename':
                full_path = get_usable_path(full_path)

            elif file_exists == 'skip':
                skip = True

            elif file_exists == 'overwrite':
                pass

        # with open(full_path, 'w'):
        #     pass

        return {'size': file_size,
                'path': full_path,
                'skip': skip}


class Mission(object):
    """任务对象"""

    def __init__(self, ID: int, data: dict, download_kit: DownloadKit):
        """初始化                               \n
        :param ID: 任务id
        :param data: 任务数据
        :param download_kit: 所属下载器
        """
        self._id = ID
        self.data = data
        self.state = 'waiting'  # 'waiting'、'running'、'done'
        self.size = None
        self.info = '等待下载'
        self.result = None  # True表示成功，False表示失败，None表示跳过

        self.tasks = []  # 多线程下载单个文件时的子任务

        self.file_name = None
        self.path = None  # 文件完整路径，Path对象
        self.download_kit = download_kit

    def __repr__(self) -> str:
        return f'<Mission {self.state} {self.info}>'

    @property
    def id(self) -> int:
        return self._id

    def wait(self, show: bool = True) -> tuple:
        """等待当前任务完成                  \n
        :param show: 是否显示下载进度
        :return: 任务结果和信息组成的tuple
        """
        return self.download_kit.wait(self, show)


class Task(Mission):
    def __init__(self, mission: Mission, range_: tuple):
        super().__init__(0, mission.data, mission.download_kit)
        self.parent = mission  # 父任务
        self.range = range_  # 分块范围
        self.path = mission.path
        self.file_name = mission.file_name
        self.download_kit = mission.download_kit

    def __repr__(self) -> str:
        return f'<Task {self.state} {self.info}>'


def _do_download(r: Response, task: Union[Task, Mission], block: int = None) -> tuple:
    """
    :param r: Response对象
    :param task: 任务
    :param block: 如果是只要第一个分块，则设置此参数
    :return:
    """
    # -------------------开始下载-------------------
    path = task.path
    download_status = False
    try:
        # with open(path, 'wb') as f:
        with open(path, 'rb+') as f:
            if block:
                # lock.acquire()
                f.write(next(r.iter_content(chunk_size=block)))
            else:
                if isinstance(task, Task):
                    f.seek(task.range[0])
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

    except Exception as e:
        # raise
        print(task.range)
        download_status, info = False, f'下载失败。\n{e}'

    else:
        #     # todo: 完成后检测任务是否完成，如果是检查文件大小是否正确
        result_size = path.stat().st_size
        if result_size == 0:
            download_status, info = False, '文件大小为0。'
        #
        #     # elif file_size and result_size < file_size:
        #     #     download_status, info = False, '文件下载中断。'
        #
        else:
            download_status, info = True, str(path)

    # finally:
    # todo: 多线程下载一个文件时不要删除
    # if download_status is False and path.exists():
    #     path.unlink()  # 删除下载出错文件
    # r.close()

    # -------------------返回结果-------------------
    # info = str(path.absolute()) if download_status else info
    return download_status, info


def _set_charset(response):
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
