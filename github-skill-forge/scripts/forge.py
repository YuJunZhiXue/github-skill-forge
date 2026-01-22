#!/usr/bin/env python3
"""
GitHub Skill Forge - 全功能自动化工具

这个脚本自动化了将任意 GitHub 仓库转换为标准化 Trae 技能的全过程。

## 核心功能
- 一键克隆 GitHub 仓库并自动创建标准技能目录结构
- 自动生成 Lite-RAG 上下文聚合文件
- 支持代理模式自动切换，解决网络访问问题
- 自动清理 .git 文件夹以减小存储体积
- 支持批量安装、自定义模板、强制覆盖等高级功能
- 提供智能错误处理和自动恢复机制

## 使用方法
    基本用法: python forge.py <github_url> [skill_name]
    批量安装: python forge.py --batch urls.txt
    试运行:   python forge.py <url> --dry-run
    强制覆盖: python forge.py <url> --force

## 配置文件
    支持 .skill-forge.toml 配置文件，配置项：
    - default_skill_name: 默认技能名称模板
    - skip_patterns: 跳过的文件模式
    - proxy_enabled: 是否启用代理
    - clone_depth: 克隆深度（默认1）
    - max_retries: 最大重试次数（默认3）
    - timeout: 超时时间（秒）

## 依赖文件支持
    自动检测并收集以下依赖文件：
    - requirements.txt / Pipfile / pyproject.toml (Python)
    - package.json (Node.js)
    - go.mod (Go)
    - Cargo.toml (Rust)
    - pom.xml / build.gradle (Java)
    - Gemfile (Ruby)

## 作者
    LO (https://github.com/)

## 版本
    v2.0 (2026-01)
"""

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

    # 代理配置
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

    Args:
        url: 要验证的 URL

    Returns:
        URL 是否有效
    """
    # GitHub URL 模式
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


def check_repository_safety(url: str) -> Tuple[bool, str]:
    """
    检查仓库安全性

    Args:
        url: GitHub 仓库 URL

    Returns:
        (是否安全, 安全信息)
    """
    try:
        # 提取 owner/repo
        parts = url.rstrip("/").split("/")
        if len(parts) < 2:
            return False, "无效的 URL 格式"

        owner = parts[-2]
        repo = parts[-1].replace(".git", "")

        # 获取仓库信息（使用 GitHub API）
        api_url = f"https://api.github.com/repos/{owner}/{repo}"

        req = urllib.request.Request(
            api_url, headers={"User-Agent": "GitHub-Skill-Forge"}
        )
        req.timeout = 10  # 设置超时

        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())

            stars = data.get("stargazers_count", 0)
            forks = data.get("forks_count", 0)
            updated_at = data.get("updated_at", "")

            # 检查是否活跃（最近一次更新在一年内）
            is_active = True
            if updated_at:
                # 解析更新时间（处理时区）
                try:
                    last_update = datetime.fromisoformat(
                        updated_at.replace("Z", "+00:00")
                    )
                    # 使用 UTC 时间进行比较
                    now = (
                        datetime.now(last_update.tzinfo)
                        if last_update.tzinfo
                        else datetime.now()
                    )
                    is_active = (now - last_update).days < 365
                except Exception:
                    is_active = True  # 解析失败时假设活跃

            # 生成安全报告
            safety_info = []
            safety_info.append(f"Stars: {stars:,}")
            safety_info.append(f"Forks: {forks:,}")
            safety_info.append(f"状态: {'活跃' if is_active else '不活跃'}")
            safety_info.append(
                f"许可证: {data.get('license', {}).get('spdx_id', '未知')}"
            )

            # 基础安全检查
            if stars < 10:
                return (
                    False,
                    f"仓库Stars数量过低，可能不够安全。详情: {'; '.join(safety_info)}",
                )

            return True, "; ".join(safety_info)

    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False, "仓库不存在或无法访问"
        return False, f"HTTP 错误: {e.code}"
    except Exception as e:
        return False, f"检查失败: {str(e)}"


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

    # 5. 主要入口文件
    content.append(f"\n{Colors.HEADER}主要入口文件{Colors.RESET}")
    entry_points = ["__main__.py", "main.py", "app.py", "index.js", "main.go", "lib.rs"]

    for entry in entry_points:
        entry_path = src_dir / entry
        if entry_path.exists():
            try:
                with open(entry_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()[:50]  # 只读取前50行
                    content.append(f"\n{Colors.HEADER}{entry}{Colors.RESET}")
                    content.append("```python")
                    content.extend(lines)
                    content.append("```\n")
            except Exception as e:
                content.append(
                    f"\n{Colors.WARNING}无法读取 {entry}: {e}{Colors.RESET}\n"
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
) -> str:
    """
    生成技能模板

    Args:
        skill_name: 技能名称
        repo_url: 仓库 URL
        language: 编程语言
        custom_template_path: 自定义模板路径

    Returns:
        SKILL.md 内容
    """
    # 优先使用自定义模板
    if custom_template_path:
        template_path = Path(custom_template_path)
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                template = f.read()
                # 替换变量
                template = template.replace("{{skill_name}}", skill_name)
                template = template.replace("{{repo_url}}", repo_url)
                template = template.replace("{{language}}", language or "Unknown")
                return template

    # 默认模板
    base_template = f"""---
name: {skill_name}
description: [DRAFT] Generated from {repo_url}.
---

# {skill_name}

> Auto-generated by GitHub Skill Forge

## 状态
**上下文已加载**: 查看 `context_bundle.md` 了解完整项目详情。

