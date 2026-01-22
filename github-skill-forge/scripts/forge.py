#!/usr/bin/env python3

import sys
import os
import subprocess
import shutil
import re
import json
import argparse
import time
import signal
import urllib.request
import urllib.error
from pathlib import Path

# 尝试加载本地 .env 文件
def load_env_file(env_path: Path):
    """
    轻量级加载 .env 文件到环境变量
    """
    if not env_path.exists():
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
    except Exception:
        pass

# 加载脚本同目录或父目录下的 .env
env_paths = [
    Path(__file__).parent / ".env",
    Path(__file__).parent.parent / ".env",
    Path.cwd() / ".env"
]
for env_p in env_paths:
    load_env_file(env_p)
from typing import Optional, List, Dict, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


# ==================== 颜色配置 ====================
class Colors:
    """终端颜色输出配置"""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # 前景色
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # 背景色
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"

    # 亮色
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # 常用颜色别名
    HEADER = MAGENTA  # 用于标题
    ERROR = RED  # 用于错误
    SUCCESS = GREEN  # 用于成功
    WARNING = YELLOW  # 用于警告
    PROGRESS = BLUE  # 用于进度
    INFO = CYAN  # 用于信息

    @staticmethod
    def supports_color() -> bool:
        """检查终端是否支持颜色输出"""
        return (
            hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        ) or os.environ.get("TERM") == "xterm-color"

    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """为文本添加颜色"""
        if cls.supports_color():
            return f"{color}{text}{cls.RESET}"
        return text

    @classmethod
    def info(cls, text: str) -> str:
        """信息提示"""
        return cls.colorize(f"ℹ {text}", cls.CYAN)

    @classmethod
    def success(cls, text: str) -> str:
        """成功提示"""
        return cls.colorize(f"✓ {text}", cls.GREEN)

    @classmethod
    def warning(cls, text: str) -> str:
        """警告提示"""
        return cls.colorize(f"⚠ {text}", cls.YELLOW)

    @classmethod
    def error(cls, text: str) -> str:
        """错误提示"""
        return cls.colorize(f"✗ {text}", cls.RED)

    @classmethod
    def progress(cls, text: str) -> str:
        """进度提示"""
        return cls.colorize(f"→ {text}", cls.BLUE)

    @classmethod
    def header(cls, text: str) -> str:
        """标题提示"""
        return cls.colorize(f"★ {text}", cls.MAGENTA)


# ==================== 配置类 ====================
@dataclass
class ForgeConfig:
    """技能锻造配置类"""

    # 基本配置
    default_skill_name: str = "{repo_name}"
    clone_depth: int = 1
    max_retries: int = 3
    timeout: int = 60

    # 镜像配置
    clone_mirrors: List[str] = field(
        default_factory=lambda: [
            "https://github.com",
            "https://kkgithub.com",
            "https://gitclone.com/github.com",
        ]
    )
    proxy_enabled: bool = True
    proxy_url: str = "gitclone.com/github.com/"

    # 文件过滤
    skip_patterns: List[str] = field(
        default_factory=lambda: [
            ".git",
            ".gitignore",
            ".github",
            ".gitattributes",
            "node_modules",
            "__pycache__",
            "*.pyc",
            ".venv",
            "venv",
            "dist",
            "build",
            ".tox",
            ".mypy_cache",
            ".pytest_cache",
            "coverage",
            ".idea",
            ".vscode",
            "*.swp",
            "*.swo",
            "~",
        ]
    )

    # 模板配置
    custom_template_path: Optional[str] = None

    # 输出配置
    verbose: bool = False
    quiet: bool = False
    dry_run: bool = False
    force: bool = False

    # 上下文配置
    max_file_count: int = 100
    max_doc_size: int = 20000

    # 安全配置
    min_stars: int = 100
    no_safety_check: bool = False

    # 镜像配置
    api_mirrors: List[str] = field(
        default_factory=lambda: [
            "https://api.github.com",
            "https://gh-api.vps.sc",
            "https://api.gitmirror.com",
            "https://ghproxy.net/https://api.github.com",
            "https://gh.api.99988866.xyz",
        ]
    )
    current_api_base: str = "https://api.github.com"

    @classmethod
    def load_from_file(cls, config_path: Path) -> "ForgeConfig":
        """从配置文件加载配置"""
        if not config_path.exists():
            return cls()

        try:
            import toml

            config_data = toml.load(config_path)

            return cls(
                default_skill_name=config_data.get(
                    "default_skill_name", cls().default_skill_name
                ),
                clone_depth=config_data.get("clone_depth", cls().clone_depth),
                max_retries=config_data.get("max_retries", cls().max_retries),
                timeout=config_data.get("timeout", cls().timeout),
                proxy_enabled=config_data.get("proxy_enabled", cls().proxy_enabled),
                proxy_url=config_data.get("proxy_url", cls().proxy_url),
                skip_patterns=config_data.get("skip_patterns", cls().skip_patterns),
                custom_template_path=config_data.get("custom_template_path"),
                verbose=config_data.get("verbose", False),
                quiet=config_data.get("quiet", False),
                dry_run=config_data.get("dry_run", False),
                force=config_data.get("force", False),
                max_file_count=config_data.get("max_file_count", cls().max_file_count),
                max_doc_size=config_data.get("max_doc_size", cls().max_doc_size),
                min_stars=config_data.get("min_stars", cls().min_stars),
                no_safety_check=config_data.get("no_safety_check", cls().no_safety_check),
            )
        except Exception as e:
            print(f"{Colors.warning('警告')}: 无法加载配置文件 {config_path}: {e}")
            return cls()


# ==================== 错误类型 ====================
class ForgeError(Exception):
    """技能锻造基础错误类"""

    def __init__(
        self, message: str, error_code: str = "UNKNOWN", details: Optional[str] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(self.message)


class CloneError(ForgeError):
    """克隆错误"""

    def __init__(self, message: str, url: str, retry_count: int = 0):
        super().__init__(
            message=message,
            error_code="CLONE_ERROR",
            details=f"URL: {url}, 重试次数: {retry_count}",
        )
        self.url = url
        self.retry_count = retry_count


class ValidationError(ForgeError):
    """验证错误"""

    def __init__(self, message: str, field: str = ""):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=f"字段: {field}" if field else None,
        )
        self.field = field


class SecurityError(ForgeError):
    """安全错误"""

    def __init__(self, message: str, repository: str, reason: str = ""):
        super().__init__(
            message=message,
            error_code="SECURITY_ERROR",
            details=f"仓库: {repository}, 原因: {reason}",
        )
        self.repository = repository
        self.reason = reason


