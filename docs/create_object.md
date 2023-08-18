## 创建`DownloadKit`对象

|     初始化参数     |                                                       类型                                                       |    默认值     | 说明                                                          |
|:-------------:|:--------------------------------------------------------------------------------------------------------------:|:----------:|-------------------------------------------------------------|
|  `goal_path`  |                                                `str`<br>`Path`                                                 |   `None`   | 文件保存路径                                                      |
|    `roads`    |                                                     `int`                                                      |    `10`    | 可同时运行的线程数                                                   |
|   `driver`    | `Session`<br>`SessionOptions`<br>`ChromiumPage`<br>`SessionPage`<br>`ChromiumTab`<br>`WebPage`<br>`WebPageTab` |   `None`   | 用于提供下载连接信息的页面或链接对象                                          |
| `file_exists` |                                                     `str`                                                      | `'renmae'` | 有同名文件名时的处理方式，可选`'skip'`, `'overwrite'`, `'rename'`, `'add'` |

---

## 示例

### 直接创建

```python
from DownloadKit import DownloadKit

d = DownloadKit()
```

---

### 接收`Session`对象

```python
from requests import Session
from DownloadKit import DownloadKit

session = Session()
d = DownloadKit(session=session)
```

---

### 接收`SessionOptions`对象

```python
from DrissionPage import SessionOptions
from DownloadKit import DownloadKit

so = SessionOptions()
d = DownloadKit(session=so)
```

---

### 接收页面对象

```python
from DrissionPage import ChromiumPage
from DownloadKit import DownloadKit

p = ChromiumPage()
d = DownloadKit(session=p)
```