---
hide:
  - navigation
---

## v1.0.2

- 支持`DrissionPage` v3.2.31 版
- 修改设置项 api，`set_xxxx()`改为`set.xxxx()`形式
- `__init__()`方法的`session`用`driver`代替，但保留向后兼容
- 可更准确显示下载进度
- `Task`增加下载进度属性
- 处理已存在文件的情况增加`add`模式
- 增加日志设置
- 优化程序逻辑，修复一些问题

---

## v0.5.3

- 支持`DrissionPage` v3.2.0 版
- 增加`missions`属性

---

## v0.4.4

- 适配`DrissionPage` v3.1.0 版
- 增加`split`全局  设置

---

## v0.4.1

- 支持`DrissionPage` v3.0 版
- 增加`set_log()`、`set_print()`和`set_proxies()`
- 改用`ByteRecorder`保存数据
- 新增`MissionData`类
- 大量修改结构，优化逻辑

---

## v0.3.5

- 新增`MissionData`类
- `add()`方法删除`session`参数
- `__init__()`方法删除`timeout`参数
- 优化`timeout`、`retry`、`interval`属性逻辑

---

## v0.3.3

- `referer`参数可从传入的页面对象获取
- 大量优化

---

## v0.3.0

- 完成主要功能
- 完善逻辑

---

## v0.1.0

- 完成基本框架
