# ==================== 进度显示 ====================
class ProgressBar:
    """进度条显示类"""

    def __init__(self, description: str = "进度", total: int = 100, width: int = 50):
        self.description = description
        self.total = total
        self.width = width
        self.current = 0
        self.lock = threading.Lock()
        self.start_time = time.time()
        self._last_update = 0

    def update(self, n: int = 1, status: str = ""):
        """更新进度"""
        with self.lock:
            self.current += n
            elapsed = time.time() - self.start_time
            percent = (
                min(100, 100.0 * self.current / self.total) if self.total > 0 else 100
            )

            # 限制更新频率
            current_time = time.time()
            if current_time - self._last_update < 0.1 and status:
                return
            self._last_update = current_time

            # 计算速度
            if elapsed > 0:
                speed = self.current / elapsed
                if speed > 60:
                    speed_str = f"{speed:.1f}/s"
                elif speed > 1:
                    speed_str = f"{speed:.1f}/s"
                else:
                    speed_str = f"{1 / speed:.1f}s/item"
            else:
                speed_str = "..."

            # 绘制进度条
            filled = int(self.width * percent / 100)
            bar = "█" * filled + "░" * (self.width - filled)

            # 输出
            progress_str = f"\r{Colors.CYAN}{self.description}{Colors.RESET} |{Colors.GREEN}{bar}{Colors.RESET}| "
            progress_str += f"{Colors.BOLD}{percent:5.1f}%{Colors.RESET} "
            progress_str += (
                f"{Colors.WHITE}[{self.current}/{self.total}]{Colors.RESET} "
            )
            if status:
                progress_str += f"{Colors.DIM}{status}{Colors.RESET}"

            sys.stdout.write(progress_str)
            sys.stdout.flush()

            if self.current >= self.total:
                sys.stdout.write("\n")
                sys.stdout.flush()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.current < self.total:
            self.update(self.total - self.current)


# ==================== 工具函数 ====================
def get_repo_info(url: str) -> Tuple[str, str]:
    """
    从 URL 提取 owner 和 repo
    """
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    
    # 處理 SSH 格式 git@github.com:owner/repo
    if url.startswith("git@"):
        match = re.match(r"git@github\.com:([\w.-]+)/([\w.-]+)", url)
        if match:
            return match.group(1), match.group(2)
            
    parts = url.split("/")
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    
    raise ForgeError(f"无法从 URL 提取仓库信息: {url}")


def make_api_request(url_path: str, config: ForgeConfig) -> Any:
    """
    发送带镜像重试的 API 请求
    """
    # 尝试从环境变量获取 GITHUB_TOKEN
    token = os.environ.get("GITHUB_TOKEN")
    
    for base_url in config.api_mirrors:
        api_url = f"{base_url.rstrip('/')}/{url_path.lstrip('/')}"
        try:
            # 针对 ghproxy 的特殊处理
            if "ghproxy.net" in base_url:
                # ghproxy.net 通常用于加速 raw/archive，对于 API 接口可能需要特定头
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                }
            else:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/vnd.github.v3+json"
                }
            
            if token and "github.com" in base_url and "ghproxy" not in base_url:
                headers["Authorization"] = f"token {token}"
                
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                config.current_api_base = base_url
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            if e.code == 403 and "ghproxy" in base_url:
                # ghproxy 经常报 403，静默跳过
                continue
            if config.verbose:
                print(f"{Colors.WARNING}镜像 {base_url} 返回 HTTP {e.code}: {e.reason}")
        except Exception as e:
            if config.verbose:
                print(f"{Colors.WARNING}镜像 {base_url} 请求失败: {e}")
            continue
    raise ForgeError(f"所有 API 镜像均无法访问: {url_path}。请检查网络或配置代理。")


def get_repo_name(url: str) -> str:
    """
    从 URL 提取仓库名称

    Args:
        url: GitHub 仓库 URL

    Returns:
        仓库名称（清理后的）

    Examples:
        >>> get_repo_name("https://github.com/username/repo-name")
        'repo-name'
        >>> get_repo_name("https://github.com/username/repo-name.git")
        'repo-name'
    """
    if url.endswith(".git"):
        url = url[:-4]

    name = url.split("/")[-1]
    # 只保留字母、数字、连字符和下划线
    name = re.sub(r"[^a-zA-Z0-9-_]", "", name)

    return name if name else "unknown-skill"


def validate_url(url: str) -> bool:
    """
    验证 GitHub URL 格式
    """
    # GitHub URL 模式 (支持 .git 后缀和各种变体)
    patterns = [
        r"^https://github\.com/[\w.-]+/[\w.-]+/?$",
        r"^https://github\.com/[\w.-]+/[\w.-]+\.git/?$",
        r"^git@github\.com:[\w.-]+/[\w.-]+\.git/?$",
        r"^git@github\.com:[\w.-]+/[\w.-]+/?$",
    ]

    return any(re.match(pattern, url) for pattern in patterns)


def get_file_tree(
    start_path: Path, limit: int = 100, skip_patterns: Optional[List[str]] = None
) -> str:
    """
    生成文件树字符串

    Args:
        start_path: 起始路径
        limit: 最大文件数量
        skip_patterns: 跳过的模式列表

    Returns:
        文件树字符串
    """
    if skip_patterns is None:
        skip_patterns = []

    tree_str = []
    count = 0

    def should_skip(name: str, is_dir: bool) -> bool:
        """检查是否应该跳过"""
        for pattern in skip_patterns:
            if pattern.startswith("*"):
                # 通配符匹配
                if name.endswith(pattern[1:]):
                    return True
            elif pattern.startswith("."):
                # 点文件/目录
                if name.startswith(pattern):
                    return True
            else:
                if name == pattern:
                    return True
        return False

    for root, dirs, files in os.walk(start_path):
        # 过滤隐藏目录
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        level = root.replace(str(start_path), "").count(os.sep)
        indent = " " * 4 * level

        dir_name = os.path.basename(root)
        if should_skip(dir_name, True):
            continue

        tree_str.append(f"{indent}{Colors.colorize(dir_name, Colors.BLUE)}/")
        subindent = " " * 4 * (level + 1)

        for f in files:
            if should_skip(f, False):
                continue

            tree_str.append(f"{subindent}{f}")
            count += 1

            if count > limit:
                tree_str.append(
                    f"{subindent}{Colors.colorize('... (truncated)', Colors.YELLOW)}"
                )
                return "\n".join(tree_str)

    return "\n".join(tree_str)


