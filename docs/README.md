---

## `DownloadKit`属性

- goal_path：文件保存路径，可赋值
- roads：可同时允许的线程数，没有任务运行时可赋值
- block_size：大文件分块大小，默认 20MB
- retry：下载失败重试次数，可赋值
- interval：下载失败重试间隔，可赋值
- timeout：连接超时时间，可赋值
- file_exists：遇到同名文件时的处理方式，可赋值，可选`'skip'`、`'overwrite'`、`'rename'`
- session：用于连接的`Session`对象
- waiting_list：等待下载的队列
- is_running：返回是否有线程还在运行

**`file_exists`属性说明：**

- `skip`：跳过该文件
- `overwrite`：覆盖该文件
- `rename`：以在后面添加序号的方式给新文件重命名

**`block_size`属性说明：**

该属性可接收`int`和`str`形式，接收`int`时以字节为单位；  
接收`str`时格式有：`'10b'`、`'10k'`、`'10m'`、`'10g'`四种。不区分大小写。

## 下载设置

可使用以下属性进行配置：

```python
d = DownloadKit()

# 设置线程数，只能在没有任务在运行的时候进行
d.roads = 20

# 大文件分块大小，默认 20MB
d.block_size = '50M'

# 设置保存路径，设置后每个任务会使用这个路径，也可添加任务时单独设置
d.goal_path = r'D:\tmp'

# 设置重试次数，初始为3
d.retry = 5

# 设置失败重试间隔，初始为5
d.interval = 2

# 设置存在文件名冲突时的处理方式，可选 'skip', 'overwrite', 'rename'
d.file_exists = 'skip'
```

## 添加下载任务

使用`add()`方法添加下载任务。

参数：

- file_url：文件网址
- goal_path：保存路径
- rename：重命名的文件名
- file_exists：遇到同名文件时的处理方式，可选`'skip'`,`'overwrite'`,`'rename'`，默认跟随实例属性
- split：是否允许多线分块下载
- kwargs：连接参数，与 requests 的参数使用方法一致

返回：`Mission`对象

使用`add()`方法返回的`Mission`对象可便于后续查看任务状态和进度。

```python
from DownloadKit import DownloadKit

d = DownloadKit()

url = 'https://www.baidu.com/img/PCfb_5bf082d29588c07f842ccde3f97243ea.png'
mission = d.add(url)
```

## 添加连接参数

可以给`Session`对象添加整体参数，或每个任务设置独立的参数。

**整体参数：**

```python
from requests import Session
from DownloadKit import DownloadKit

session = Session()
session.headers = {'xxxx': 'xxxx'}
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

## 观察下载过程

`show()`方法可实时显示所有线程下载过程。

**注意：** 若使用 pyCharm 运行，须在运行配置里勾选“模拟输出控制台中的终端”才能正常显示输出。

参数：

- asyn：是否异步进行
- keep：是否保持显示，为`True`时即使任务全部结束，也会保持显示，可按回车结束显示

返回：None

```python
d = DownloadKit(r'.\files', size=3)
url = 'https://example.com/file/abc.zip'
mission = d.add(url)
d.show()
```

输出：

```shell
等待任务数：0
线程0：M1 D:\files\abc.zip
线程1：M1 D:\files\abc.zip
线程2：空闲
```

## 等待任务结束

有时须要等待任务结束，以便获取结果，可用`DownloadKit`对象或`Mission`对象的`wait()`方法。  
当传入任务时，等待该任务结束并返回结果。不传入参数时等待所有任务结束，与`show()`方法一致。

`DownloadKit`对象的`wait()`方法：

参数：

- mission：任务对象或任务`id`，为`None`时等待所有任务结束
- show：是否显示进度

返回：

- 指定任务时，返回任务结果和信息组成的两位 tuple。其中任务结果`'success'`表示成功，`False`表示失败，`'skip'`
  表示跳过。成功和跳过时信息为文件绝对路径，失败时信息为失败原因
- 不指定任务时，返回`None`

`Mission`对象的`wait()`方法

参数：

- show：是否显示进度

返回：返回任务结果和信息组成的两位 tuple。其中任务结果`'success'`表示成功，`False`表示失败，`'skip'`
表示跳过。成功和跳过时信息为文件绝对路径，失败时信息为失败原因

```python
d = DownloadKit(r'.\files')
url = 'https://www.baidu.com/img/PCfb_5bf082d29588c07f842ccde3f97243ea.png'
mission = d.add(url)
d.wait(mission)
# 或
mission.wait()
```

输出：

```shell
url：https://www.baidu.com/img/PCfb_5bf082d29588c07f842ccde3f97243ea.png
文件名：PCfb_5bf082d29588c07f842ccde3f97243ea_4.png
目标路径：D:\files
100% 下载完成 D:\files\PCfb_5bf082d29588c07f842ccde3f97243ea_4.png
```

**Tips：** `Mission`对象也有`wait()`方法，作用与上述的一致。

```python
mission = d.add(url)
mission.wait()
```

## 获取某个任务结果

`Mission`对象用于管理下载任务，可查看该任务执行情况。

**`Mission`对象属性：**

- id：任务 id
- file_name：要保存的文件名
- path：要保存的路径，为Path对象
- data：任务数据
- state：任务状态，有`'waiting'`、`'running'`、`'done'`三种
- rate：任务进度，以百分比显示
- info：任务信息，成功会返回文件绝对路径，失败会显示原因
- result：任务结果，`'success'`表示成功，`False`表示失败，`'skip'`表示跳过

```python
mission = page.download.add(url)
print(mission.state)
```

输出：

```python
running
```

## 取消某个正在下载的任务

使用`Mission`对象的`cancel()`方法，取消会删除该任务已下载的文件。

```python
mission.cancel()
```

## 获取失败任务

使用`DownloadKit`对象的`get_failed_missions()`方法，可获取下载失败的任务。可以把失败的任务保存到文件，支持 txt、xlsx、txt、csv
四种格式。

参数：

- save_to：失败任务保存到文件的路径，默认为`None`表示不保存

返回：`Mission`对象组成的列表