# 图片地址替换工具

这是一个自动化工具，可以将文档中的图片地址替换为微信公众号图片地址。工具会自动下载原始图片，上传到微信公众号后台，然后替换文档中的图片链接。

## 功能特性

- 🔍 **智能提取**: 从多种文档格式中提取图片URL（支持 .txt, .md, .html, .htm）
- 📥 **批量下载**: 并发下载图片，支持重试机制
- ☁️ **微信上传**: 自动上传图片到微信公众号，支持永久和临时素材
- 🔄 **智能替换**: 在文档中精确替换图片地址
- 📊 **详细报告**: 生成完整的处理报告
- 🛡️ **安全备份**: 自动备份原始文件
- 🎨 **友好界面**: 彩色命令行界面，进度条显示

## 安装说明

### 1. 克隆项目

```bash
git clone <repository-url>
cd link-change
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置微信公众号

复制环境变量模板：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的微信公众号信息：

```env
WECHAT_APPID=your_wechat_appid_here
WECHAT_SECRET=your_wechat_secret_here
```

## 使用方法

### 快速开始

运行完整的图片替换流程：

```bash
python main.py run document.md
```

或者指定输出目录：

```bash
python main.py run document.md --output output/
```

### 分步操作

#### 1. 提取图片URL

```bash
python main.py extract document.md
```

这会生成 `extracted_urls.txt` 文件，包含所有找到的图片URL。

#### 2. 下载图片

```bash
python main.py download extracted_urls.txt
```

图片会下载到 `downloads/` 目录，并生成 `download_mapping.json` 映射文件。

#### 3. 上传到微信公众号

```bash
python main.py upload downloads/ --appid YOUR_APPID --secret YOUR_SECRET
```

这会生成 `upload_mapping.json` 文件，包含本地路径到微信URL的映射。

#### 4. 替换文档中的URL

首先需要创建完整的URL映射文件，然后执行替换：

```bash
python main.py replace document.md url_mapping.json --output new_document.md
```

### 命令行选项

#### `run` 命令（完整流程）

```bash
python main.py run [OPTIONS] SOURCE_PATH
```

选项：
- `--output, -o`: 输出路径
- `--appid`: 微信公众号AppID
- `--secret`: 微信公众号AppSecret
- `--workers, -w`: 最大并发数（默认5）
- `--no-backup`: 不备份原文件
- `--temporary`: 上传为临时素材（默认永久素材）
- `--no-save-mapping`: 不保存URL映射文件

#### `extract` 命令（提取URL）

```bash
python main.py extract SOURCE_PATH
```

#### `download` 命令（下载图片）

```bash
python main.py download [OPTIONS] URLS_FILE
```

选项：
- `--workers, -w`: 最大并发数（默认5）

#### `upload` 命令（上传图片）

```bash
python main.py upload [OPTIONS] IMAGES_DIR
```

选项：
- `--appid`: 微信公众号AppID
- `--secret`: 微信公众号AppSecret
- `--temporary`: 上传为临时素材

#### `replace` 命令（替换URL）

```bash
python main.py replace [OPTIONS] SOURCE_PATH MAPPING_FILE
```

选项：
- `--output, -o`: 输出路径
- `--no-backup`: 不备份原文件

## 支持的文档格式

- **纯文本** (`.txt`): 提取HTTP/HTTPS图片链接
- **Markdown** (`.md`): 支持 `![](url)` 语法和HTML img标签
- **HTML** (`.html`, `.htm`): 支持 `<img>` 标签和CSS背景图片

## 支持的图片格式

- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- GIF (`.gif`)
- BMP (`.bmp`)
- WebP (`.webp`)

## 配置说明

### 环境变量

在 `.env` 文件中配置：

```env
# 微信公众号配置
WECHAT_APPID=your_appid
WECHAT_SECRET=your_secret
```

### 配置文件

在 `config.py` 中可以修改以下配置：

```python
# 文件路径配置
DOWNLOAD_DIR = 'downloads'  # 图片下载目录
LOG_DIR = 'logs'  # 日志目录

# 图片配置
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 最大图片大小 10MB
SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']

# 请求配置
REQUEST_TIMEOUT = 30  # 请求超时时间
MAX_RETRIES = 3  # 最大重试次数
```

## 使用示例

### 示例1：处理单个Markdown文件

```bash
# 完整流程
python main.py run article.md --output processed_article.md
```

### 示例2：处理整个目录

```bash
# 处理docs目录下的所有文档
python main.py run docs/ --output processed_docs/
```

### 示例3：使用自定义配置

```bash
# 使用临时素材，10个并发
python main.py run document.md \
  --appid wx1234567890 \
  --secret abcdef1234567890 \
  --workers 10 \
  --temporary
```

## 输出文件

工具运行后会生成以下文件：

- `extracted_urls.txt`: 提取的图片URL列表
- `download_mapping.json`: 原始URL到本地路径的映射
- `upload_mapping.json`: 本地路径到微信URL的映射
- `url_mapping.json`: 原始URL到微信URL的完整映射
- `replacement_report.txt`: 详细的替换报告
- `logs/app.log`: 详细的运行日志
- `*.backup`: 原始文件的备份

## 错误处理

工具具有完善的错误处理机制：

- **网络错误**: 自动重试下载和上传
- **文件错误**: 详细的错误信息和建议
- **格式错误**: 跳过不支持的文件格式
- **权限错误**: 清晰的权限问题提示

## 日志记录

所有操作都会记录到日志文件中：

- 日志文件位置: `logs/app.log`
- 日志级别: INFO（可在config.py中修改）
- 同时输出到控制台和文件

## 注意事项

1. **微信公众号限制**:
   - 图片大小不能超过10MB
   - 需要有效的AppID和AppSecret
   - 临时素材有效期3天，永久素材长期有效

2. **网络要求**:
   - 需要稳定的网络连接
   - 某些图片服务器可能有防盗链保护

3. **文件安全**:
   - 默认会创建备份文件
   - 建议在处理重要文档前手动备份

4. **性能考虑**:
   - 大量图片处理时建议适当调整并发数
   - 避免同时处理过多大文件

## 故障排除

### 常见问题

**Q: 提示"微信上传器初始化失败"**
A: 检查AppID和AppSecret是否正确，网络是否正常

**Q: 图片下载失败**
A: 可能是图片URL无效或网络问题，查看日志获取详细信息

**Q: 没有找到图片URL**
A: 检查文档格式是否支持，图片链接是否为HTTP/HTTPS格式

**Q: 替换后的文档格式异常**
A: 检查原始文档编码，建议使用UTF-8编码

### 获取帮助

```bash
# 查看帮助信息
python main.py --help

# 查看特定命令帮助
python main.py run --help
```

## 开发说明

### 项目结构

```
link-change/
├── main.py                 # 主程序入口
├── config.py              # 配置文件
├── utils.py               # 工具函数
├── exceptions.py          # 自定义异常
├── document_processor.py  # 文档处理模块
├── image_downloader.py    # 图片下载模块
├── wechat_uploader.py     # 微信上传模块
├── url_replacer.py        # URL替换模块
├── requirements.txt       # 依赖列表
├── .env.example          # 环境变量模板
└── README.md             # 说明文档
```

### 扩展开发

如需添加新的文档格式支持，在 `document_processor.py` 中添加对应的处理函数。

如需修改上传逻辑，可以扩展 `wechat_uploader.py` 模块。

## 许可证

本项目采用 MIT 许可证。

## 更新日志

### v1.0.0
- 初始版本发布
- 支持基本的图片地址替换功能
- 支持多种文档格式
- 完整的命令行界面