def check_repository_safety(url: str, config: ForgeConfig) -> Tuple[bool, str, str]:
    """
    检查仓库安全性并获取描述

    Returns:
        (是否安全, 统计信息, 描述)
    """
    try:
        # 提取 owner/repo
        url = url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]
        parts = url.split("/")
        owner = parts[-2]
        repo = parts[-1]

        data = make_api_request(f"repos/{owner}/{repo}", config)

        stars = data.get("stargazers_count", 0)
        forks = data.get("forks_count", 0)
        license_info = data.get("license", {})
        license_id = license_info.get("spdx_id", "未知") if license_info else "未知"
        description = data.get("description", "")

        # 生成安全报告
        safety_info = [
            f"Stars: {stars:,}",
            f"Forks: {forks:,}",
            f"许可证: {license_id}"
        ]

        # 严格安全检查
        if stars < config.min_stars:
            return (
                False,
                f"仓库 Stars ({stars}) 低于设定的金标阈值 ({config.min_stars})。详情: {'; '.join(safety_info)}",
                description
            )

        return True, "; ".join(safety_info), description

    except Exception as e:
        return False, f"安全检查失败: {str(e)}", ""


def fetch_github_contents(owner: str, repo: str, path: str, config: ForgeConfig) -> Any:
    """递归在线获取 GitHub 内容"""
    return make_api_request(f"repos/{owner}/{repo}/contents/{path}", config)


def download_file_content(download_url: str) -> str:
    """通过直链下载文件内容"""
    try:
        # 针对镜像站，可能需要替换下载域名，这里先尝试原链接
        req = urllib.request.Request(download_url)
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return f"下载失败: {e}"


def online_repo_scanner(url: str, config: ForgeConfig) -> Dict[str, Any]:
    """
    全在线扫描仓库，不克隆。支持递归扫描关键目录和抓取入口代码。
    """
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    
    parts = url.split("/")
    if len(parts) < 2:
        raise ForgeError(f"无法解析 URL 中的 owner 和 repo: {url}")
        
    owner = parts[-2]
    repo = parts[-1]

    print(f"{Colors.INFO}正在进行全在线扫描 (镜像: {config.current_api_base})...")

    results = {
        "tree": [],
        "key_docs": {},
        "dependencies": {},
        "core_code": {},
        "entry_files": {},  # 分開存儲入口文件
        "language": "Unknown"
    }

    # 待扫描的队列 (path, depth)
    scan_queue = [("", 0)]
    scanned_paths = set()
    max_depth = 2  # 增加深度到2层，以覆盖更多子目录

    # 核心代码入口文件名 (擴展列表)
    entry_points = {
        "main.py", "__main__.py", "app.py", "cli.py", "core.py",
        "index.js", "main.js", "app.js", "server.js",
        "index.ts", "main.ts", "app.ts",
        "main.go", "lib.rs", "main.rs", "mod.rs",
        "App.java", "Main.java",
        "application.rb", "main.rb"
    }
    # 值得递归的目录名
    interest_dirs = {"src", "lib", "app", "bin", "include", "pkg", "internal", "cmd", repo.lower().replace("-", "_"), repo.lower()}

    while scan_queue:
        current_path, depth = scan_queue.pop(0)
        if current_path in scanned_paths or depth > max_depth:
            continue
        
        scanned_paths.add(current_path)
        try:
            items = fetch_github_contents(owner, repo, current_path, config)
            if not isinstance(items, list): continue

            for item in items:
                rel_path = f"{current_path}/{item['name']}".lstrip("/")
                results["tree"].append(f"[{item['type']}] {rel_path}")

                # 1. 关键文档 (只在根目录或一级目录)
                if item["type"] == "file" and any(re.match(p, item["name"], re.I) for p in ["README.*", "LICENSE.*", "CONTRIBUTING.*"]):
                    if len(results["key_docs"]) < 5:  # 限制数量
                        print(f"{Colors.PROGRESS}抓取文档: {rel_path}")
                        results["key_docs"][rel_path] = download_file_content(item["download_url"])

                # 2. 依赖项
                dep_map = {
                    "requirements.txt": "Python", "package.json": "Node.js", 
                    "go.mod": "Go", "Cargo.toml": "Rust", "pyproject.toml": "Python",
                    "setup.py": "Python", "pom.xml": "Java", "Gemfile": "Ruby"
                }
                if item["name"] in dep_map:
                    # 如果尚未確定語言，則更新
                    if results["language"] == "Unknown":
                        results["language"] = dep_map[item["name"]]
                        print(f"{Colors.SUCCESS}識別到主要語言: {results['language']} ({item['name']})")
                    
                    if item["name"] not in results["dependencies"]:
                        results["dependencies"][item["name"]] = download_file_content(item["download_url"])

                # 3. 入口文件與核心代碼
                if item["type"] == "file":
                    is_entry = item["name"].lower() in entry_points
                    is_code_file = item["name"].endswith((".py", ".js", ".ts", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".cs", ".rb", ".php", ".sh"))
                    
                    # 過濾測試和文檔
                    if any(x in rel_path.lower() for x in ["/tests/", "/test/", "/docs/", "/examples/", "/site-packages/"]):
                        continue

                    if is_entry:
                        if len(results["entry_files"]) < 5:
                            print(f"{Colors.PROGRESS}抓取入口代碼: {rel_path}")
                            code = download_file_content(item["download_url"])
                            results["entry_files"][rel_path] = "\n".join(code.splitlines()[:100])
                    elif is_code_file and depth > 0:
                        if len(results["core_code"]) < 10:
                            print(f"{Colors.PROGRESS}抓取核心代碼: {rel_path}")
                            code = download_file_content(item["download_url"])
                            results["core_code"][rel_path] = "\n".join(code.splitlines()[:100])

                # 4. 递归决策
                if item["type"] == "dir" and depth < max_depth:
                    if item["name"].lower() in interest_dirs or depth == 0:
                        scan_queue.append((rel_path, depth + 1))

        except Exception as e:
            if config.verbose:
                print(f"{Colors.WARNING}无法读取路径 {current_path}: {e}")
            continue

    return results


def detect_programming_language(src_dir: Path) -> Optional[str]:
    """
    检测项目编程语言

    Args:
        src_dir: 源代码目录

    Returns:
        检测到的编程语言
    """
    lang_extensions = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".c": "C",
        ".cpp": "C++",
        ".cs": "C#",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".scala": "Scala",
        ".r": "R",
        ".m": "Objective-C",
    }

    lang_counts: Dict[str, int] = {}

    for root, _, files in os.walk(src_dir):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in lang_extensions:
                lang_counts[lang_extensions[ext]] = (
                    lang_counts.get(lang_extensions[ext], 0) + 1
                )

    if lang_counts:
        # 返回最常见的语言
        return max(lang_counts, key=lambda k: lang_counts.get(k, 0))

    return None


