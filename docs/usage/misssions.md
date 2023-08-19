本节介绍下载任务的管理。

`add()`方法会返回一个`Mission`对象，该对象可用于查看任务信息和管理任务。

## ✅️️ 任务进度

### 📌 `rate`

该属性返回任务完成的百分比。

**类型：**`float`

**示例：**

```python
d = DownloadKit()
m = d.add(url)

print(m.rate)
```

---

### 📌 等待单个任务结束

`Mission`对象的`wait()`方法可等待该任务结束。

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`show`|`bool`|`True`|是否打印下载信息|
|`timeout`|`float`|`0`|超时时间，`0`表示不限时|

|返回类型|说明|
|`tuple`|任务结果和信息组成的`tuple`，格式：(任务结果, 任务信息)|

**示例：**

```python
d = DownloadKit()
m = d.add(url)

m.wait()
```

---

### 📌 等待所有任务结束

`DownloadKit`对象的`wait()`方法，可等待所有任务结束。

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`mission`|`Mission`<br>`int`|`None`|任务对象或任务 id，为`None`时等待所有任务结束|
|`show`|`bool`|`False`|是否显示进度|
|`timeout`|`float`<br>`None`|`None`|超时时间，`None`或`0`不限时|

**示例：**

```python
d = DownloadKit()
d.add(url1)
d.add(url2)

d.wait()
```

---

### 📌 取消任务

`cancel()`用于中途取消任务。

**参数：** 无

**返回：**`None`

---

### 📌 删除已下载文件

`del_file()`用于删除任务已下载的文件。

**参数：** 无

**返回：**`None`

---

## ✅️️ 任务信息

### 📌 任务状态

`state`属性返回任务状态，有以下三种：

- `'waiting'`：等待开始
- `'running'`：运行中
- `'done'`：已结束

任务状态不能看出任务是否成功，只能显示任务是否在运行。

---

### 📌 任务结果

`result`属性返回任务结果，有以下几种：

- `'success'`：下载成功
- `'skipped'`：跳过，存在同名文件，且设置为跳过时
- `'canceled'`：被取消
- `False`：任务失败
- `None`：未知，任务还没结束

---

### 📌 任务信息

`info`属性返回任务信息，在任务不同阶段，会返回不同信息。

`info`是对当前状态的文字解释，如任务失败时，会返回失败原因，成功时会返回文件保存路径。

---

## ✅️️ 获取任务对象

### 📌 获取所有任务对象

`DownloadKit`对象的`missions`属性以`liist`方式返回所有任务对象。

**示例：**

```python
d = DownloadKit()
d.add(url)
print(d.missions)
```

---

### 📌 查找任务

`DownloadKit`对象的`get_mission()`方法可根据任务 id 获取任务对象。

|参数名称|类型|默认值|说明|
|:---:|:---:|:---:|---|
|`mission_or_id`|`Mission`<br>`int`|必填|任务或任务 id|

|返回类型|说明|
|:---:|---|
|`Mission`|任务对象|
|`None`|没有找到该任务|

---

### 📌 获取失败的任务

`DownloadKit`对象的`get_failed_missions()`方法可以`list`方式返回失败的任务。

**参数：** 无

|返回类型|说明|
|:---:|---|
|`List[Mission]`|任务对象组成的列表|

---

## ✅️️ `Mission`对象的属性

### 📌 `id`

此属性返回任务 id。

**类型：**`int`

---

### 📌 `data`

此属性返回任务使用的数据，即创建任务时输入的参数。

**类型：**`MissionData`

---

### 📌 `state`

此属性返回任务状态，有三种：`'waiting'`、`'running'`、`'done'`。

**类型：**`str`

---

### 📌 `result`

此属性返回任务结果，有以下几种：`'success'`、`'skipped'`、`'canceled'`、`False`、`None`

**类型：**`str`

---

### 📌 `info`

此属性返回任务描述信息。

**类型：**`str`

---

### 📌 `is_done`

此属性返回任务是否已完成。

**类型：**`bool`

---

### 📌 `size`

此属性返回文件大小。

**类型：**`int`或`None`

---

### 📌 `tasks`

此属性以`list`方式返回所有子任务

**类型：**`List[Task]`

---

### 📌 `tasks_count`

此属性返回子任务数量。

**类型：**`int`

---

### 📌 `done_tasks_count`

此属性返回已完成的子任务数量。

**类型：**`int`

---

### 📌 `file_name`

此属性返回文件名。

**类型：**`str`或`None`

---

### 📌 `method`

此属性返回连接方式，`'get'`或`'post'`。

**类型：**`str`

---

### 📌 `path`

此属性返回文件保存路径。

**类型：**`str`

---

### 📌 `rate`

此属性以百分比方式返回下载进度。

**类型：**`float`
