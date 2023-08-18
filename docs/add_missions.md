本节介绍如何添加下载任务。

## 创建任务

### 单线程任务

使用`download()`方法，可创建单线程阻塞式任务。

即使遇到大文件，`download()`也只有一个线程执行下载，不会分块。

该方法会在文件下载完成后才让程序继续往下运行。

**示例：**

```python
from DownloadKit import DowwnloadKit

d = DownloadKit()
url = 'https://gitee.com/static/images/logo-black.svg'

d.download(url)
```

---

### 多线程并发任务

使用`add()`方法，可添加并发任务。

`add()`方法返回`Mission`对象，可以用于任务管理。

**示例：**

```python
from DownloadKit import DowwnloadKit

d = DownloadKit()
url1 = 'https://gitee.com/static/images/logo-black.svg'
url2 = 'https://gitee.com/static/images/logo-black.svg'

m1 = d.add(url1)
m2 = d.add(url2)
```

---

### 多线程阻塞式任务

如果想使用多线程下载大文件，且需要在这个文件下载完再执行后面的语句，可以在`add()`后面使用`wait()`方法，可创建单线程阻塞式任务。

`wait()`方法有`show_msg`参数，可指定是否打印下载进度。

**示例：**

```python
from DownloadKit import DowwnloadKit

d = DownloadKit()
url = 'https://gitee.com/static/images/logo-black.svg'

d.add(url).wait(show_msg=False)
```

---

### post 方式

当`download()`或`add()`存在`data`或`json`参数时，会使用 post 方式进行连接。

不存在这两个参数时，用 get 方式连接。

**示例：**

```pyton
data = {'abc': 123}
d.download(url, data=data)  # 自动采用post方式
```

---

## 任务参数

`download()`和`add()`方法参数基本一致，有微小差别。

### `download()`

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`file_url`|`str`|必填|文件网址|
|`goal_path`|`str`<br>`Path`|`None`|保存路径，为`None`时保存到当前文件夹|
|`rename`|`str`|`None`|指定文件另存的名称，可不带后缀，程序会自动补充|
|`file_exists`|`str`|`None`|遇到同名文件时的处理方式，可选`'skip'`, `'overwrite'`, `'rename'`, `'add'`，默认跟随实例属性|
|`show_msg`|`bool`|`True`|是否打印下载信息和进度|
|`**kwargs`|`Any`|无|requests 的连接参数|

---

### `add()`

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`file_url`|`str`|必填|文件网址|
|`goal_path`|`str`<br>`Path`|`None`|保存路径，为`None`时保存到当前文件夹|
|`rename`|``str`|`None`|指定文件另存的名称，可不带后缀，程序会自动补充|
|`file_exists`|`str`|`None`|遇到同名文件时的处理方式，可选`'skip'`, `'overwrite'`, `'rename'`, `'add'`，默认跟随实例属性|
|`split`|`bool`|`None`|是否启用多线程分块下载，默认跟随实例属性|
|`**kwargs`|`Any`|无|requests 的连接参数|


---

### 连接参数

连接参数即`**kwargs`允许接收到参数，与 requests 的`get()`方法一致。

|参数名称|类型|说明|
|:---:|:---:|---|
|`timeout`|`float`|连接超时时间|
|`params`|`dict`|查询参数字典|
|`headers`|`dict`|headers|
|`cookies`|`Any`|cookies|
|`data`|`Any`|data 数据|
|`json`|`Any`|json 数据|
|`files`|`Any`|文件数据|
|`auth`|`Tuple[str, str]`<br>`HTTPBasicAuth`|认证元组或对象|
|`allow_redirects`|`bool`|是否允许自动跳转|
|`proxies`|`dict`|代理 ip|
|`hooks`|`dict`|回调方法|
|`verify`|`bool`|是否验证SSL证书|
|`cert`|`str`<br>`Tuple[str, str]`|SSL客户端证书|