# ==================== 核心功能函数 ====================
def create_context_bundle(
    src_dir: Path,
    output_path: Path,
    max_file_count: int = 100,
    max_doc_size: int = 20000,
    skip_patterns: Optional[List[str]] = None,
) -> None:
    """
    创建上下文聚合文件

    Args:
        src_dir: 源代码目录
        output_path: 输出路径
        max_file_count: 最大文件数量
        max_doc_size: 最大文档大小
        skip_patterns: 跳过的模式列表
    """
    content = []

    # 1. 项目结构
    content.append(f"{Colors.HEADER}项目结构{Colors.RESET}")
    content.append("```")
    content.append(get_file_tree(src_dir, max_file_count, skip_patterns))
    content.append("```\n")

    # 2. 编程语言检测
    lang = detect_programming_language(src_dir)
    if lang:
        content.append(f"{Colors.HEADER}编程语言: {Colors.RESET}{lang}\n")

    # 3. 关键文档
    content.append(f"{Colors.HEADER}关键文档{Colors.RESET}")
    doc_files = ["README*", "CONTRIBUTING*", "AUTHORS*", "LICENSE*", "CHANGELOG*"]
    docs = []
    for pattern in doc_files:
        docs.extend(src_dir.glob(pattern))

    for doc in docs:
        try:
            with open(doc, "r", encoding="utf-8", errors="ignore") as f:
                doc_content = f.read()

                # 截断过长的文档
                if len(doc_content) > max_doc_size:
                    doc_content = doc_content[:max_doc_size]
                    doc_content += f"\n\n{Colors.YELLOW}... (文档截断，完整内容请查看源代码){Colors.RESET}"

                content.append(f"\n{Colors.HEADER}文件: {doc.name}{Colors.RESET}")
                content.append(doc_content)
                content.append("\n" + "-" * 60 + "\n")
        except Exception as e:
            content.append(
                f"\n{Colors.WARNING}无法读取 {doc.name}: {e}{Colors.RESET}\n"
            )

    # 4. 依赖项
    content.append(f"\n{Colors.HEADER}依赖项{Colors.RESET}")

    dep_files = {
        "Python": ["requirements.txt", "Pipfile", "pyproject.toml", "setup.py"],
        "Node.js": ["package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"],
        "Go": ["go.mod", "go.sum"],
        "Rust": ["Cargo.toml", "Cargo.lock"],
        "Java": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "Ruby": ["Gemfile", "Gemfile.lock"],
    }

    for lang, files in dep_files.items():
        for filename in files:
            dep_path = src_dir / filename
            if dep_path.exists():
                try:
                    with open(dep_path, "r", encoding="utf-8", errors="ignore") as f:
                        dep_content = f.read()
                        content.append(
                            f"\n{Colors.HEADER}{lang} - {filename}{Colors.RESET}"
                        )
                        content.append("```")
                        content.append(dep_content)
                        content.append("```\n")
                except Exception as e:
                    content.append(
                        f"\n{Colors.WARNING}无法读取 {filename}: {e}{Colors.RESET}\n"
                    )

    # 4. 主要入口文件
    content.append(f"\n{Colors.HEADER}主要入口文件{Colors.RESET}")
    # 增加更多語言的入口文件
    entry_points = [
        "__main__.py", "main.py", "app.py", "cli.py", "core.py",  # Python
        "index.js", "main.js", "app.js", "server.js",             # JS
        "index.ts", "main.ts", "app.ts",                          # TS
        "main.go", "lib.rs", "main.rs",                           # Go/Rust
        "App.java", "Main.java",                                  # Java
        "application.rb", "main.rb"                               # Ruby
    ]

    found_entries = 0
    for entry in entry_points:
        # 遞迴搜索入口文件 (不超過兩層)
        matches = list(src_dir.glob(f"**/{entry}"))
        for entry_path in matches:
            if found_entries >= 10: break # 最多顯示 10 個入口文件
            
            # 計算相對路徑深度，避免抓到太深的文件
            try:
                rel_path = entry_path.relative_to(src_dir)
                if len(rel_path.parts) > 3: continue 
            except ValueError:
                continue

            if entry_path.exists() and entry_path.is_file():
                try:
                    with open(entry_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()[:100]  # 增加到 100 行
                        ext = entry.split(".")[-1] if "." in entry else "text"
                        content.append(f"\n{Colors.HEADER}{rel_path}{Colors.RESET}")
                        content.append(f"```{ext}")
                        content.writelines(lines)
                        content.append("```\n")
                        found_entries += 1
                except Exception as e:
                    content.append(
                        f"\n{Colors.WARNING}无法读取 {rel_path}: {e}{Colors.RESET}\n"
                    )

    # 写入文件
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(content))

    print(f"{Colors.SUCCESS}已生成上下文包: {output_path}")


