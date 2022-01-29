# -*- coding:utf-8 -*-
from os import path as os_PATH, sep
from pathlib import Path
from queue import Queue
from random import randint
from re import search, sub
from threading import Thread
from time import time, sleep, perf_counter
from typing import Union
from urllib.parse import quote, urlparse, unquote

from requests import Session

from .common import make_valid_name, get_usable_path


class DownloadKit(object):
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

        self.goal_path = str(goal_path) if isinstance(goal_path, Path) else goal_path
        self.retry: int = 3
        self.interval: int = 5
        self.timeout: float = timeout if timeout is not None else 20
        self.file_exists: str = file_exists

        self.session = _get_session(session)

    def __call__(self,
                 file_url: str,
                 goal_path: str = None,
                 session: Session = None,
                 rename: str = None,
                 file_exists: str = None,
                 post_data: Union[str, dict] = None,
                 show_msg: bool = True,
                 retry: int = None,
                 interval: float = None,
                 **kwargs) -> tuple:
        """以阻塞的方式下载一个文件并返回结果                                                              \n
        :param file_url: 文件网址
        :param goal_path: 保存路径
        :param session: 用于下载的Session对象，默认使用实例属性的
        :param rename: 重命名的文件名
        :param file_exists: 遇到同名文件时的处理方式，可选 'skip', 'overwrite', 'rename'，默认跟随实例属性
        :param post_data: post方式使用的数据
        :param show_msg: 是否打印进度
        :param retry: 重试次数，默认跟随实例属性
        :param interval: 重试间隔，默认跟随实例属性
        :param kwargs: 连接参数
        :return: 任务结果和信息组成的tuple
        """
        mission = self.add(file_url=file_url,
                           goal_path=goal_path,
                           session=session,
                           rename=rename,
                           file_exists=file_exists,
                           post_data=post_data,
                           retry=retry,
                           interval=interval,
                           **kwargs)
        return self.wait(mission, show=show_msg)

    @property
    def size(self) -> int:
        """可同时运行的线程数"""
        return self._size

    @property
    def waiting_list(self) -> Queue:
        """返回等待队列"""
        return self._waiting_list

    @property
    def file_exists(self) -> str:
        """此属性表示在遇到目标目录有同名文件名时的处理方式，可选 'skip', 'overwrite', 'rename'"""
        return self._file_exists

    @file_exists.setter
    def file_exists(self, mode: str):
        if mode not in ('skip', 'overwrite', 'rename'):
            raise ValueError("file_exists参数只能传入'skip', 'overwrite', 'rename'")
        self._file_exists = mode

    def is_running(self) -> bool:
        """检查是否有线程还在运行中"""
        return any(self._threads.values())

    def add(self,
            file_url: str,
            goal_path: str = None,
            session: Session = None,
            rename: str = None,
            file_exists: str = None,
            post_data: Union[str, dict] = None,
            retry: int = None,
            interval: float = None,
            **kwargs) -> 'Mission':
        """添加一个下载任务并将其返回                                                                    \n
        :param file_url: 文件网址
        :param goal_path: 保存路径
        :param session: 用于下载的Session对象，默认使用实例属性的
        :param rename: 重命名的文件名
        :param file_exists: 遇到同名文件时的处理方式，可选 'skip', 'overwrite', 'rename'，默认跟随实例属性
        :param post_data: post方式使用的数据
        :param retry: 重试次数，默认跟随实例属性
        :param interval: 重试间隔，默认跟随实例属性
        :param kwargs: 连接参数
        :return: 任务对象
        """
        data = {'file_url': file_url,
                'goal_path': goal_path or self.goal_path or '.',
                'session': session or self.session,
                'rename': rename,
                'file_exists': file_exists or self.file_exists,
                'post_data': post_data,
                'retry': retry if retry is not None else self.retry,
                'interval': interval if interval is not None else self.interval,
                'kwargs': kwargs}
        self._missions_num += 1
        mission = Mission(self._missions_num, data)
        self._missions[self._missions_num] = mission

        thread_id = self._get_usable_thread()
        if thread_id is not None:
            thread = Thread(target=self._run, args=(thread_id, mission))
            self._threads[thread_id] = {'thread': thread, 'mission': None}
            thread.start()
        else:
            self._waiting_list.put(mission)

        return mission

    def _run(self, ID: int, mission: 'Mission'):
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

    def wait(self, mission: Union[int, 'Mission'] = None, show: bool = True) -> Union[tuple, None]:
        """等待所有或指定任务完成                                    \n
        :param mission: 任务对象或任务id，为None时等待所有任务结束
        :param show: 是否显示进度
        :return: 任务结果和信息组成的tuple
        """
        if mission:
            mission = self.get_mission(mission)
            if show:
                print(f'url：{mission.data["file_url"]}')
                t1 = perf_counter()
                while mission.file_name is None and perf_counter() - t1 < 4:
                    sleep(0.01)
                print(f'文件名：{mission.file_name}')
                print(f'目标路径：{mission.path}')

            while mission.state != 'done':
                if show:
                    rate = mission.rate
                    if isinstance(rate, (float, int)):
                        print(f'\r{rate}% ', end='')
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
                self.show()
            else:
                while self.is_running():
                    sleep(0.1)

    def show(self) -> None:
        """实时显示所有线程进度"""
        t1 = perf_counter()
        o = None
        while self.is_running() or perf_counter() - t1 < 2:
            if o:
                print(f'\033[{self.size}A\r', end='')
                print(f'\033[K', end='')
            for k, v in self._threads.items():
                o = True
                m = v['mission'] if v else None
                rate, name, path = (f'{m.rate}%', m.file_name, m.path) if m else (None, None, None)
                print(f'线程{k}：{rate} {path}{sep}{name}')

            sleep(0.2)

        print(f'\033[{self.size}A', end='')
        for i in range(self.size):
            print(f'\033[K', end='')
            print(f'线程{i}：None')

    def _get_usable_thread(self) -> Union[int, None]:
        """获取可用线程，没有则返回None"""
        for k, v in self._threads.items():
            if v is None:
                return k

    def _download(self, mission: 'Mission') -> None:
        """此方法是执行下载的线程方法，用于根据任务下载文件     \n
        :param mission: 下载任务对象
        :return: None
        """
        file_url = mission.data['file_url']
        goal_path = mission.data['goal_path']
        session = mission.data['session']
        rename = mission.data['rename']
        file_exists = mission.data['file_exists']
        post_data = mission.data['post_data']
        kwargs = mission.data['kwargs']
        retry_times = mission.data['retry'] if mission.data['retry'] is not None else self.retry
        retry_interval = mission.data['interval'] if mission.data['interval'] is not None else self.interval

        goal_Path = Path(goal_path)
        # 按windows规则去除路径中的非法字符
        goal_path = goal_Path.anchor + sub(r'[*:|<>?"]', '', goal_path.lstrip(goal_Path.anchor)).strip()
        goal_Path = Path(goal_path).absolute()
        goal_Path.mkdir(parents=True, exist_ok=True)
        goal_path = str(goal_Path)
        mission.path = goal_path

        def set_result(res, info):
            mission.result = res
            mission.info = info

        if file_exists == 'skip' and rename and (goal_Path / rename).exists():
            mission.file_name = rename
            set_result(None, '已跳过')
            return

        def do() -> tuple:
            kwargs['stream'] = True
            if 'timeout' not in kwargs:
                kwargs['timeout'] = 20

            # 生成临时的response
            mode = 'post' if post_data is not None or kwargs.get('json', None) else 'get'
            r, info = self._make_response(file_url, session=session, mode=mode, data=post_data, **kwargs)

            if r is None:
                return False, info

            if not r.ok:
                return False, f'状态码：{r.status_code}'

            # -------------------获取文件名-------------------
            file_name = _get_download_file_name(file_url, r)

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

            mission.file_name = full_path.name

            # -------------------开始下载-------------------
            if skip:
                return None, str(full_path)

            # 获取远程文件大小
            content_length = r.headers.get('content-length')
            file_size = int(content_length) if content_length else None

            # 已下载文件大小和下载状态
            downloaded_size, download_status = 0, False

            try:
                with open(str(full_path), 'wb') as tmpFile:
                    for chunk in r.iter_content(chunk_size=1024):
                        if chunk:
                            tmpFile.write(chunk)

                            # 如表头有返回文件大小，显示进度
                            if file_size:
                                downloaded_size += 1024
                                rate = downloaded_size / file_size if downloaded_size < file_size else 1
                                mission.rate = round(rate * 100, 2)

            except Exception as e:
                download_status, info = False, f'下载失败。\n{e}'

            else:
                if full_path.stat().st_size == 0:
                    download_status, info = False, '文件大小为0。'

                else:
                    download_status, info = True, str(full_path)

            finally:
                if download_status is False and full_path.exists():
                    full_path.unlink()  # 删除下载出错文件
                r.close()

            # -------------------返回结果-------------------
            info = str(full_path.absolute()) if download_status else info
            return download_status, info

        result = do()

        if result[0] is False:  # 第一位为None表示跳过的情况
            for i in range(retry_times):
                sleep(retry_interval)

                result = do()
                if result[0] is not False:
                    break

        set_result(*result)

    def _make_response(self,
                       url: str,
                       session: Session,
                       mode: str = 'get',
                       data: Union[dict, str] = None,
                       show_errmsg: bool = False,
                       **kwargs) -> tuple:
        """生成response对象                                                   \n
        :param url: 目标url
        :param mode: 'get', 'post' 中选择
        :param data: post方式要提交的数据
        :param show_errmsg: 是否显示和抛出异常
        :param kwargs: 连接参数
        :return: tuple，第一位为Response或None，第二位为出错信息或'Success'
        """
        if not url:
            if show_errmsg:
                raise ValueError('URL为空。')
            return None, 'URL为空。'

        if mode not in ('get', 'post'):
            raise ValueError("mode参数只能是'get'或'post'。")

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

        if 'timeout' not in kwargs_set:
            kwargs['timeout'] = self.timeout

        try:
            r = None

            if mode == 'get':
                r = session.get(url, **kwargs)
            elif mode == 'post':
                r = session.post(url, data=data, **kwargs)

        except Exception as e:
            if show_errmsg:
                raise e

            return None, e

        else:
            # ----------------获取并设置编码开始-----------------
            # 在headers中获取编码
            content_type = r.headers.get('content-type', '').lower()
            charset = search(r'charset[=: ]*(.*)?[;]', content_type)

            if charset:
                r.encoding = charset.group(1)

            # 在headers中获取不到编码，且如果是网页
            elif content_type.replace(' ', '').startswith('text/html'):
                re_result = search(b'<meta.*?charset=[ \\\'"]*([^"\\\' />]+).*?>', r.content)

                if re_result:
                    charset = re_result.group(1).decode()
                else:
                    charset = r.apparent_encoding

                r.encoding = charset
            # ----------------获取并设置编码结束-----------------

            return r, 'Success'


