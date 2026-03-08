#!/usr/bin/env python3
"""
Antigravity Better 部署工具
将 app_root/workbench.html 替换到 Antigravity 安装目录中的 workbench.html
原文件备份为 workbench.html.origin
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

# ================== 配置 ==================
# 源文件相对路径（相对于脚本目录）
SOURCE_RELATIVE_PATH = "app_root/workbench.html"

# 目标目录搜索规则：在 Program Files 下查找 Antigravity
TARGET_SEARCH_PATHS = [
    Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Antigravity" / "resources" / "app" / "out" / "vs" / "code" / "electron-browser" / "workbench",
    Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Antigravity" / "resources" / "app" / "out" / "vs" / "code" / "electron-browser" / "workbench",
    Path("D:\\Program Files") / "Antigravity" / "resources" / "app" / "out" / "vs" / "code" / "electron-browser" / "workbench",
]

TARGET_FILENAME = "workbench.html"
BACKUP_SUFFIX = ".origin"


def find_script_dir() -> Path:
    """获取脚本所在目录"""
    return Path(__file__).parent.resolve()


def find_source_file() -> Path:
    """查找源文件"""
    script_dir = find_script_dir()
    source_path = script_dir / SOURCE_RELATIVE_PATH
    if source_path.exists():
        return source_path
    raise FileNotFoundError(f"源文件不存在: {source_path}")


def find_target_dir() -> Path | None:
    """自动查找目标目录"""
    for path in TARGET_SEARCH_PATHS:
        if path.exists() and path.is_dir():
            target_file = path / TARGET_FILENAME
            if target_file.exists():
                return path
    return None


def deploy(target_dir: Path, dry_run: bool = False) -> tuple[bool, str]:
    """
    执行部署操作
    
    Args:
        target_dir: 目标目录
        dry_run: 仅模拟，不实际执行
        
    Returns:
        (成功, 消息)
    """
    try:
        source_file = find_source_file()
        target_file = target_dir / TARGET_FILENAME
        backup_file = target_dir / (TARGET_FILENAME + BACKUP_SUFFIX)
        
        # 检查目标文件
        if not target_file.exists():
            return False, f"目标文件不存在: {target_file}"
        
        # 备份原文件（如果备份不存在）
        if not backup_file.exists():
            if dry_run:
                print(f"[DRY-RUN] 备份: {target_file} -> {backup_file}")
            else:
                shutil.copy2(target_file, backup_file)
                print(f"✅ 已备份: {backup_file}")
        else:
            print(f"ℹ️ 备份已存在，跳过: {backup_file}")
        
        # 复制新文件
        if dry_run:
            print(f"[DRY-RUN] 复制: {source_file} -> {target_file}")
        else:
            shutil.copy2(source_file, target_file)
            print(f"✅ 已部署: {target_file}")
        
        return True, "部署成功！重启 Antigravity 生效。"
        
    except Exception as e:
        return False, f"部署失败: {e}"


def restore(target_dir: Path, dry_run: bool = False) -> tuple[bool, str]:
    """
    恢复原始文件
    
    Args:
        target_dir: 目标目录
        dry_run: 仅模拟，不实际执行
        
    Returns:
        (成功, 消息)
    """
    try:
        target_file = target_dir / TARGET_FILENAME
        backup_file = target_dir / (TARGET_FILENAME + BACKUP_SUFFIX)
        
        if not backup_file.exists():
            return False, f"备份文件不存在: {backup_file}"
        
        if dry_run:
            print(f"[DRY-RUN] 恢复: {backup_file} -> {target_file}")
        else:
            shutil.copy2(backup_file, target_file)
            print(f"✅ 已恢复: {target_file}")
        
        return True, "恢复成功！重启 Antigravity 生效。"
        
    except Exception as e:
        return False, f"恢复失败: {e}"


# ================== CLI 模式 ==================
def run_cli():
    """命令行模式入口"""
    parser = argparse.ArgumentParser(
        description="Antigravity Better 部署工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python deploy_cascade.py deploy           # 自动查找并部署
  python deploy_cascade.py deploy -t "D:\\..."  # 指定目标目录
  python deploy_cascade.py restore          # 恢复原始文件
  python deploy_cascade.py --gui            # 启动图形界面
        """
    )
    
    parser.add_argument("action", nargs="?", choices=["deploy", "restore", "status"],
                        help="执行的操作: deploy=部署, restore=恢复, status=查看状态")
    parser.add_argument("-t", "--target", type=str, help="指定目标目录路径")
    parser.add_argument("-n", "--dry-run", action="store_true", help="仅模拟，不实际执行")
    parser.add_argument("--gui", action="store_true", help="启动图形界面")
    
    args = parser.parse_args()
    
    # 启动 GUI
    if args.gui or args.action is None:
        run_gui()
        return
    
    # 确定目标目录
    if args.target:
        target_dir = Path(args.target)
        if not target_dir.exists():
            print(f"❌ 指定目录不存在: {target_dir}")
            sys.exit(1)
    else:
        target_dir = find_target_dir()
        if not target_dir:
            print("❌ 未找到 Antigravity 安装目录，请使用 -t 参数指定")
            sys.exit(1)
    
    print(f"📂 目标目录: {target_dir}")
    
    # 执行操作
    if args.action == "deploy":
        success, msg = deploy(target_dir, args.dry_run)
    elif args.action == "restore":
        success, msg = restore(target_dir, args.dry_run)
    elif args.action == "status":
        target_file = target_dir / TARGET_FILENAME
        backup_file = target_dir / (TARGET_FILENAME + BACKUP_SUFFIX)
        print(f"目标文件: {target_file} ({'存在' if target_file.exists() else '不存在'})")
        print(f"备份文件: {backup_file} ({'存在' if backup_file.exists() else '不存在'})")
        return
    
    print(f"\n{'✅' if success else '❌'} {msg}")
    sys.exit(0 if success else 1)


