#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_ico.py — 从 macOS 的 AppIcon.icns 里取出既有 PNG，重新封装成 Windows 的 .ico。

不重绘、不依赖 PIL：icns 里本来就按尺寸存着 PNG（ic08=256 / ic07=128 / ic12=64 / ic11=32），
直接搬出来拼进 ICO 容器即可（ICO 从 Vista 起支持内嵌 PNG 数据，无需再转 BMP）。

用法（在 macOS 上）：
    python3 windows/tools/make_ico.py
产物：
    windows/AquaMark.ico
可选：
    系统装有 sips 时会额外补 48 / 16 两个尺寸，让任务栏与资源管理器列表更锐利。
"""
import io
import os
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ICNS = os.path.join(ROOT, "macos", "AppIcon.icns")
OUT = os.path.join(ROOT, "windows", "AquaMark.ico")

# icns 的类型标签 -> 真实像素边长
SIZES = {"ic07": 128, "ic08": 256, "ic09": 512, "ic10": 1024,
         "ic11": 32, "ic12": 64, "ic13": 256, "ic14": 512}


def read_icns(path):
    """icns = 8 字节头 + 若干 (type, len, payload) 块。返回 {size: png_bytes}。"""
    data = open(path, "rb").read()
    total = struct.unpack(">I", data[4:8])[0]
    out, i = {}, 8
    while i + 8 <= total:
        tag = data[i:i + 4].decode("latin-1")
        length = struct.unpack(">I", data[i + 4:i + 8])[0]
        payload = data[i + 8:i + length]
        i += length
        if tag in SIZES and payload[:4] == b"\x89PNG":
            out.setdefault(SIZES[tag], payload)
    return out


def build_ico(entries):
    """entries: [(size, png_bytes)] -> ICO 二进制。"""
    n = len(entries)
    header = struct.pack("<HHH", 0, 1, n)
    offset = 6 + 16 * n
    dirs, blobs = [], b""
    for size, png in entries:
        # bWidth/bHeight: 256 在单字节里写不下，按规范填 0
        dirs.append(struct.pack("<BBBBHHII",
                                size if size < 256 else 0,
                                size if size < 256 else 0,
                                0, 0, 1, 32, len(png), offset))
        blobs += png
        offset += len(png)
    return header + b"".join(dirs) + blobs


def main():
    if not os.path.exists(ICNS):
        sys.exit("找不到 %s" % ICNS)
    pool = read_icns(ICNS)
    picks = [256, 128, 64, 32]
    entries = [(s, pool[s]) for s in picks if s in pool]

    # 有 sips（macOS 自带）时补两个 Windows 常用尺寸
    try:
        base = pool.get(256) or pool.get(512) or pool.get(1024)
        src = os.path.join(os.path.dirname(OUT), ".tmp-src.png")
        open(src, "wb").write(base)
        for want in (48, 16):
            if want in pool:
                continue
            tmp = os.path.join(os.path.dirname(OUT), ".tmp-%d.png" % want)
            subprocess.run(["sips", "-Z", str(want), "-s", "format", "png", src, "--out", tmp],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            entries.append((want, open(tmp, "rb").read()))
            os.remove(tmp)
        os.remove(src)
    except Exception:
        pass  # 没有 sips 也能用，只是少了两个备选尺寸

    if not entries:
        sys.exit("icns 里没有可用的 PNG 条目")

    blob = build_ico(entries)
    open(OUT, "wb").write(blob)
    print("已生成 %s（%d 字节，尺寸：%s）" % (OUT, len(blob), ", ".join(str(s) for s, _ in entries)))


if __name__ == "__main__":
    main()
