#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_windows_variant.py — 从根目录的 AquaMark.html（Mac 唯一真源）生成 Windows 版本。

设计原则：Mac 那份文件一个字节都不动；Windows 版是「同一份源码 + 一组补丁」的产物，
随时可以随着 Mac 端的改进重新生成。每处替换都带出现次数校验，
源码日后有变动时会直接报错退出，而不是悄悄生成一个残缺的页面。

用法：
    python3 windows/tools/make_windows_variant.py
产物：
    windows/AquaMark.html
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "AquaMark.html")
DST = os.path.join(ROOT, "windows", "AquaMark.html")

ACCEL_BLOCK = r"""

/* =====================================================================
   0-win. 跨平台：快捷键标识本地化（仅 Windows / Linux 变体）
   页面里所有快捷键一律按 macOS 写法记录（⌘ ⇧ ⌥ ⌃）。
   按键判定本身早就兼容两套（mod = metaKey || ctrlKey），要改的只是
   「显示给人看的标签」：⌘S → Ctrl+S，⇧⌘F → Ctrl+Shift+F，⌃⌘F → F11。
   Mac 上再由 IS_APPLE 判定原样返回，所以这段放进 Mac 版也无害。
   ===================================================================== */
const IS_APPLE = /Mac|iPhone|iPad|iPod/i.test(
  (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || navigator.userAgent || ''
);
function accelOne(m){
  if(/⌃/.test(m) && /⌘/.test(m)) return 'F11';       /* macOS 专属组合，别处没有对应键 */
  const order = [];
  if(/⌘/.test(m)) order.push('Ctrl');
  if(/⌥/.test(m)) order.push('Alt');
  if(/⇧/.test(m)) order.push('Shift');
  if(/⌃/.test(m) && order[0] !== 'Ctrl') order.push('Ctrl');
  const key = m.replace(/[⌘⇧⌥⌃]/g, '');
  return key ? order.concat([key]).join('+') : order.join('+');
}
function accelText(s){
  if(IS_APPLE || typeof s !== 'string' || !/[⌘⇧⌥⌃]/.test(s)) return s;
  return s
    .replace(/[⌘⇧⌥⌃]+[^\s·、,，；;]+/g, accelOne)
    .replace(/⌘/g, 'Ctrl').replace(/⌥/g, 'Alt').replace(/⇧/g, 'Shift').replace(/⌃/g, 'Ctrl');
}
/* 把整棵子树里的标签改写成本平台写法（正文 ≈ title 属性都算） */
function localizeAccels(root){
  if(IS_APPLE) return;
  root = root || document.body;
  if(!root) return;
  root.querySelectorAll && root.querySelectorAll('[title]').forEach(el=>{
    const old = el.getAttribute('title');
    if(old && /[⌘⇧⌥⌃]/.test(old)) el.setAttribute('title', accelText(old));
  });
  if(!document.createTreeWalker) return;
  const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(n){
      if(!n.nodeValue || !/[⌘⇧⌥⌃]/.test(n.nodeValue)) return NodeFilter.FILTER_REJECT;
      const p = n.parentElement;
      if(!p || p.tagName === 'SCRIPT' || p.tagName === 'STYLE' || p.id === 'hl') return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }
  });
  const hits = []; let n;
  while((n = tw.nextNode())) hits.push(n);
  hits.forEach(tn=>{ tn.nodeValue = accelText(tn.nodeValue); });
}"""


KEY_OLD = """  if(!(e.metaKey || e.ctrlKey) || e.altKey) return;
  if(composing || e.isComposing || e.keyCode === 229) return;
  const k = e.key;
  /* ⌃⌘F 全屏（与菜单项一致）。注意 macOS 上控制键组合的 key 仍是字母本身。 */
  if(e.ctrlKey && (e.metaKey || e.ctrlKey) && (k === 'f' || k === 'F' || e.code === 'KeyF')){
    e.preventDefault(); toggleFullscreen(); return;
  }"""

KEY_NEW = """  /* Win/Linux 变体：F11 进全屏。必须写在「要有修饰键」的守卫之前 ——
     第一版补丁把它放到了守卫后面，结果 F11 永远进不到这里。 */
  if(e.key === 'F11'){ e.preventDefault(); toggleFullscreen(); return; }
  if(!(e.metaKey || e.ctrlKey) || e.altKey) return;
  if(composing || e.isComposing || e.keyCode === 229) return;
  const k = e.key;
  /* ⌃⌘F 仍是 Mac 写法；Windows 侧绝不能写成 ctrlKey && (metaKey || ctrlKey)，
     那样 Ctrl+F 会同时触发「查找」和「全屏」。 */
  if(e.metaKey && e.ctrlKey && (k === 'f' || k === 'F' || e.code === 'KeyF')){
    e.preventDefault(); toggleFullscreen(); return;
  }"""


