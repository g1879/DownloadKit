# -*- coding:utf-8 -*-
from os import path as os_PATH, sep
from pathlib import Path
from random import randint
from re import search, sub
from collections import deque
from threading import Thread
from time import time, sleep, perf_counter
from typing import Union
from urllib.parse import quote, urlparse, unquote

from DrissionPage import Drission
from DrissionPage.config import SessionOptions
from requests import Session

from .common import make_valid_name, get_usable_path


class DownloadKit:
    def __init__(self,
                 goal_path: str = None,
                 size: int = 3,
                 session_or_options: Union[Session, SessionOptions] = None,
                 timeout: float = None,
                 file_exists: str = 'rename'):
        self.size = size
        self.missions = deque()
        self.threads = {i: None for i in range(self._size)}
        self.任务管理线程 = None
        self.线程管理线程 = None
        self.信息显示线程 = None

        self.goal_path = goal_path
        self.retry: int = 3
        self.interval: int = 5
        self.timeout: float = timeout if timeout is not None else 20
        self.file_exists: str = file_exists

        if isinstance(session_or_options, Session):
            self.session = session_or_options
        elif isinstance(session_or_options, SessionOptions):
            self.session = Drission(driver_or_options=False, session_or_options=session_or_options).session
        else:
            self.session = Drission(driver_or_options=False).session

        self.show()

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, size):
        # todo: 改成可修改字典大小
        self._size = size

    @property
    def file_exists(self):
        return self._file_exists

    @file_exists.setter
    def file_exists(self, mode: str):
        if mode not in ('skip', 'overwrite', 'rename'):
            raise ValueError("file_exists参数只能传入'skip', 'overwrite', 'rename'")
        self._file_exists = mode

    def show(self):
        if self.信息显示线程 is None or not self.信息显示线程.is_alive():
            self.信息显示线程 = Thread(target=self._show)
            self.信息显示线程.start()

    def _show(self):
        t1 = perf_counter()
        while self.is_running() or perf_counter() - t1 < 2:
            mis = [f"{i['file_url']}\n" for i in self.missions]
            txt = [f'{k} {v["info"]} {v["data"]["file_url"]}\n' if v is not None else f'{k} None\n' for k, v in self.threads.items()]
            print(f"{''.join(mis)}\n{''.join(txt)}\n", flush=False)
            sleep(.5)
        # print('显示进程停止', flush=False)

    def go(self):
        if self.任务管理线程 is None or not self.任务管理线程.is_alive():
            print('任务线程启动', flush=False)
            self.任务管理线程 = Thread(target=self._missions_manage)
            self.任务管理线程.start()

        if self.线程管理线程 is None or not self.线程管理线程.is_alive():
            print('管理线程启动', flush=False)
            self.线程管理线程 = Thread(target=self._threads_manage)
            self.线程管理线程.start()

    def add(self,
            file_url: str,
            goal_path: str = None,
            session: Session = None,
            rename: str = None,
            file_exists: str = None,
            post_data: Union[str, dict] = None,
            retry: int = None,
            interval: float = None,
            **kwargs):
        data = {'file_url': file_url,
                'goal_path': goal_path or self.goal_path,
                'session': session or self.session,
                'rename': rename,
                'file_exists': file_exists or self.file_exists,
                'post_data': post_data,
                'retry': retry if retry is not None else self.retry,
                'interval': interval if interval is not None else self.interval,
                'kwargs': kwargs}
        self.missions.append(data)
        self.go()

    def _missions_manage(self):
        t1 = perf_counter()
        while self.missions or perf_counter() - t1 < 2:
            if self.missions:
                num = self._get_usable_thread()
                msg = {'thread': None,
                       'result': None,
                       'info': None,
                       'close': False,
                       'data': self.missions.popleft()}
                thread = Thread(target=self._download, args=(msg,))
                msg['thread'] = thread
                thread.start()
                self.threads[num] = msg

        print('任务管理线程停止', flush=False)

    def _get_usable_thread(self):
        """获取可用线程"""
        while True:
            for k, v in self.threads.items():
                if v is None:
                    return k

    def _threads_manage(self):
        """负责把完成的线程清除出列表"""
        t1 = perf_counter()
        while True:
            for k, v in self.threads.items():
                if isinstance(v, dict) and not v['thread'].is_alive():
                    # TODO: 保存结果
                    # print(v['info'])
                    self.threads[k] = None

            if perf_counter() - t1 > 2 and not self.is_running():
                break

        print('管理线程停止', flush=False)

    def is_running(self):
        """检查是否有线程还在运行中"""
        return [k for k, v in self.threads.items() if v is not None]

    def _download(self, args: dict):
        """下载一个文件"""
        file_url = args['data']['file_url']
        goal_path = args['data']['goal_path']
        session = args['data']['session']
        rename = args['data']['rename']
        file_exists = args['data']['file_exists']
        post_data = args['data']['post_data']
        kwargs = args['data']['kwargs']
        retry_times = args['data']['retry'] if args['data']['retry'] is not None else self.retry
        retry_interval = args['data']['interval'] if args['data']['interval'] is not None else self.interval

        def set_result(res, info):
            args['result'] = res
            args['info'] = info

        if file_exists == 'skip' and Path(f'{goal_path}{sep}{rename}').exists():
            set_result(None, '已跳过')
            return

        def do() -> tuple:
            kwargs['stream'] = True
            if 'timeout' not in kwargs:
                kwargs['timeout'] = 20

            # 生成临时的response
            mode = 'post' if post_data is not None else 'get'
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
            goal_Path = Path(goal_path)
            skip = False

            # 按windows规则去除路径中的非法字符
            goal = goal_Path.anchor + sub(r'[*:|<>?"]', '', goal_path.lstrip(goal_Path.anchor)).strip()
            Path(goal).absolute().mkdir(parents=True, exist_ok=True)
            full_path = Path(f'{goal}{sep}{full_name}')

            if full_path.exists():
                if file_exists == 'rename':
                    full_path = get_usable_path(f'{goal}{sep}{full_name}')
                    # full_name = full_path.name

                elif file_exists == 'skip':
                    skip = True

                elif file_exists == 'overwrite':
                    pass

            # -------------------开始下载-------------------
            if skip:
                return None, '已跳过'

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
                                args['info'] = '{:.0%} '.format(rate)

            except Exception as e:
                # raise
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

            # -------------------显示并返回值-------------------
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
        """生成response对象                     \n
        :param url: 目标url
        :param mode: 'get', 'post' 中选择
        :param data: post方式要提交的数据
        :param show_errmsg: 是否显示和抛出异常
        :param kwargs: 其它参数
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
