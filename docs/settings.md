本节介绍`DownloadKit`对象相关设置。

## `使用方法`

使用`DownloadKit`对象的`set`属性，可调用各种设置项。

```python
from DownloadKit import DownloadKit

d = DownloadKit()
d.set.block_size('10m')  # 设置分块大小
```

---

## 运行设置

### `set.driver()`

此方法用于设置提供下载连接信息的页面或链接对象。

支持 DrissionPage 所有页面对象、`Session`对象、`SessionOptions`对象。

程序可从传入的对象中自动获取登录信息，如传入页面对象，还能自动设置`Referer`参数。

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`driver`|`Session`<br>`SessionOptions`<br>`ChromiumPage`<br>`SessionPage`<br>`ChromiumTab`<br>`WebPage`<br>`WebPageTab`|必填|用于提供连接信息的对象|

**返回：**`None`

---

### `set.goal_path()`

此方法用于设置文件保存路径。

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`goal_path`|`str`<br>`Path`|必填|文件保存路径|

**返回：**`None`

---

### `set.if_file_exists()`

此方法用于设置路径存在同名文件时的处理方式。

可选`'skip'`, `'rename'`, `'overwrite'`, `'add'`。

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`mode`|`str`|必填|处理方式字符串|

**返回：**`None`

---

### `set.if_file_exists.xxxx()`

这几个方法用于设置路径存在同名文件时的处理方式。

效果与`set.if_file_exists()`一致。

- `skip()`：跳过，不下载
- `rename()`：重命名，在原有文件名后加上`'_序号'`
- `overwrite()`：覆盖原有文件
- `add()`：在原有文件末尾追加内容

**示例：**

```python
from DownloadKit import DownloadKit

d = DownloadKit()
d.set.if_file_exists.skip()
```

---

### `set.roads()`

此方法用于设置可同时运行的线程数。

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`num`|`int`|必填|线程数量|

**返回：**`None`

---

### `set.retry()`

此方法用于设置连接失败时重试次数。

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`times`|`int`|必填|重试次数|

**返回：**`None`

---

### `set.interval()`

此方法用于设置连接失败时重试间隔。

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`seconds`|`float`|必填|连接失败时重试间隔（秒）|

**返回：**`None`

---

### `set.timeout()`

此方法用于设置连接超时时间。

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`seconds`|`float`|必填|超时时间（秒）|

**返回：**`None`

---

### `set.split()`

此方法用于设置大文件是否分块下载。

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`on_off`|`bool`|必填|`bool`代表开关|

**返回：**`None`

---

### `set.block_size()`

此方法用于设置设置分块大小。

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`size`|`str`<br>`int`|必填|单位为字节，可用'K'、'M'、'G'为单位，如`'50M'`|

**返回：**`None`

---

### `set.proxies()`

此方法用于设置代理地址及端口，例：'127.0.0.1:1080'。

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`http`|`str`|`None`|http 代理地址及端口|
|`https`|`str`|`None`|https 代理地址及端口|

**返回：**`None`

---

## 日志设置

日志设置方法在`set.log`属性中。

### `set.log_mode.xxxx()`

这几个方法用于设置路径存在同名文件时的处理策略。

- `skip()`：跳过，不下载
- `rename()`：重命名，在原有文件名后加上`'_序号'`
- `overwrite()`：覆盖原有文件
- `add()`：在原有文件末尾追加内容

**示例：**

```python
from DownloadKit import DownloadKit

d = DownloadKit()
d.set.if_file_exists.skip()
```