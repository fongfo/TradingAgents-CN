# Conda 环境设置指南

本指南将帮助您使用 conda 创建独立的 Python 环境来运行 TradingAgents-CN 项目。

## 前置要求

### 选择安装类型：Anaconda vs Miniconda

#### Anaconda Distribution（完整版）
- **大小**: 约 500MB - 1GB
- **包含内容**: 
  - conda 包管理器
  - Python 解释器
  - 150+ 预装的科学计算包（NumPy, Pandas, Matplotlib, Jupyter 等）
  - Anaconda Navigator（图形界面）
  - Spyder IDE
- **适用场景**: 
  - 需要立即使用大量科学计算包
  - 喜欢图形界面管理环境
  - 不介意较大的安装体积
- **下载地址**: https://www.anaconda.com/download

#### Miniconda（精简版）⭐ **推荐**
- **大小**: 约 50MB - 100MB
- **包含内容**: 
  - conda 包管理器
  - Python 解释器
  - 仅基础工具（无预装包）
- **适用场景**: 
  - 项目已有完整的依赖列表（如本项目有 `environment.yml`）
  - 希望最小化安装体积
  - 需要更快的安装速度
  - 更灵活的环境管理
- **下载地址**: https://docs.conda.io/en/latest/miniconda.html

#### 推荐选择

**对于本项目（TradingAgents-CN），推荐使用 Miniconda**，原因：
1. ✅ 项目已提供完整的 `environment.yml` 依赖配置
2. ✅ 安装体积小，下载和安装更快
3. ✅ 只安装项目实际需要的包，避免不必要的依赖
4. ✅ 环境更干净，减少包冲突的可能性

**如果您是数据科学初学者或需要频繁使用 Jupyter Notebook**，可以选择 Anaconda。

### 安装步骤

1. **下载并安装 Miniconda（推荐）**
   - 访问：https://docs.conda.io/en/latest/miniconda.html
   - 选择对应操作系统的安装包（Windows/Mac/Linux）
   - 运行安装程序
   - ⚠️ **重要**: 安装时勾选 "Add Miniconda to PATH"（Windows）或选择 "Initialize conda"（Mac/Linux）

2. **验证 conda 安装**
   ```bash
   conda --version
   ```
   如果显示版本号（如 `conda 24.x.x`），说明安装成功。

## 创建环境

### 方法一：使用 environment.yml 文件（推荐）

项目根目录已包含 `environment.yml` 文件，使用以下命令创建环境：

```bash
# 创建环境
conda env create -f environment.yml

# 激活环境
conda activate tradingagents
```

### 方法二：手动创建环境

如果您想手动创建环境并逐步安装依赖：

```bash
# 创建新的 conda 环境，指定 Python 版本
conda create -n tradingagents python=3.10

# 激活环境
conda activate tradingagents

# 安装项目依赖（使用 pip）
pip install -e .
```

## 环境管理命令

### 激活环境
```bash
conda activate tradingagents
```

### 停用环境
```bash
conda deactivate
```

### 查看所有环境
```bash
conda env list
```

### 更新环境
如果 `environment.yml` 文件有更新，可以使用以下命令更新环境：
```bash
conda env update -f environment.yml --prune
```

### 删除环境
```bash
conda env remove -n tradingagents
```

### 导出环境
如果您修改了环境并想保存配置：
```bash
conda env export > environment.yml
```

## 在环境中运行项目

激活环境后，您可以正常运行项目：

```bash
# 激活环境
conda activate tradingagents

# 运行项目
python main.py
```

## 常见问题

### 1. conda 命令未找到

**Windows:**
- 确保在安装 Anaconda/Miniconda 时选择了"Add to PATH"选项
- 或者使用 Anaconda Prompt 而不是普通的 PowerShell/CMD

**Linux/Mac:**
- 初始化 conda：
  ```bash
  conda init bash  # 对于 bash
  conda init zsh   # 对于 zsh
  ```
- 重新启动终端或运行 `source ~/.bashrc` (bash) 或 `source ~/.zshrc` (zsh)

### 2. 环境创建失败

- 检查网络连接（conda 需要下载包）
- 尝试使用国内镜像源：
  ```bash
  conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
  conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free
  conda config --set show_channel_urls yes
  ```

### 3. 包安装冲突

如果遇到包版本冲突，可以：
- 使用 `conda env update` 更新环境
- 或者删除环境后重新创建

## 使用 conda 的优势

1. **隔离性**: 每个项目有独立的 Python 环境和依赖
2. **版本管理**: 可以轻松管理不同 Python 版本
3. **跨平台**: 在 Windows、Linux、Mac 上都能使用
4. **依赖管理**: 自动处理依赖冲突

## 与虚拟环境的区别

- **conda**: 可以管理 Python 版本和系统级依赖（如 C 库）
- **venv/virtualenv**: 只能管理 Python 包，不能管理 Python 版本

对于需要特定系统依赖或跨平台开发的项目，conda 是更好的选择。