def generate_skill_template(
    skill_name: str,
    repo_url: str,
    language: Optional[str] = None,
    custom_template_path: Optional[str] = None,
    entry_file: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    """
    生成技能模板
    """
    # 优先使用自定义模板
    if custom_template_path:
        template_path = Path(custom_template_path)
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                template = f.read()
                template = template.replace("{{skill_name}}", skill_name)
                template = template.replace("{{repo_url}}", repo_url)
                template = template.replace("{{language}}", language or "Unknown")
                template = template.replace("{{description}}", description or f"Generated from {repo_url}.")
                return template

    # 根據語言生成安裝指南
    install_guide = ""
    run_guide = ""
    lang_lower = (language or "").lower()
    
    # 默認入口處理
    entry = entry_file or "src/main.py"
    
    if "python" in lang_lower:
        install_guide = "pip install -r requirements.txt"
        run_guide = f"python3 {entry} --help"
    elif "node" in lang_lower or "javascript" in lang_lower or "typescript" in lang_lower:
        install_guide = "npm install"
        run_guide = f"node {entry} --help"
    elif "go" in lang_lower:
        install_guide = "go mod download"
        run_guide = f"go run {entry} --help"
    elif "rust" in lang_lower:
        install_guide = "cargo build"
        run_guide = f"cargo run -- --help"
    else:
        install_guide = "# 請查看 context_bundle.md 獲取安裝說明"
        run_guide = f"# 請查看 context_bundle.md 獲取運行說明\n./{entry} --help"

    # 根据描述推断角色和调用场景
    desc_raw = description or "一个高效的开源工具"
    
    # 尝试自动翻译 (通过简单的正则匹配或规则，而不是死板的模板)
    def auto_translate(text: str) -> str:
        # 如果已经是中文，直接返回
        if re.search(r'[\u4e00-\u9fa5]', text):
            return text
            
        # 极简映射翻译逻辑 (应对常见关键词)
        translation_map = {
            "Fast, unopinionated, minimalist web framework for node": "快速、灵活、极简的 Node.js Web 框架",
            "A feature-rich command-line audio/video downloader": "功能丰富的命令行音频/视频下载工具",
            "Fast, unopinionated, minimalist web framework for Node.js": "快速、灵活、极简的 Node.js Web 框架",
        }
        
        for eng, chn in translation_map.items():
            if eng.lower() in text.lower():
                return chn
        
        # 简单的正则替换翻译 (自动处理一些常见结构)
        replacements = [
            (r'A (.*) for (.*)', r'一个用于 \2 的 \1'),
            (r'(.*) implementation of (.*)', r'\2 的 \1 实现'),
            (r'Simple (.*)', r'简单的 \1'),
            (r'Official (.*)', r'官方 \1'),
            (r'Modern (.*)', r'现代化的 \1'),
            (r'Fast (.*)', r'快速的 \1'),
            (r'Flexible (.*)', r'灵活的 \1'),
            (r'Lightweight (.*)', r'轻量级的 \1'),
            (r'Open source (.*)', r'开源的 \1'),
            (r'Powerful (.*)', r'功能强大的 \1'),
            (r'Python (.*)', r'Python \1'),
            (r'JavaScript (.*)', r'JavaScript \1'),
            (r'TypeScript (.*)', r'TypeScript \1'),
            (r'Go (.*)', r'Go \1'),
            (r'Rust (.*)', r'Rust \1'),
            (r'CLI (.*)', r'命令行 \1'),
            (r'Web (.*)', r'Web \1'),
            (r'Framework', r'框架'),
            (r'Library', r'库'),
            (r'Tool', r'工具'),
            (r'Plugin', r'插件'),
            (r'Client', r'客户端'),
            (r'Server', r'服务端'),
            (r'API', r'接口'),
            (r'Documentation', r'文档'),
            (r'Examples', r'示例'),
            (r'Utility', r'工具'),
            (r'Application', r'应用'),
            (r'Downloader', r'下载器'),
        ]
        
        result = text
        for pattern, replacement in replacements:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
            
        return result

    desc_zh = auto_translate(desc_raw)

    # 简单的关键词提取作为 tags
    tags = [skill_name.replace("-skill", ""), language] if language else [skill_name.replace("-skill", "")]
    
    # 自动从描述中提取更多 tags
    potential_tags = {
        "download": ["downloader", "下载器"],
        "video": ["video", "视频"],
        "audio": ["audio", "音频"],
        "music": ["music", "音乐"],
        "web": ["web", "网页"],
        "framework": ["framework", "框架"],
        "api": ["api", "接口"],
        "cli": ["cli", "命令行"],
        "tool": ["tool", "工具"],
        "gui": ["gui", "界面"],
        "library": ["library", "库"],
        "client": ["client", "客户端"],
        "server": ["server", "服务端"],
        "docker": ["docker", "容器化"],
        "cloud": ["cloud", "云原生"],
    }
    
    for keyword, associated_tags in potential_tags.items():
        if keyword in desc_raw.lower() or keyword in desc_zh.lower():
            for t in associated_tags:
                if t not in tags:
                    tags.append(t)
    
    # 默认模板
    base_template = f"""---
name: {skill_name}
description: {desc_zh}
tags: {tags}
---

# {skill_name}

## 角色设定
你是一个精通 {skill_name} 的专家级 Agent。你不仅熟悉该工具的核心逻辑，还能灵活运用它解决实际问题。
你的目标是作为用户的「技术副驾驶」，通过 {repo_url} 提供的能力，高效完成以下任务：{desc_zh}。

## 何时调用
- **核心需求**: 当用户需要执行「{desc_zh}」相关的操作时。
- **自动化流**: 需要通过 `scripts/` 目录下的脚本进行批量处理或复杂逻辑封装时。
- **集成开发**: 在开发过程中需要调用该项目的 API、库或 CLI 工具作为底层支撑时。

## 功能概述
该项目是一个基于 {language or "未知语言"} 构建的成熟方案。
### 核心价值
{desc_zh}

### 关键能力
1. **深度集成**: 支持通过 `scripts/` 编写自定义 Python/JS 脚本，直接调用 `src/` 中的核心模块。
2. **灵活配置**: 可根据 `context_bundle.md` 中的文档说明，通过环境变量或配置文件调整运行行为。
3. **高效执行**: 针对 {tags} 等场景进行了深度优化。

## 使用方法

### 1. 基础安装
在当前技能目录下执行依赖安装，确保环境就绪：
```bash
{install_guide}
```

### 2. 命令行直调
如果只需快速执行单次任务，可直接运行：
```bash
{run_guide}
```

### 3. 脚本化进阶（推荐）
对于复杂任务，建议在 `scripts/` 目录下创建包装脚本。
**示例脚本结构 (Python)**:
```python
import sys
import os
# 自动将 src 添加到路径
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
# 接下来可以 import 核心模块进行调用
```

## 执行步骤
1. **需求分析**: 根据用户输入的具体任务（如：下载某个链接），匹配该工具的最佳运行参数。
2. **环境检查**: 确认 `context_bundle.md` 中提到的依赖和配置是否已正确加载。
3. **任务执行**: 优先检查 `scripts/` 目录下是否有现成的包装脚本，若无则根据 `run_guide` 直接执行。
4. **结果交付**: 处理工具输出的数据，将其转化为用户可理解的最终成果。
"""
    return base_template


def clone_repository(url: str, target_dir: Path, config: ForgeConfig) -> bool:
    """
    克隆仓库

    Args:
        url: 仓库 URL
        target_dir: 目标目录
        config: 配置

    Returns:
        是否克隆成功
    """
    # 清理目录
    if target_dir.exists():
        if config.force:
            shutil.rmtree(target_dir)
        else:
            print(f"{Colors.ERROR}目标目录已存在: {target_dir}")
            return False

    # 提取 owner 和 repo
    parts = url.rstrip("/").split("/")
    if len(parts) >= 2:
        repo_path = f"{parts[-2]}/{parts[-1]}"
        # 移除 .git 后缀
        if repo_path.endswith(".git"):
            repo_path = repo_path[:-4]
    else:
        repo_path = ""

    # 尝试克隆
    clone_urls = []

    # 1. 尝试配置中的所有镜像
    for mirror_base in config.clone_mirrors:
        if repo_path:
            # 确保 mirror_base 结尾没有斜杠，repo_path 开头没有斜杠
            base = mirror_base.rstrip("/")
            clone_urls.append(f"{base}/{repo_path}")
        else:
            # 如果解析失败，回退到原始替换逻辑
            proxy_url = url.replace("github.com", mirror_base.replace("https://", "").replace("http://", ""))
            clone_urls.append(proxy_url)

    # 2. 确保原始 URL 在最后作为保底
    if url not in clone_urls:
        clone_urls.append(url)

    for attempt in range(config.max_retries):
        for clone_url in clone_urls:
            print(
                f"{Colors.PROGRESS}尝试克隆 ({attempt + 1}/{config.max_retries}): {clone_url}"
            )

            try:
                # 构建 git 命令
                # 在 Windows 下，如果直接使用列表，subprocess 有时无法正确处理 shell 别名或路径
                # 尝试使用 shell=True 并直接拼接字符串（注意安全，这里 clone_url 是可控的）
                # 检查 git 是否可用
                try:
                    subprocess.run(["git", "--version"], capture_output=True, check=True, shell=True)
                    cmd_str = f'git clone --depth {config.clone_depth} "{clone_url}" "{target_dir}"'
                except:
                    # 如果 git 失败，尝试完全限定路径或报错
                    cmd_str = f'git clone --depth {config.clone_depth} "{clone_url}" "{target_dir}"'

                print(f"{Colors.INFO}执行命令: {cmd_str}")
                result = subprocess.run(
                    cmd_str, capture_output=True, text=True, timeout=config.timeout, shell=True
                )

                if result.returncode == 0:
                    print(f"{Colors.SUCCESS}克隆成功")
                    return True
                else:
                    print(f"{Colors.WARNING}克隆失败: {result.stderr}")

            except subprocess.TimeoutExpired:
                print(f"{Colors.WARNING}克隆超时")
            except Exception as e:
                print(f"{Colors.ERROR}克隆错误: {e}")

        # 重试前等待
        if attempt < config.max_retries - 1:
            wait_time = (attempt + 1) * 2
            print(f"{Colors.INFO}等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)

    return False


def cleanup_git_folder(src_dir: Path) -> bool:
    """
    清理 .git 文件夹

    Args:
        src_dir: 源代码目录

    Returns:
        是否清理成功
    """
    git_folder = src_dir / ".git"

    if not git_folder.exists():
        return True

    try:

        def on_rm_error(func, path, exc_info):
            """处理删除错误"""
            try:
                os.chmod(path, 0o777)
                func(path)
            except Exception:
                pass

        shutil.rmtree(git_folder, onerror=on_rm_error)
        print(f"{Colors.SUCCESS}已清理 .git 文件夹")
        return True

    except Exception as e:
        print(f"{Colors.WARNING}无法清理 .git 文件夹: {e}")
        return False


def create_skill_structure(skill_name: str, target_dir: Path) -> Dict[str, Path]:
    """
    创建技能目录结构

    Args:
        skill_name: 技能名称
        target_dir: 目标目录

    Returns:
        创建的目录路径字典
    """
    paths = {
        "skill": target_dir,
        "src": target_dir / "src",
        "scripts": target_dir / "scripts",
    }

    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)

    return paths


def create_default_files(
    skill_name: str,
    repo_url: str,
    paths: Dict[str, Path],
    language: Optional[str] = None,
    custom_template_path: Optional[str] = None,
    description: Optional[str] = None,
    entry_file: Optional[str] = None,
) -> None:
    """
    创建默认文件

    Args:
        skill_name: 技能名称
        repo_url: 仓库 URL
        paths: 路径字典
        language: 编程语言
        custom_template_path: 自定义模板路径
        description: 项目描述
        entry_file: 入口文件路径
    """
    # 1. 创建 SKILL.md
    skill_md_path = paths["skill"] / "SKILL.md"
    template = generate_skill_template(
        skill_name, repo_url, language, custom_template_path, entry_file, description
    )
    with open(skill_md_path, "w", encoding="utf-8") as f:
        f.write(template)
    print(f"{Colors.SUCCESS}已创建 SKILL.md")

    # 2. 创建 .gitignore
    gitignore_path = paths["skill"] / ".gitignore"
    gitignore_content = """# GitHub Skill Forge - Default .gitignore

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Node.js
node_modules/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Trae
.trae/skills/*
!/.trae/skills/README.md
"""
    with open(gitignore_path, "w", encoding="utf-8") as f:
        f.write(gitignore_content)
    print(f"{Colors.SUCCESS}已创建 .gitignore")

    # 3. 创建 requirements.txt（如果不存在）
    src_requirements = paths["src"] / "requirements.txt"
    if not src_requirements.exists():
        # 检查是否需要创建
        if any(
            (paths["src"] / f).exists()
            for f in ["setup.py", "pyproject.toml", "Pipfile"]
        ):
            src_requirements.touch()
            print(f"{Colors.SUCCESS}已创建 requirements.txt 占位符")

    # 4. 创建 README.md（技能库说明）
    readme_path = paths["skill"].parent / "README.md"
    if not readme_path.exists():
        readme_content = f"""# Trae Skills

This directory contains {skill_name} skill generated by GitHub Skill Forge.

## Skills

- **{skill_name}**: {repo_url}

---
Generated by [GitHub Skill Forge](https://github.com)
"""
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)


