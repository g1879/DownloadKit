## ✅️️ `DownloadKit`对象方法

### 📌 `download()`

此方法用于单线程阻塞式下载一个文件。

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`file_url`|`str`|必填|文件网址|
|`goal_path`|`str`<br>`Path`|`None`|保存路径，为`None`时保存到当前文件夹|
|`rename`|`str`|`None`|指定文件另存的名称，可不带后缀，程序会自动补充|
|`file_exists`|`str`|`None`|遇到同名文件时的处理方式，可选`'skip'`, `'overwrite'`, `'rename'`, `'add'`，默认跟随实例属性|
|`show_msg`|`bool`|`True`|是否打印下载信息和进度|
|`**kwargs`|`Any`|无|requests 的连接参数|

连接参数`**kwargs`与 requests 的`get()`方法一致。

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

|返回类型|说明|
|:---:|---|
|`tuple`|格式：(任务结果, 任务信息)|

任务结果有如下几种：

- `'success'`：下载成功
- `'skipped'`：已跳过
- `'canceled'`：被取消
- `False`：任务失败

如果下载成功，任务信息返回文件路径，如果失败，返回失败原因。

---

### 📌 `add()`

此方法添加一个并发任务。

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`file_url`|`str`|必填|文件网址|
|`goal_path`|`str`<br>`Path`|`None`|保存路径，为`None`时保存到当前文件夹|
|`rename`|``str`|`None`|指定文件另存的名称，可不带后缀，程序会自动补充|
|`file_exists`|`str`|`None`|遇到同名文件时的处理方式，可选`'skip'`, `'overwrite'`, `'rename'`, `'add'`，默认跟随实例属性|
|`split`|`bool`|`None`|当前任务是否启用多线程分块下载，默认跟随实例属性|
|`**kwargs`|`Any`|无|requests 的连接参数|

`**kwargs`参数与`download()`一致，见上文。

|返回类型|说明|
|:---:|---|
|`Mission`|任务对象，可用于观察任务状态、取消任务|

---

### 📌 `wait()`

此方法用于等待所有或指定任务完成。

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`mission`|`Mission`<br>`int`|`None`|任务对象或任务 id，为`None`时等待所有任务结束|
|`show`|`bool`|`False`|是否显示进度|
|`timeout`|`float`<br>`None`|`None`|超时时间，`None`或`0`不限时|

---

### 📌 `cancel()`

此方法用于取消所有等待中或执行中的任务。

**参数：** 无

**返回：**`None`

---

### 📌 `get_mission()`

此方法根据id值获取一个任务。

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`mission_or_id`|`Mission`<br>`int`|必填|任务或任务 id|

|返回类型|说明|
|:---:|---|
|`Mission`|任务对象|
|`None`|没有找到该任务|

---

### 📌 `get_failed_missions()`

此方法返回失败任务列表。

**参数：** 无

|返回类型|说明|
|:---:|---|
|`List[Mission]`|任务对象组成的列表|

---

## ✅️️`DownloadKit`属性

### 📌 `goal_path`

此属性返回文件默认保存文件夹路径，默认程序当前路径。

**类型：** `str`

---

### 📌 `file_exists`

此属性返回遇到同名文件时的处理方式，有以下几种：`'skip'`, `'overwrite'`, `'rename'`, `'add'`。

默认`'rename'`。

**类型：** `str`

---

### 📌 `split`

此属性返回大文件是否分块下载，默认`True`。

**类型：** `bool`

---

### 📌 `set`

此属性返回用于设置`DownloadKit`对象的设置对象。

**类型：** `Setter`

---

### 📌 `timeout`

此属性返回连接超时时间，默认 20 秒，如果驱动是`DrissionPage`的页面对象，使用页面对象的`timeout`属性。

**类型：** `float`

---

### 📌 `retry`

此属性返回连接失败时重试次数，默认`3`。

**类型：** `int`

---

### 📌 `interval`

此属性返回连接失败时重试间隔，默认 5 次。

**类型：** `int`

---

### 📌 `is_running`

此属性返回是否有线程还在运行。

**类型：** `bool`

---

### 📌 `missions`

此属性返回所有任务对象。

**类型：** `bool`

---

### 📌 `waiting_list`

此属性返回返回等待执行的任务队列。

**类型：** `List[Mission]`

---

































