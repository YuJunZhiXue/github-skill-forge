---
name: github-skill-forge
description: 一个"制造技能的技能"。这个工具自动化了将任意 GitHub 仓库转换为标准化 Trae 技能的全过程，是扩展 AI Agent 能力的核心工具。
tags: ["github", "skill-forge", "meta-skill", "automation", "integration", "CLI", "scaffolding",
  "Lite-RAG", "context-aggregation", "repository-clone", "skill-management", "tool-integration",
  "开源集成", "技能锻造", "元技能", "自动化工具", "CLI工具集成", "脚手架", "上下文聚合",
  "工具安装", "GitHub工具", "能力扩展", "智能代理", "工作流自动化"
]
---

# GitHub 技能锻造厂

一个"制造技能的技能"。这个工具自动化了将 GitHub 仓库转换为标准化 Trae 技能的过程。

## 核心功能

### 1. 自动化脚手架
- 一键克隆 GitHub 仓库
- 自动创建标准技能目录结构
- 自动生成上下文聚合文件

### 2. Lite-RAG 上下文聚合
- 自动提取项目文件树结构
- 自动解析 README 和文档
- 自动收集依赖项信息（requirements.txt, package.json, pyproject.toml）
- 生成单一上下文文件供 Agent 快速理解

### 3. 智能错误处理
- 代理模式自动切换
- 目录存在性检测
- Git 克隆失败自动重试

### 4. 标准化输出
- 自动生成符合规范的技能结构
- 统一的目录布局（scripts/, references/, context_bundle.md）
- 预置 SKILL.md 模板

## 快速开始

### 安装要求

```bash
# 基础依赖
Python 3.7+
Git
```

### 基本使用

```bash
# 语法: python scripts/forge.py <URL> [SKILL_NAME]
python3 .trae/skills/github-skill-forge/scripts/forge.py "https://github.com/username/repo"
```

## 使用场景

- 当你想使用在 GitHub 上找到的工具时
- 当用户发送 GitHub 链接并说"我想用这个"时
- 需要"安装"新功能到 `.trae/skills` 库时
- 需要快速集成开源工具到工作流时
- 需要标准化团队工具使用规范时

## 工作流程

### 步骤 1：锻造框架
运行脚手架脚本来克隆仓库、创建结构并生成上下文包。

```bash
# 基础用法
python3 .trae/skills/github-skill-forge/scripts/forge.py "https://github.com/username/repo"

# 指定技能名称
python3 .trae/skills/github-skill-forge/scripts/forge.py "https://github.com/username/repo" "my-custom-skill"
```

### 步骤 2：分析与定稿（AI 任务）
脚本会在新的技能文件夹中生成 `context_bundle.md`。你（作为 Agent）必须：

1. **读取上下文包**：查看 `context_bundle.md`
   - 这个文件包含文件树、README 和依赖项
   - 不需要手动搜索文件
   - 建议限制读取前 500 行开始

2. **更新 SKILL.md**：重写新技能目录中的草稿
   - **描述**：总结工具的功能
   - **先决条件**：列出安装命令（如 `pip install -r src/requirements.txt`）
   - **用法**：提供使用 `src/...` 运行工具的清晰示例

3. **创建包装脚本（可选）**：
   - 如果工具需要复杂参数，在 `.trae/skills/<new_skill>/scripts/` 中编写简化的 Python/Shell 脚本

### 步骤 3：验证
运行工具的帮助命令以确保其正常工作。

```bash
python3 .trae/skills/<new_skill>/src/<main_script>.py --help
```

## 使用示例

### 示例 1：基础使用

用户："安装这个仓库：https://github.com/sqlmapproject/sqlmap"

Agent 操作：
1. 运行锻造脚本
   ```
   python3 .trae/skills/github-skill-forge/scripts/forge.py https://github.com/sqlmapproject/sqlmap
   ```
2. Agent 读取上下文包
   ```
   read .trae/skills/sqlmap/context_bundle.md
   ```
3. Agent 编辑 SKILL.md
   ```
   edit .trae/skills/sqlmap/SKILL.md
   ```
4. Agent 运行验证
   ```
   python3 .trae/skills/sqlmap/src/sqlmap.py --help
   ```

### 示例 2：指定技能名称

```bash
python3 .trae/skills/github-skill-forge/scripts/forge.py "https://github.com/requests/requests" "http-requests-lib"
```