# (说明, old, new, 期望出现次数)
PATCHES = [
    ("插入快捷键本地化模块",
     "const $$ = s => Array.from(document.querySelectorAll(s));",
     "const $$ = s => Array.from(document.querySelectorAll(s));" + ACCEL_BLOCK, 1),

    ("Windows 字体栈：等宽补 Consolas",
     '"Monaco","Menlo","Courier New"', '"Monaco","Menlo","Consolas","Courier New"', 4),
    ("Windows 字体栈：等宽补 Consolas",
     '"Monaco","Menlo",monospace', '"Monaco","Menlo","Consolas",monospace', 3),
    ("Windows 字体栈：等宽补 Consolas",
     'Monaco,Menlo,"Courier New",monospace', 'Monaco,Menlo,Consolas,"Courier New",monospace', 1),
    ("Windows 字体栈：界面字体补 Segoe UI",
     '"Lucida Sans Unicode","Helvetica Neue",Helvetica,"PingFang SC"',
     '"Lucida Sans Unicode","Helvetica Neue",Helvetica,"Segoe UI","PingFang SC"', 1),
    ("Windows 字体栈：正文补 Segoe UI 与雅黑",
     'Helvetica,"PingFang SC","Hiragino Sans GB",Arial',
     'Helvetica,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",Arial', 1),

    ("Ctrl+F 与全屏的键位冲突", KEY_OLD, KEY_NEW, 1),

    ("帮助等面板内容本地化",
     """function openSheet(title, html, cls){
  sheetTitle.textContent = title;
  sheetBody.innerHTML = html;""",
     """function openSheet(title, html, cls){
  sheetTitle.textContent = accelText(title);
  sheetBody.innerHTML = accelText(html);""", 1),

    ("状态栏提示本地化",
     "if(!d.nativePath){ fileInfo.textContent = '未关联磁盘文件（⌘S 另存为）'; return; }",
     "if(!d.nativePath){ fileInfo.textContent = accelText('未关联磁盘文件（⌘S 另存为）'); return; }", 1),

    ("无文件句柄时说明「为什么会下载副本」",
     "if(!fileHandle){ fileInfo.textContent = '未关联磁盘文件（⌘S 另存为）'; return; }",
     """if(!fileHandle){
    /* file:// 下拿不到 File System Access API，浏览器不允许写回原文件，
       保存会降级成「下载副本」——必须在状态栏说清楚，否则 Windows 上直接双击 HTML
       使用时完全不知道发生了什么。走启动脚本（http://127.0.0.1）就没有这个限制。 */
    fileInfo.textContent = accelText(hasFS ? '未关联磁盘文件（⌘S 另存为）'
                                           : '只读会话：⌘S 会下载副本（改用 Start-AquaMark.bat 可获得真正的保存）');
    return;
  }""", 1),

    ("欢迎文档里的快捷键表格本地化",
     "  return t.join('\\n');", "  return accelText(t.join('\\n'));", 1),

    ("冲突面板提示本地化",
     """+ '<div class="note" style="margin-top:12px;color:#8a93a0">选「保留我的编辑」后按 ⌘S 会用当前内容覆盖磁盘。</div>');""",
     """+ accelText('<div class="note" style="margin-top:12px;color:#8a93a0">选「保留我的编辑」后按 ⌘S 会用当前内容覆盖磁盘。</div>'));""", 1),

    ("toast 本地化",
     "if(!st){ toast('当前文稿没有关联磁盘文件（⌘S 另存为）'); return; }",
     "if(!st){ toast(accelText('当前文稿没有关联磁盘文件（⌘S 另存为）')); return; }", 1),

    ("toast 本地化",
     "toast(prefs.autosave ? '已开启自动保存到浏览器' : '已关闭自动保存（记得手动 ⌘S）');",
     "toast(accelText(prefs.autosave ? '已开启自动保存到浏览器' : '已关闭自动保存（记得手动 ⌘S）'));", 1),

    ("toast 本地化",
     ": '已关闭自动写回磁盘 —— 落盘只由 ⌘S 触发');",
     ": accelText('已关闭自动写回磁盘 —— 落盘只由 ⌘S 触发'));", 1),

    ("toast 本地化",
     "if(!ok) toast('浏览器不允许自动全屏 —— 之后可用 ⌃⌘F 手动进入');",
     "if(!ok) toast(accelText('浏览器不允许自动全屏 —— 之后可用 ⌃⌘F 手动进入（Windows 上按 F11）'));", 1),

    ("toast 本地化",
     "toast('提示：⌘S 保存 · ⌘B 加粗 · ⇧⌘F 整理格式');",
     "toast(accelText('提示：⌘S 保存 · ⌘B 加粗 · ⇧⌘F 整理格式'));", 1),

    ("启动时把静态文案整体本地化一遍",
     "if(firstRun && store.ok){",
     "localizeAccels(document.body);      /* 菜单项 / 工具栏提示 / 启动幕等静态文案 */\n\nif(firstRun && store.ok){", 1),
]


def main():
    src = open(SRC, encoding="utf-8").read()
    print("源 %s（%d 字节）" % (os.path.relpath(SRC, ROOT), len(src.encode("utf-8"))))

    out = src
    for desc, old, new, want in PATCHES:
        n = out.count(old)
        if n != want:
            sys.exit("✗ [%s] 期望匹配 %d 次，实际 %d 次 —— 源码已改动，请更新补丁后再生成。\n  锚点：%s"
                     % (desc, want, n, old.replace("\n", "\\n")[:90]))
        out = out.replace(old, new)
        print("  ✓ %s（%d 处）" % (desc, n))

    open(DST, "w", encoding="utf-8").write(out)
    print("已生成 %s（%d 字节）" % (os.path.relpath(DST, ROOT), len(out.encode("utf-8"))))


if __name__ == "__main__":
    main()