## 功能概述

### 编程语言
{language or "Unknown"}

### 主要功能
（请根据 context_bundle.md 填写）

## 使用方法

### 基本用法

```bash
# 请根据实际入口文件调整
python3 src/main.py --help
```

## 依赖项

### 安装依赖

```bash
# Python
pip install -r requirements.txt

# Node.js
npm install

# Go
go mod download

# Rust
cargo build --release
```

## 高级用法

### 配置选项

### 命令行参数

## 示例

### 示例 1

```bash
python3 src/main.py example
```

## 故障排除

### 常见问题

#### 问题 1

**症状**: 

**解决方案**: 

## 源信息

- 仓库: {repo_url}
- 本地路径: ./src/
- 语言: {language or "Unknown"}

## 下一步（Agent 任务）

1. 阅读 `context_bundle.md` 了解完整项目信息
2. 理解工具的用途和使用方法
3. 重写此 SKILL.md，添加清晰的"使用示例"和"依赖项"部分
4. 如有必要，在 `scripts/` 目录创建包装脚本
5. 验证工具功能正常
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

    # 尝试克隆
    clone_urls = []

    if config.proxy_enabled:
        # 代理 URL
        proxy_url = url.replace("github.com", config.proxy_url)
        clone_urls.append(proxy_url)

    # 原始 URL
    clone_urls.append(url)

    for attempt in range(config.max_retries):
        for clone_url in clone_urls:
            print(
                f"{Colors.PROGRESS}尝试克隆 ({attempt + 1}/{config.max_retries}): {clone_url}"
            )

            try:
                # 构建 git 命令
                cmd = [
                    "git",
                    "clone",
                    "--depth",
                    str(config.clone_depth),
                    clone_url,
                    str(target_dir),
                ]

                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=config.timeout
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
        "references": target_dir / "references",
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
) -> None:
    """
    创建默认文件

    Args:
        skill_name: 技能名称
        repo_url: 仓库 URL
        paths: 路径字典
        language: 编程语言
        custom_template_path: 自定义模板路径
    """
    # 1. 创建 SKILL.md
    skill_md_path = paths["skill"] / "SKILL.md"
    template = generate_skill_template(
        skill_name, repo_url, language, custom_template_path
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


def process_single_repository(
    url: str, skill_name: Optional[str], config: ForgeConfig, base_output_dir: Path
) -> bool:
    """
    处理单个仓库

    Args:
        url: 仓库 URL
        skill_name: 技能名称（可选）
        config: 配置
        base_output_dir: 输出基础目录

    Returns:
        是否处理成功
    """
    print(f"\n{Colors.HEADER}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.HEADER}处理仓库: {url}{Colors.RESET}")
    print(f"{Colors.HEADER}{'=' * 60}{Colors.RESET}")

    # 1. 验证 URL
    if not validate_url(url):
        print(f"{Colors.ERROR}无效的 GitHub URL: {url}")
        return False

    # 2. 确定技能名称
    if skill_name is None:
        skill_name = config.default_skill_name.format(repo_name=get_repo_name(url))

    # 3. 检查安全性（如果启用）
    if not config.quiet:
        print(f"{Colors.INFO}检查仓库安全性...")
        is_safe, safety_info = check_repository_safety(url)
        if not is_safe:
            print(f"{Colors.WARNING}安全警告: {safety_info}")
            if not config.force:
                print(f"{Colors.INFO}使用 --force 强制继续")
                return False
        else:
            print(f"{Colors.SUCCESS}安全检查通过: {safety_info}")

    # 4. 试运行模式
    if config.dry_run:
        print(f"{Colors.INFO}试运行模式 - 以下操作将被执行:")
        print(f"  1. 克隆 {url}")
        print(f"  2. 创建目录结构: {base_output_dir / skill_name}")
        print(f"  3. 生成 context_bundle.md")
        print(f"  4. 生成 SKILL.md")
        return True

    # 5. 创建目录结构
    target_dir = base_output_dir / skill_name
    paths = create_skill_structure(skill_name, target_dir)
    print(f"{Colors.SUCCESS}已创建目录结构: {target_dir}")

    # 6. 克隆仓库
    if not clone_repository(url, paths["src"], config):
        print(f"{Colors.ERROR}克隆失败")
        # 清理已创建的目录
        if target_dir.exists():
            shutil.rmtree(target_dir)
        return False

    # 7. 清理 .git 文件夹
    cleanup_git_folder(paths["src"])

    # 8. 检测编程语言
    language = detect_programming_language(paths["src"])
    if language:
        print(f"{Colors.SUCCESS}检测到编程语言: {language}")

    # 9. 创建上下文包
    bundle_path = paths["skill"] / "context_bundle.md"
    create_context_bundle(
        paths["src"],
        bundle_path,
        config.max_file_count,
        config.max_doc_size,
        config.skip_patterns,
    )

    # 10. 创建默认文件
    create_default_files(skill_name, url, paths, language, config.custom_template_path)

    print(f"\n{Colors.SUCCESS}{'=' * 60}")
    print(f"{Colors.SUCCESS}技能锻造成功!")
    print(f"{Colors.SUCCESS}{'=' * 60}")
    print(f"{Colors.INFO}技能目录: {target_dir}")
    print(f"{Colors.INFO}下一步操作:")
    print(f"  1. 阅读 {bundle_path}")
    print(f"  2. 更新 {paths['skill'] / 'SKILL.md'}")
    print(f"  3. 验证工具功能")

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