class Mission(object):
    """任务对象"""

    def __init__(self, ID: int, data: dict):
        """初始化
        :param ID: 任务id
        :param data: 任务数据
        """
        self._id = ID
        self.data = data
        self.state = 'waiting'
        self.rate = 0
        self.info = '等待下载'
        self.result = None

        self.file_name = None
        self.path = None

    def __repr__(self) -> str:
        return f'{self.state} {self.info}'

    @property
    def id(self) -> int:
        return self._id


def _get_download_file_name(url, response) -> str:
    """从headers或url中获取文件名，如果获取不到，生成一个随机文件名
    :param url: 文件url
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
    if not file_name and os_PATH.basename(url):
        file_name = os_PATH.basename(url).split("?")[0]

    # 找不到则用时间和随机数生成文件名
    if not file_name:
        file_name = f'untitled_{time()}_{randint(0, 100)}'

    # 去除非法字符
    charset = charset or 'utf-8'
    return unquote(file_name, charset)


def _get_session(session: Union[Session, 'SessionOptions', 'MixPage', 'Drission']) -> Session:
    """获取Session对象                                      \n
    :param session: Session对象或包含Session信息的对象
    :return: Session对象
    """
    if not isinstance(session, Session):
        try:
            from DrissionPage import Drission, MixPage
            from DrissionPage.config import SessionOptions

            if isinstance(session, SessionOptions):
                session = Drission(driver_or_options=False, session_or_options=session).session
            elif isinstance(session, (Drission, MixPage)):
                session = session.session
            else:
                session = Drission(driver_or_options=False).session

        except ImportError:
            session = Session()

    return session
