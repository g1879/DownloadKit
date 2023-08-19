---
hide:
  - navigation
---

## 💬 简介

DownloadKit 是一个基于 python 的简洁易用的多线程文件下载工具。
使用简单，功能强大。

当前版本：v1.0.2

---

## 💖 特性

- 多线程，可同时下载多个文件
- 大文件自动分块用多线程下载
- 自动任务调度，简易的任务添加方式
- 可使用已有`Session`对象，便于保持登录状态
- 与 DrissionPage 良好兼容
- 自动创建目标路径
- 自动去除路径中的非法字符
- 自动处理文件名冲突
- 可对现有文件追加内容
- 连接失败自动重试

---

## 💥 简单示例

```python
from DownloadKit import DownloadKit

# 创建下载器对象
d = DownloadKit(r'.\files')

# 添加多个任务
url1 = 'https://gitee.com/static/images/logo.svg?t=158106664'
url2 = 'https://www.baidu.com/img/PCfb_5bf082d29588c07f842ccde3f97243ea.png'

d.download(url1)
d.download(url2)
```

---

## ☕ 请我喝咖啡

如果本项目对您有所帮助，不妨请作者我喝杯咖啡 ：）

![](http://g1879.gitee.io/drissionpagedocs/imgs/code.jpg)