这将创建一个名为 `http-requests-lib` 的技能目录。

### 示例 3：复杂项目

用户："我想用这个工具做数据可视化：https://github.com/mwaskom/seaborn"

Agent 操作：
1. 运行锻造脚本
2. 读取 `context_bundle.md` 了解 seaborn 的 API
3. 识别依赖项（numpy, pandas, matplotlib）
4. 编写简化的使用脚本到 `scripts/` 目录
5. 更新 SKILL.md 添加使用示例

### 示例 4：CLI 工具安装

用户："我想用 fzf 这样的模糊查找工具：https://github.com/junegunn/fzf"

Agent 操作：
1. 运行锻造脚本
2. 分析 fzf 的功能：
   - 读取 context_bundle.md 了解核心功能
   - 识别依赖（Go 环境）
   - 了解安装方式（多平台支持）
3. 创建简化的使用脚本：
   - `scripts/fuzzy-search.py` - 简化文件搜索
   - `scripts/history-search.py` - 命令历史搜索
4. 更新 SKILL.md：
   ```markdown
   ## 使用方法
   
   ### 基本文件搜索
   ```bash
   python3 scripts/fuzzy-search.py
   ```
   
   ### 命令历史搜索
   ```bash
   python3 scripts/history-search.py
   ```
   
   ## 依赖项
   
   - Go 1.22+（从源码编译）
   - 或使用预编译二进制文件
   
   ## 安装命令
   
   ```bash
   # macOS
   brew install fzf
   
   # Linux
   sudo apt install fzf
   
   # Windows
   choco install fzf
   ```
   ```

### 示例 5：数据处理工具

用户："安装 jq 这样的 JSON 处理工具：https://github.com/jqlang/jq"

Agent 操作：
1. 运行锻造脚本
2. 读取 context_bundle.md
3. 创建简化的包装脚本：
   - `scripts/json-format.py` - JSON 格式化
   - `scripts/json-query.py` - JSON 查询工具
4. 更新 SKILL.md：
   ```markdown
   ## 使用示例
   
   ### 格式化 JSON
   ```bash
   cat data.json | python3 scripts/json-format.py
   ```
   
   ### 查询 JSON 路径
   ```bash
   python3 scripts/json-query.py "data.json" ".users[0].name"
   ```
   ```

## 高级用法

### 手动创建上下文包

如果需要重新生成上下文包：

```python
from forge import create_context_bundle
create_context_bundle("./src", "./context_bundle.md")
```

### 自定义文件树限制

修改 `forge.py` 中的 `limit` 参数：
```python
def get_file_tree(start_path, limit=100):  # 增加限制到 100 个文件
    ...
```

### 批量安装多个技能

```bash
# 创建一个批量安装脚本
for url in "https://github.com/fzf" "https://github.com/jqlang/jq" "https://github.com/sharkdp/bat"; do
    python3 .trae/skills/github-skill-forge/scripts/forge.py "$url"
done
```

### 自定义模板

你可以通过环境变量定制生成的内容：

```bash
# 自定义默认技能名
export SKILL_FORCE_NAME="custom-skill"

# 自定义文件限制
export SKILL_FILE_LIMIT=100

# 自定义文档截断大小
export SKILL_DOC_TRUNCATE=20000
```

## 故障排除

### 问题 1：克隆失败

**症状**：
```
❌ Git clone failed: fatal: Could not read from remote repository.
```

**解决方案**：
1. 检查 URL 是否正确
2. 确保网络连接正常
3. 尝试使用代理模式（脚本自动处理）
4. 验证 Git 认证（如果需要）
   ```bash
   git config --global credential.helper store
   ```

### 问题 2：目录已存在

**症状**：
```
⚠️  Warning: Skill directory 'xxx' already exists.
❌ Aborting: Directory exists.
```

**解决方案**：
1. 使用不同的技能名称
   ```bash
   python3 forge.py <URL> new_skill_name
   ```
2. 或手动删除已存在的目录后重试
   ```bash
   rm -rf .trae/skills/xxx
   ```

### 问题 3：依赖项缺失

**症状**：
```
ModuleNotFoundError: No module named 'xxx'
```

**解决方案**：
1. 在 SKILL.md 中明确列出依赖项
2. 提供安装命令
3. 创建 requirements.txt（如果原项目没有）
4. 检查 Python 版本兼容性

### 问题 4：上下文包过大