def create_online_context_bundle(
    online_data: Dict[str, Any],
    output_path: Path,
    config: ForgeConfig,
) -> None:
    """
    基于在线数据创建上下文聚合文件
    """
    content = []

    # 1. 项目结构
    content.append(f"{Colors.HEADER}项目结构 (全在线递归扫描){Colors.RESET}")
    content.append("```")
    # 排序树结构
    tree = sorted(online_data.get("tree", []))
    content.append("\n".join(tree))
    content.append("```\n")

    # 2. 编程语言
    lang = online_data.get("language", "Unknown")
    content.append(f"{Colors.HEADER}主要语言: {Colors.RESET}{lang}\n")

    # 3. 关键文档
    content.append(f"{Colors.HEADER}关键文档内容{Colors.RESET}")
    for name, text in online_data.get("key_docs", {}).items():
        content.append(f"\n{Colors.HEADER}文件: {name}{Colors.RESET}")
        if len(text) > config.max_doc_size:
            text = text[:config.max_doc_size] + f"\n\n{Colors.YELLOW}... (文档截断){Colors.RESET}"
        content.append(text)
        content.append("\n" + "-" * 60 + "\n")

    # 4. 核心代码预览
    if online_data.get("core_code"):
        content.append(f"\n{Colors.HEADER}核心代码预览 (Top 100 Lines){Colors.RESET}")
        for name, code in online_data.get("core_code", {}).items():
            ext = name.split(".")[-1] if "." in name else ""
            content.append(f"\n{Colors.HEADER}文件: {name}{Colors.RESET}")
            content.append(f"```{ext}")
            content.append(code)
            content.append("```\n")

    # 5. 入口文件预览 (在线版)
    if online_data.get("entry_files"):
        content.append(f"\n{Colors.HEADER}入口文件预览 (Top 100 Lines){Colors.RESET}")
        for name, code in online_data.get("entry_files", {}).items():
            ext = name.split(".")[-1] if "." in name else ""
            content.append(f"\n{Colors.HEADER}文件: {name}{Colors.RESET}")
            content.append(f"```{ext}")
            content.append(code)
            content.append("```\n")

    # 5. 依赖项
    content.append(f"\n{Colors.HEADER}依赖项详情{Colors.RESET}")
    for name, text in online_data.get("dependencies", {}).items():
        content.append(f"\n{Colors.HEADER}{name}{Colors.RESET}")
        content.append("```")
        content.append(text)
        content.append("```\n")

    # 写入文件
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(content))

    print(f"{Colors.SUCCESS}已生成在线上下文包: {output_path}")


