# 简介

DownloadKit 是一个基于 python 的简洁易用的多线程文件下载工具。   
希望做得足够简单，只要不断往里添加下载任务，它会按顺序自行下载完成。

# 特性

- 多线程，可同时下载多个文件
- 自动任务调度，简易的任务添加方式
- 可使用已有`Session`对象，便于保持登录状态
- 自动创建目标路径
- 自动去除路径中的非法字符
- 自动处理文件名冲突
- 任务失败自动重试

# 安装

```shell
pip install DownloadKit
```

# 导入

```python
from DownloadKit import DownloadKit
```

# 简单示例

```python
from DownloadKit import DownloadKit

# 创建下载器对象
d = DownloadKit(r'.\files')

# 添加多个任务
url1 = 'https://gitee.com/static/images/logo.svg?t=158106664'
url2 = 'https://www.baidu.com/img/PCfb_5bf082d29588c07f842ccde3f97243ea.png'

d.add(url1)
d.add(url2)
```

# 使用方法

## 创建`DownloadKit`对象

初始化参数：

- goal_path：文件保存路径，默认当前路径
- size：可同时运行的线程数
- session：使用的`Session`对象，或配置对象等
- timeout：连接超时时间
- file_exists：有同名文件名时的处理方式，可选`'skip'`,`'overwrite'`,`'rename'`

**session 参数说明：**

该参数可接收一个现成的`Session`对象，也可以接收`SessionOptions`、`MixPage`、`Drission`对象，生成或使用其中的`Session`对象。 若不传入以上对象，程序会自行生成一个。如果当前环境安装了
DrissionPage，程序会读取其 ini 配置文件生成，如果没有，则生成一个空`Session`对象。

> `SessionOptions`、`MixPage`、`Drission`对象用法见： [DrissionPage]([DrissionPage (gitee.io)](http://g1879.gitee.io/drissionpage/))

直接创建：

```python
d = DownloadKit()
```

接收`Session`对象

```python
from requests import Session

session = Session()
d = DownloadKit(session=session)
```

接收`SessionOptions`对象

```python
from DrissionPage.config import SessionOptions

so = SessionOptions()
d = DownloadKit(session=so)
```

接收`MixPage`对象

```python
from DrissionPage import MixPage

page = MixPage('s')
d = DownloadKit(session=page)
```

接收`Drission`对象

```python
from DrissionPage import MixPage

page = MixPage('s')
d = DownloadKit(session=page.drission)
```

## `DownloadKit`属性

- goal_path：文件保存路径，可赋值
- retry：下载失败重试次数，可赋值
- interval：下载失败重试间隔，可赋值
- timeout：连接超时时间，可赋值
- file_exists：遇到同名文件时的处理方式，可赋值，可选`'skip'`、`'overwrite'`、`'rename'`
- session：用于连接的`Session`对象
- waiting_list：等待下载的队列
- is_running()：返回是否有线程还在运行

**`file_exists`属性说明：**

- `skip`：跳过该文件
- `overwrite`：覆盖该文件
- `rename`：以在后面添加序号的方式给新文件重命名

## 添加下载任务

使用`add()`方法添加下载任务。

参数：

- file_url：文件网址
- goal_path：保存路径
- session：用于下载的Session对象，默认使用实例属性的
- rename：重命名的文件名
- file_exists：遇到同名文件时的处理方式，可选`'skip'`,`'overwrite'`,`'rename'`，默认跟随实例属性
- post_data：post 方式使用的数据
- retry：重试次数，默认跟随实例属性
- interval：重试间隔，默认跟随实例属性
- kwargs：连接参数，与 requests 的参数使用方法一致

返回：`Mission`对象

使用`add()`方法返回的`Mission`对象可便于后续查看任务状态和进度。

```python
from DownloadKit import DownloadKit

d = DownloadKit()

url = 'https://www.baidu.com/img/PCfb_5bf082d29588c07f842ccde3f97243ea.png'
mission = d.add(url)
```

## 添加任务参数

可以给`Session`对象添加整体参数，或每个任务设置独立的参数。

**整体参数：**

```python
from requests import Session
from DownloadKit import DownloadKit

session = Session()
session.headers={xxxx: xxxx}
d = DownloadKit(session=session)
```

更简便的方法是使用`SessionOptions`。该对象可使用保存在配置文件里的参数，免得每次在代码里设置复杂的`headers`
等参数，方便易用。详见：[DrissionPage]([🔧 Session 启动配置 (gitee.io)](http://g1879.gitee.io/drissionpage/#/使用方法\启动配置\Session启动配置))

```python
from DrissionPage.config import SessionOptions
from DownloadKit import DownloadKit

so = SessionOptions().set_proxies({'http': 'http://127.0.0.1'})
d = DownloadKit(session=so)
```

**任务独立设置参数：**

```python
from DownloadKit import DownloadKit

d = DownloadKit()

url = 'https://www.baidu.com/img/PCfb_5bf082d29588c07f842ccde3f97243ea.png'
proxies = {'http': 'http://127.0.0.1'}
d.add(url, proxies=proxies)
```

## 任务连接方式

任务可以用 get 或 post 方式，默认使用 get 方式，添加任务时，传入`data`或`json`参数即可使用 post 方式。

```python
url = 'https://www.baidu.com/img/PCfb_5bf082d29588c07f842ccde3f97243ea.png'

# 使用 get 方式
d.add(url)

# 使用 post 方式
data = {'xxx': 'xxx'}
d.add(url, json=data)
# 或
d.add(url, data=data)
```

**Tips：** `json`参数没有显式写在参数里，但直接调用即可。

## 等待任务结束

有时须要等待任务结束，以便获取结果，可用`wait()`方法。

参数：

- mission：任务对象或任务 id
- show：是否显示进度

返回：任务结果和信息组成的两位 tuple。`True`表示成功，`False`表示失败，`None`表示跳过。

```python
d = DownloadKit(r'.\files')
url = 'https://www.baidu.com/img/PCfb_5bf082d29588c07f842ccde3f97243ea.png'
mission = d.add(url1)
d.wait(mission)
```

输出：

```shell
url：https://www.baidu.com/img/PCfb_5bf082d29588c07f842ccde3f97243ea.png
文件名：PCfb_5bf082d29588c07f842ccde3f97243ea_4.png
目标路径：D:\files
100% 下载完成 D:\files\PCfb_5bf082d29588c07f842ccde3f97243ea_4.png
```

## 观察下载过程

`show()`方法可实时显示所有线程下载过程，直到所有任务结束，但中途不能退出。

```python
d = DownloadKit(r'.\files', size=3)
url = 'https://example.com/file/abc.zip'
mission = d.add(url1)
d.wait(mission)
```

输出：

```shell
线程0：97.41% abc.zip D:\files
线程1：None None None
线程2：None None None
```

**注意：** 若使用 pyCharm 运行，须在运行配置里勾选“模拟输出控制台中的终端”才能正常显示输出。

## `Mission`对象

`Mission`对象用于管理下载任务。

属性：

- id：任务 id
- data：任务使用的参数，与`add()`方法参数一致
- state：任务状态，有`'waiting'`、`'running'`、`'done'`三种
- rate：下载进度（百分比）
- info：任务信息
- result：任务结果，`True`表示成功，`False`表示失败，`None`表示跳过
- file_name：任务文件名
- path：保存路径