**症状**：
生成的 `context_bundle.md` 超过预期大小

**解决方案**：
脚本已自动截断超过 10KB 的文档，如需更详细的上下文可手动查看源文件。

### 问题 5：权限错误

**症状**：
```
Permission denied: '.trae/skills/xxx'
```

**解决方案**：
1. 检查目录权限
   ```bash
   ls -la .trae/skills/
   ```
2. 修复权限
   ```bash
   chmod -R 755 .trae/skills/
   ```

### 问题 6：Git LFS 文件

**症状**：
```
Git LFS: (1 of 1 files) 0 B / 100.00 MB
```

**解决方案**：
1. 安装 Git LFS
   ```bash
   git lfs install
   ```
2. 手动拉取 LFS 文件
   ```bash
   git lfs pull
   ```

## 最佳实践

### 1. 技能命名规范
- 使用小写字母和连字符
- 长度控制在 3-50 个字符
- 避免使用保留字

### 2. SKILL.md 编写规范
- 保持简洁，只包含必要信息
- 详细内容放在 `context_bundle.md`
- 使用中文标题，英文命令
- 提供可执行的示例代码

### 3. 包装脚本创建
- 简化复杂命令行接口
- 提供默认参数
- 添加错误处理
- 支持 `-h/--help` 参数

### 4. 依赖项管理
- 明确列出所有依赖
- 指定版本范围
- 提供多平台安装方式

### 5. 验证测试
- 在发布前运行所有示例
- 测试不同操作系统
- 验证依赖安装正确性

## 技能结构规范

### 标准目录结构

```
.trae/skills/
└── <skill-name>/
    ├── SKILL.md           # 技能说明文档
    ├── context_bundle.md  # 上下文聚合（自动生成）
    ├── requirements.txt   # 依赖项（可选）
    ├── src/              # 源代码
    │   └── <main-script>
    ├── scripts/          # 包装脚本（可选）
    │   └── <helper-scripts>
    └── references/       # 参考文档（可选）
        └── <documentation>
```

### SKILL.md 模板

```markdown
---
name: <skill-name>
description: <简短描述>
---

# <技能名称>

## 功能特性
- <特性1>
- <特性2>

## 使用要求
- <依赖项1>
- <依赖项2>

## 安装方法
```bash
<安装命令>
```

## 使用方法
### 基本用法
```bash
<基本命令>
```

## 高级用法
### <高级功能>
```bash
<高级命令>
```

## 故障排除
### 问题
<解决方案>

## 更新日志
- <版本>：<更新内容>
```

## 性能优化

### 1. 减少克隆深度
```bash
# 使用浅克隆
git clone --depth 1 <url>
```

### 2. 跳过不必要的文件
```python
# 在 forge.py 中添加
SKIP_DIRS = ['.git', '.github', 'docs', 'test']
SKIP_FILES = ['*.md', '*.txt']
```

### 3. 并行处理
```python
# 使用多线程处理多个任务
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor() as executor:
    executor.submit(process_file, file1)
    executor.submit(process_file, file2)
```

## 安全性考虑

### 1. 验证仓库来源
- 检查仓库的 stars 和 forks 数量
- 查看最近的提交记录
- 检查维护者的活跃度

### 2. 依赖项安全
- 检查已知漏洞
- 使用依赖扫描工具
- 定期更新依赖

### 3. 代码执行安全
- 在隔离环境中测试
- 限制文件系统访问
- 记录所有操作日志

## 集成建议

### 1. CI/CD 集成
```yaml
# .github/workflows/skill-test.yml
name: Test Skills
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Test skill
        run: python3 src/main.py --help
```

### 2. 自动化更新
```bash
# 定期更新技能脚本
0 0 * * 0 cd /path/to/skills && python3 github-skill-forge/scripts/forge.py <url>
```

## 相关资源

- [fzf - 命令行模糊查找器](https://github.com/junegunn/fzf)
- [awesome-cli-apps - CLI 应用精选](https://github.com/agarrharr/awesome-cli-apps)
- [GitHub CLI 官方文档](https://cli.github.com/)

## 注意事项

- 脚本会删除克隆仓库中的 `.git` 文件夹以减小体积
- 代理模式使用 gitclone.com 作为代理服务
- 建议在运行前确认 URL 的正确性
- 大型仓库可能需要较长时间克隆
- 建议定期更新 github-skill-forge 本身
- 在生产环境使用前先进行测试