def process_single_repository(
    url: str, skill_name: Optional[str], config: ForgeConfig, base_output_dir: Path
) -> bool:
    """
    处理单个仓库 (全在线模式，带克隆回退)
    """
    print(f"\n{Colors.HEADER}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.HEADER}处理仓库: {url}{Colors.RESET}")
    print(f"{Colors.HEADER}{'=' * 60}{Colors.RESET}")

    # 1. 验证 URL
    if not validate_url(url):
        print(f"{Colors.ERROR}无效的 GitHub URL: {url}")
        return False

    # 3. 确定技能名称
    if skill_name is None:
        try:
            _, repo_name = get_repo_info(url)
            skill_name = f"{repo_name}-skill"
        except Exception:
            skill_name = f"{get_repo_name(url)}-skill"

    target_dir = base_output_dir / skill_name
    
    # [Debug] 打印生成的 target_dir
    print(f"{Colors.INFO}目标技能目录: {target_dir}")
    
    paths = create_skill_structure(skill_name, target_dir)

    # 4. 检查安全性
    repo_description = None
    if not config.no_safety_check:
        print(f"{Colors.INFO}检查仓库安全性 (阈值: {config.min_stars} Stars)...")
        try:
            is_safe, safety_info, repo_description = check_repository_safety(url, config)
            if not is_safe:
                print(f"{Colors.WARNING}金标筛选未通过: {safety_info}")
                if not config.force:
                    print(f"{Colors.INFO}使用 --force 强制继续")
                    return False
                else:
                    print(f"{Colors.WARNING}已使用 --force，忽略安全警告继续...")
            else:
                print(f"{Colors.SUCCESS}金标验证成功: {safety_info}")
        except Exception as e:
            print(f"{Colors.WARNING}无法在线检查安全性，将跳过此步: {e}")

    # 5. 试运行模式
    if config.dry_run:
        print(f"{Colors.INFO}试运行模式 - 以下操作将被执行:")
        print(f"  1. 在线扫描 {url}")
        print(f"  2. 创建目录结构: {target_dir}")
        print(f"  3. 生成 context_bundle.md")
        return True

    # 6. 在线扫描仓库 (尝试在线模式)
    online_success = False
    try:
        print(f"{Colors.PROGRESS}嘗試全在線掃描模式 (Zero-Clone)...")
        online_data = online_repo_scanner(url, config)
        
        # 验证是否真的抓到了数据 (tree 不应为空)
        if online_data and online_data.get("tree"):
            # 获取入口文件路径用于 SKILL.md
            entry_file = None
            if online_data.get("entry_files"):
                entry_file = list(online_data["entry_files"].keys())[0]

            # 创建上下文包 (在线版)
            bundle_path = paths["skill"] / "context_bundle.md"
            create_online_context_bundle(online_data, bundle_path, config)
            
            # 创建默认文件
            language = online_data.get("language")
            create_default_files(
                skill_name, 
                url, 
                paths, 
                language, 
                config.custom_template_path,
                description=repo_description,
                entry_file=entry_file
            )
            online_success = True
            
            # 在線模式下，如果路徑中意外產生了 src 且不為空，也進行清理（保持純淨）
            src_dir = paths["src"]
            if src_dir.exists() and any(src_dir.iterdir()):
                print(f"{Colors.INFO}正在清理在线模式产生的残留文件...")
                try:
                    def on_rm_error(func, path, exc_info):
                        os.chmod(path, 0o777)
                        func(path)
                    shutil.rmtree(src_dir, onerror=on_rm_error)
                    src_dir.mkdir(parents=True, exist_ok=True) # 保持目錄結構但清空內容
                except Exception:
                    pass

            print(f"{Colors.SUCCESS}全在线扫描成功！")
        else:
            print(f"{Colors.WARNING}在线扫描未返回有效数据，可能由于速率限制或仓库为空。")
    except Exception as e:
        print(f"{Colors.WARNING}全在线扫描失败: {e}")
        if config.verbose:
            import traceback
            traceback.print_exc()

    # 7. 保底方案: 自动回退到最小化克隆模式
    if not online_success:
        print(f"\n{Colors.WARNING}正在執行保底方案: 最小化克隆模式 (Clone Depth 1)...")
        
        # 重新创建/清理 src 目录
        src_dir = paths["src"]
        if src_dir.exists():
            try:
                def on_rm_error(func, path, exc_info):
                    os.chmod(path, 0o777)
                    func(path)
                shutil.rmtree(src_dir, onerror=on_rm_error)
            except Exception:
                pass
        src_dir.mkdir(parents=True, exist_ok=True)
        
        # [Debug] 强制打印克隆前的状态
        print(f"{Colors.INFO}準備克隆到: {src_dir.absolute()}")
        
        if clone_repository(url, src_dir, config):
            # 清理 .git
            cleanup_git_folder(src_dir)
            
            # 扫描本地代码生成聚合文件
            bundle_path = paths["skill"] / "context_bundle.md"
            create_context_bundle(
                src_dir,
                bundle_path,
                config.max_file_count,
                config.max_doc_size,
                config.skip_patterns
            )
            
            # 检测语言并生成默认文件
            language = detect_programming_language(src_dir)
            
            # 本地模式也嘗試找入口文件
            entry_file = None
            entry_points_list = [
                "__main__.py", "main.py", "app.py", "index.js", "main.js", 
                "app.js", "index.ts", "main.go", "main.rs"
            ]
            for ep in entry_points_list:
                matches = list(src_dir.glob(f"**/{ep}"))
                if matches:
                    entry_file = str(matches[0].relative_to(src_dir))
                    break

            create_default_files(
                skill_name, 
                url, 
                paths, 
                language, 
                config.custom_template_path,
                description=repo_description,
                entry_file=entry_file
            )
            
            # 任務完成後，如果是保底克隆模式且配置了清理
            if src_dir.exists():
                print(f"{Colors.INFO}正在清理克隆的源代碼目錄...")
                try:
                    def on_rm_error(func, path, exc_info):
                        os.chmod(path, 0o777)
                        func(path)
                    shutil.rmtree(src_dir, onerror=on_rm_error)
                except Exception as e:
                    print(f"{Colors.WARNING}清理失敗: {e}")

            print(f"{Colors.SUCCESS}保底克隆模式成功完成！")
        else:
            print(f"{Colors.ERROR}所有尝试均已失败，请检查网络连接或仓库权限。")
            return False

    print(f"\n{Colors.SUCCESS}{'=' * 60}")
    print(f"{Colors.SUCCESS}技能锻造完成!")
    print(f"{Colors.SUCCESS}{'=' * 60}")
    print(f"{Colors.INFO}技能目录: {target_dir}")
    
    return True