# ================== GUI 模式 ==================
def run_gui():
    """图形界面模式"""
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    
    class DeployApp:
        def __init__(self, root):
            self.root = root
            self.root.title("Antigravity Better 部署工具")
            self.root.geometry("500x450")
            self.root.resizable(False, False)
            
            # 尝试设置主题
            try:
                self.root.tk.call("source", "azure.tcl")
                ttk.Style().theme_use("azure-dark")
            except:
                pass
            
            self.target_dir = tk.StringVar()
            self.status_text = tk.StringVar(value="就绪")
            
            self.setup_ui()
            self.auto_detect_target()
        
        def setup_ui(self):
            # 主框架
            main_frame = ttk.Frame(self.root, padding=20)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            title_label = ttk.Label(main_frame, text="🚀 Antigravity Better 部署工具", 
                                    font=("Segoe UI", 14, "bold"))
            title_label.pack(pady=(0, 20))
            
            # 源文件信息
            source_frame = ttk.LabelFrame(main_frame, text="📁 源文件", padding=10)
            source_frame.pack(fill=tk.X, pady=(0, 10))
            
            try:
                source_file = find_source_file()
                source_text = str(source_file)
                source_status = "✅ 已找到"
            except FileNotFoundError as e:
                source_text = str(e)
                source_status = "❌ 未找到"
            
            ttk.Label(source_frame, text=source_text, wraplength=430).pack(anchor=tk.W)
            ttk.Label(source_frame, text=source_status, foreground="green" if "✅" in source_status else "red").pack(anchor=tk.W)
            
            # 目标目录
            target_frame = ttk.LabelFrame(main_frame, text="🎯 目标目录", padding=10)
            target_frame.pack(fill=tk.X, pady=(0, 10))
            
            path_frame = ttk.Frame(target_frame)
            path_frame.pack(fill=tk.X)
            
            self.target_entry = ttk.Entry(path_frame, textvariable=self.target_dir, width=50)
            self.target_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
            
            browse_btn = ttk.Button(path_frame, text="浏览...", command=self.browse_target)
            browse_btn.pack(side=tk.RIGHT)
            
            detect_btn = ttk.Button(target_frame, text="🔍 自动检测", command=self.auto_detect_target)
            detect_btn.pack(anchor=tk.W, pady=(5, 0))
            
            # 操作按钮
            btn_frame = ttk.Frame(main_frame)
            btn_frame.pack(pady=20)
            
            deploy_btn = ttk.Button(btn_frame, text="📤 部署", command=self.do_deploy, width=15)
            deploy_btn.pack(side=tk.LEFT, padx=10)
            
            restore_btn = ttk.Button(btn_frame, text="📥 恢复原版", command=self.do_restore, width=15)
            restore_btn.pack(side=tk.LEFT, padx=10)
            
            # 状态栏
            status_frame = ttk.Frame(main_frame)
            status_frame.pack(fill=tk.X, side=tk.BOTTOM)
            
            ttk.Label(status_frame, text="状态:").pack(side=tk.LEFT)
            self.status_label = ttk.Label(status_frame, textvariable=self.status_text)
            self.status_label.pack(side=tk.LEFT, padx=5)
        
        def auto_detect_target(self):
            """自动检测目标目录"""
            target = find_target_dir()
            if target:
                self.target_dir.set(str(target))
                self.status_text.set("✅ 已自动检测到目标目录")
            else:
                self.status_text.set("⚠️ 未找到目标目录，请手动指定")
        
        def browse_target(self):
            """浏览选择目标目录"""
            directory = filedialog.askdirectory(title="选择 Antigravity 扩展目录")
            if directory:
                self.target_dir.set(directory)
        
        def do_deploy(self):
            """执行部署"""
            target = self.target_dir.get().strip()
            if not target:
                messagebox.showerror("错误", "请先指定目标目录")
                return
            
            target_path = Path(target)
            if not target_path.exists():
                messagebox.showerror("错误", f"目录不存在: {target}")
                return
            
            success, msg = deploy(target_path)
            if success:
                messagebox.showinfo("成功", msg)
                self.status_text.set("✅ 部署成功")
            else:
                messagebox.showerror("失败", msg)
                self.status_text.set("❌ 部署失败")
        
        def do_restore(self):
            """执行恢复"""
            target = self.target_dir.get().strip()
            if not target:
                messagebox.showerror("错误", "请先指定目标目录")
                return
            
            target_path = Path(target)
            success, msg = restore(target_path)
            if success:
                messagebox.showinfo("成功", msg)
                self.status_text.set("✅ 已恢复原版")
            else:
                messagebox.showerror("失败", msg)
                self.status_text.set("❌ 恢复失败")
    
    root = tk.Tk()
    app = DeployApp(root)
    root.mainloop()


# ================== 主入口 ==================
if __name__ == "__main__":
    # 无参数时启动 GUI，有参数时进入 CLI
    if len(sys.argv) == 1:
        run_gui()
    else:
        run_cli()
