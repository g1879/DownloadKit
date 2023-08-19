# -*- coding:utf-8 -*-
from setuptools import setup, find_packages

with open("README.md", "r", encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name="DownloadKit",
    version="1.0.2",
    author="g1879",
    author_email="g1879@qq.com",
    description="一个简洁易用的多线程文件下载工具。",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="BSD",
    keywords="DownloadKit",
    url="https://gitee.com/g1879/DownloadKit",
    include_package_data=True,
    packages=find_packages(),
    install_requires=[
        "requests",
        "DataRecorder>=3.4.2"
    ],
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
    python_requires='>=3.6'
)