def process_batch_file(
    batch_file: Path, config: ForgeConfig, base_output_dir: Path
) -> Tuple[int, int]:
    """
    批量处理仓库

    Args:
        batch_file: 批量文件路径
        config: 配置
        base_output_dir: 输出基础目录

    Returns:
        (成功数量, 失败数量)
    """
    if not batch_file.exists():
        print(f"{Colors.ERROR}批量文件不存在: {batch_file}")
        return 0, 0

    # 读取 URLs
    urls = []
    with open(batch_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)

    if not urls:
        print(f"{Colors.ERROR}批量文件中没有有效的 URL")
        return 0, 0

    print(f"{Colors.INFO}开始批量处理 {len(urls)} 个仓库...")

    success_count = 0
    fail_count = 0

    for i, line in enumerate(urls, 1):
        parts = line.split()
        url = parts[0]
        skill_name = parts[1] if len(parts) > 1 else None

        print(f"\n{Colors.HEADER}[{i}/{len(urls)}] 处理中{Colors.RESET}")

        if process_single_repository(url, skill_name, config, base_output_dir):
            success_count += 1
        else:
            fail_count += 1

    print(f"\n{Colors.HEADER}{'=' * 60}")
    print(f"{Colors.HEADER}批量处理完成{Colors.RESET}")
    print(f"{Colors.SUCCESS}成功: {success_count}")
    print(f"{Colors.ERROR}失败: {fail_count}")

    return success_count, fail_count


# ==================== 主函数 ====================
def parse_arguments() -> argparse.Namespace:
    """
    解析命令行参数

    Returns:
        参数命名空间
    """
    parser = argparse.ArgumentParser(
        description="GitHub Skill Forge - 将 GitHub 仓库转换为 Trae 技能",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 基本用法
    python forge.py https://github.com/username/repo
    
    # 指定技能名称
    python forge.py https://github.com/username/repo my-custom-skill
    
    # 强制覆盖已存在的技能
    python forge.py https://github.com/username/repo --force
    
    # 试运行模式
    python forge.py https://github.com/username/repo --dry-run
    
    # 批量处理
    python forge.py --batch urls.txt
    
    # 使用配置文件
    python forge.py https://github.com/username/repo --config .skill-forge.toml
    
    # 跳过安全检查
    python forge.py https://github.com/username/repo --no-safety-check
        """,
    )

    # 位置参数
    parser.add_argument("url", nargs="?", help="GitHub 仓库 URL")

    parser.add_argument(
        "skill_name", nargs="?", help="技能名称（可选，默认使用仓库名）"
    )

    # 可选参数
    parser.add_argument(
        "--batch",
        "-b",
        metavar="FILE",
        help="批量处理文件（每行一个 URL，可选技能名称用空格分隔）",
    )

    parser.add_argument(
        "--config", "-c", metavar="FILE", help="配置文件路径（支持 .skill-forge.toml）"
    )

    parser.add_argument(
        "--dry-run", "-n", action="store_true", help="试运行模式（不实际执行任何操作）"
    )

    parser.add_argument(
        "--force", "-f", action="store_true", help="强制覆盖已存在的技能目录"
    )

    parser.add_argument(
        "--no-safety-check", action="store_true", help="跳过仓库安全检查"
    )

    parser.add_argument(
        "--output", "-o", metavar="DIR", help="输出目录（默认: .trae/skills）"
    )

    parser.add_argument("--depth", type=int, default=1, help="Git 克隆深度（默认: 1）")

    parser.add_argument(
        "--max-retries", type=int, default=3, help="最大重试次数（默认: 3）"
    )

    parser.add_argument(
        "--timeout", type=int, default=60, help="超时时间（秒，默认: 60）"
    )

    parser.add_argument("--no-proxy", action="store_true", help="禁用代理模式")

    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    parser.add_argument(
        "--quiet", "-q", action="store_true", help="安静模式（减少输出）"
    )

    parser.add_argument("--version", action="version", version="%(prog)s v2.0")

    parser.add_argument(
        "--min-stars", type=int, default=20, help="金标筛选阈值（默认: 20 Stars）"
    )

    return parser.parse_args()


def main() -> int:
    """
    主函数

    Returns:
        退出码（0=成功，非0=失败）
    """

    # 设置信号处理
    def signal_handler(sig, frame):
        print(f"\n{Colors.WARNING}收到中断信号，正在退出...")
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 解析参数
    args = parse_arguments()

    # 加载配置
    config = ForgeConfig()

    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            config = ForgeConfig.load_from_file(config_path)

    # 应用命令行参数覆盖配置
    if args.dry_run:
        config.dry_run = True
    if args.force:
        config.force = True
    if args.no_proxy:
        config.proxy_enabled = False
    if args.verbose:
        config.verbose = True
    if args.quiet:
        config.quiet = True
    if args.depth:
        config.clone_depth = args.depth
    if args.max_retries:
        config.max_retries = args.max_retries
    if args.timeout:
        config.timeout = args.timeout
    if args.no_safety_check:
        config.no_safety_check = True
    if args.min_stars:
        config.min_stars = args.min_stars

    # 确定输出目录
    if args.output:
        output_dir = Path(args.output).resolve()
    else:
        script_dir = Path(__file__).parent.resolve()
        output_dir = script_dir.parent.parent.resolve()

    # 验证输出目录
    if not output_dir.exists():
        if config.dry_run:
            print(f"{Colors.INFO}试运行: 将创建目录 {output_dir}")
        else:
            try:
                output_dir.mkdir(parents=True)
                print(f"{Colors.SUCCESS}已创建输出目录: {output_dir}")
            except Exception as e:
                print(f"{Colors.ERROR}无法创建输出目录: {e}")
                return 1

    # 根据模式执行
    if args.batch:
        # 批量处理模式
        batch_file = Path(args.batch).resolve()
        success, fail = process_batch_file(batch_file, config, output_dir)
        return 1 if fail > 0 else 0

    elif args.url:
        # 单个仓库模式
        if process_single_repository(args.url, args.skill_name, config, output_dir):
            return 0
        else:
            return 1

    else:
        # 无参数或帮助
        parse_arguments()  # 显示帮助信息
        return 0


if __name__ == "__main__":
    sys.exit(main())
