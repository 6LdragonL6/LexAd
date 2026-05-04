# LexAd — 广告合规审查平台 Demo v0.1.0

广告合规审查平台第一版骨架。覆盖法律、行业、平台三层审查体系，支持文本与图片广告合规检测。

**注意：本版本为 Demo 骨架，所有审查结论均为占位/Mock 结果，不构成真实合规意见。**

## 技术栈

- **后端**: FastAPI (Python 3.10+)
- **模板**: Jinja2
- **局部刷新**: HTMX
- **样式**: 原生 CSS
- **架构**: 单 FastAPI 服务，不拆分前后端

## 目录结构

```
app/
  main.py              # 应用入口
  core/
    config.py           # 配置、常量、环境变量
  routers/
    pages.py            # 路由层（只做收发，不写业务逻辑）
  services/
    preprocess.py       # 预处理服务
    rule_assembly.py    # 规则组装服务
    review.py           # 三层审查服务
    case_match.py       # 案例匹配服务
    template_match.py   # 模板匹配服务
    penalty.py          # 罚金评估服务
    final_suggestion.py # 最终建议生成服务
    pipeline.py         # 全流程编排
  utils/
    json_reader.py      # JSON 安全读取
    id_gen.py           # ID / 时间戳生成
    file_handler.py     # 文件上传处理
    ocr.py              # OCR 工具（本地 Tesseract 预留）
  schemas/
    models.py           # Pydantic 模型定义
  templates/
    base.html           # 基础布局
    index.html          # 首页
    review.html         # 审查页
    cases.html          # 案例库页
    templates.html      # 模板库页
    result.html         # 结果展示页
    partials/           # HTMX 局部刷新片段
  static/
    css/style.css       # 样式
    js/                 # JS（预留）
    uploads/            # 上传文件目录
data/
  legal_rules.json      # 法律规则模板（空）
  industry_rules.json   # 行业规则模板（空）
  platform_rules.json   # 平台规则模板（空）
  case_library.json     # 案例库模板（空）
  rewrite_templates.json# 改写模板库模板（空）
requirements.txt
render.yaml
README.md
```

## 本地启动

```bash
# 1. 进入项目目录
cd LexAd

# 2. 创建虚拟环境（建议）
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 5. 打开浏览器访问
# http://localhost:8000
```

## 页面路由

| 路由 | 说明 |
|------|------|
| `GET /` | 首页 |
| `GET /review` | 审查页面 |
| `POST /review/submit` | 提交审查（支持 HTMX 局部刷新） |
| `GET /cases` | 案例库展示页 |
| `GET /templates` | 模板库展示页 |
| `GET /result/{request_id}` | 审查结果详情页 |
| `POST /preprocess/image` | 图片预处理接口（JSON） |
| `GET /partial/review-result` | HTMX 审查结果片段 |
| `GET /partial/cases` | HTMX 案例库片段 |
| `GET /partial/templates` | HTMX 模板库片段 |
| `GET /partial/final-result` | HTMX 最终结果片段 |
| `GET /api/result/{request_id}` | JSON API 接口 |

## Tesseract 安装（OCR 功能）

项目预留了本地 Tesseract OCR 方案。安装 Tesseract 后启用真实 OCR：

### Windows
从 [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) 下载安装包，安装时勾选中文语言包。

### macOS
```bash
brew install tesseract
```

### Linux (Ubuntu/Debian)
```bash
sudo apt install tesseract-ocr tesseract-ocr-chi-sim
```

安装完成后：
1. 取消 `requirements.txt` 中 `pytesseract` 和 `Pillow` 的注释并安装
2. 在 `app/core/config.py` 中将 `TESSERACT_AVAILABLE` 设为 `True`
3. 取消 `app/utils/ocr.py` 中真实 Tesseract 调用代码的注释

**如果 Tesseract 未安装，OCR 会自动 fallback 到 mock 模式，不影响项目启动。**

## Render 部署

1. 将项目推送到 GitHub
2. 在 [Render](https://render.com) 创建新的 Web Service
3. 连接 GitHub 仓库
4. Render 会自动读取 `render.yaml` 配置
5. 或手动配置：
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_ENV` | 运行环境 | `development` |
| `DEEPSEEK_API_KEY` | DeepSeek API Key（预留） | 空 |
| `DEEPSEEK_BASE_URL` | DeepSeek 接口地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | DeepSeek 模型名 | `deepseek-chat` |

第一版不要求真实调用这些变量，配置层已预留读取逻辑，不存在时使用安全默认值。

## 常见问题

### Q: 图片上传后没有 OCR 结果？
A: Tesseract 未安装。安装 Tesseract 并启用配置后可获得真实 OCR。当前版本返回占位 OCR 文本。

### Q: 审查结果都是 Mock？
A: 第一版为 Demo 骨架，所有审查规则均为占位。后续在 `app/services/` 和 `data/` 中接入真实规则即可。

### Q: 案例库/模板库显示"暂无数据"？
A: `data/case_library.json` 和 `data/rewrite_templates.json` 目前内容为空。向这些文件中添加数据即可。

### Q: 页面样式有问题？
A: 本项目使用原生 CSS，无需编译。确认 `app/static/css/style.css` 文件存在。
