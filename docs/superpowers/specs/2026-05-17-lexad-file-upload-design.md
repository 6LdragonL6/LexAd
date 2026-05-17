# LexAd — 文件上传与格式识别设计文档

**日期**: 2026-05-17
**状态**: 已确认
**范围**: 文件上传、多格式文本提取（OCR / PDF / Office）、提交流程优化、预览编辑

## 一、概述

当前 LexAd 仅支持纯文本粘贴提交，无法处理广告物料中常见的图片、PDF、Word 等文件格式。项目已内置 OCR 依赖（pytesseract + Pillow + tessdata），但未接入流程。

本设计补充文件上传→提取→预览→合并→提交的完整链路，支持 8 种常见格式，文件仅临时处理不持久化，数据库始终只存储文本。

## 二、设计决策

| 维度 | 决策 |
|------|------|
| 提交方式 | 文本输入 + 文件上传，两者并重，可单独或混合使用 |
| 处理策略 | 混合模式：<10MB 同步提交，>=10MB 拒绝（MVP 阶段） |
| 文件存储 | 不持久化，提取文本后即丢弃临时文件 |
| 支持格式 | JPG / PNG / GIF / BMP / PDF / DOCX / DOC / PPTX / XLSX / TXT |
| 失败处理 | 自动降级：首选解析 → OCR 兜底 → 提示用户手动输入 |
| 预览编辑 | 提供：提交前可预览提取文本并手动修改 |

## 三、架构

```
前端 SubmitPage
  ├─ 文本输入（保留现有 textarea）
  └─ 文件上传区域（新增）
       ├─ 拖拽/点击上传
       ├─ 格式校验（前端预检扩展名 + 大小）
       ├─ >10MB 拒绝提示
       └─ 预览提取文本 → 用户可编辑确认
              │
              ▼
POST /api/v1/materials/preview-text  （仅提取文本，不保存）
POST /api/v1/materials/submit        （扩展：multipart, 可选 file 字段）
              │
              ▼
MaterialService.create_material()
  ├─ 1. 如有文件 → FileExtractionService.extract(file)
  │    ├─ 写临时文件到 /tmp/lexad/<uuid>/
  │    ├─ MIME 校验（magic bytes，不信任扩展名）
  │    ├─ dispatch 对应解析器（首选方案）
  │    ├─ 失败时降级 OCR
  │    └─ finally: 清理临时文件
  ├─ 2. 合并文本：extracted_text + raw_text
  └─ 3. 保存 Material（仅文本，不存文件路径/图片）
              │
              ▼
ReviewService.trigger_ai_review() → 四层引擎（现有流程不变）
```

### 新增模块

```
backend/app/services/
  file_extraction.py          ← FileExtractionService 主入口 + 降级编排
  parsers/
    image_parser.py           ← OCR (Tesseract + Pillow)
    pdf_parser.py             ← PDF 文本提取 (PyMuPDF) + OCR 降级
    office_parser.py          ← DOCX/DOC/PPTX/XLSX 文本提取
    text_parser.py            ← TXT 直读（含编码检测）
```

## 四、文件提取服务

### FileExtractionService（入口 + 降级编排）

```
extract(upload_file, mime) → ExtractionResult
  ├─ MIME 确认（magic bytes 校验）
  ├─ 写临时文件到 /tmp/lexad/<uuid>/
  ├─ try: dispatch(parser_by_mime, file)   # 首选方案
  │   except ExtractionError:
  │       fallback_to_ocr(file)             # OCR 兜底
  │   except:
  │       raise ExtractionError("无法提取文本，建议手动输入")
  └─ finally: 清理临时文件
```

### ExtractionResult

```python
@dataclass
class ExtractionResult:
    text: str
    source_format: str      # "pdf_text" | "pdf_ocr" | "image_ocr" | "docx_parse" | "pptx_parse" | "xlsx_parse" | "txt_raw"
    quality: str            # "good" | "degraded" | "minimal"
    fallback_used: bool
```

### 各格式解析器

| 格式 | 首选方案 | 降级方案 |
|------|---------|---------|
| JPG/PNG/GIF/BMP | OCR (Tesseract) | 无 |
| PDF（文本型） | PyMuPDF 提取嵌入文本 | OCR 逐页渲染 |
| PDF（扫描型） | 自动检测无嵌入文本→OCR | 标记 quality=degraded |
| DOCX | python-docx 提取段落 | OCR（渲染后） |
| DOC | python-docx 尝试读取 | OCR |
| PPTX | python-pptx 提取文本框 | OCR |
| XLSX | openpyxl 读取单元格，行列拼接 | OCR |
| TXT | 直接读取，UTF-8/GBK 编码检测 | 无 |

### 文本合并

```
final_text = (extracted_text.strip() + "\n" + form_raw_text.strip()).strip()
```

引擎只消费 `raw_text`，不感知文本来源。提取元信息（source_format, quality, fallback_used）记录在 `review.ai_result.extraction_meta` 中供追溯。

## 五、API 变更

### Schema: MaterialSubmit（扩展）

```python
class MaterialSubmit(BaseModel):
    name: str = Field(..., max_length=200)
    industry: str = Field(default="", max_length=50)
    platforms: list[str] = Field(default_factory=list)
    material_type: str = Field(default="文字")  # 扩展可选值
    raw_text: str = Field(default="")           # 改为可选，允许纯文件提交
    priority: str = Field(default="normal", pattern="^(normal|urgent|extreme)$")
    deadline: datetime | None = None
```

### 端点：POST /api/v1/materials/submit（改造）

- 请求格式：JSON → `multipart/form-data`
- 文件字段：`file`（可选 UploadFile）
- 新增 async，支持大文件不阻塞

```python
@router.post("/submit", response_model=MaterialOut, status_code=201)
async def submit_material(
    body: str = Form(...),
    file: UploadFile | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
```

### 新增端点：POST /api/v1/materials/preview-text

- 仅提取文本，不保存 Material
- 请求：`multipart/form-data`，字段 `file`
- 响应：`{ text, quality, source_format }`
- 复用 FileExtractionService

### material_type 扩展值

`文字 / 图片 / PDF文档 / Word文档 / PPT演示 / Excel表格 / 视频脚本 / 直播话术`

前端根据上传文件 MIME 自动预设，用户可手动修改。

## 六、前端变更（SubmitPage.vue）

### 表单布局

- 保留现有 textarea 文本输入
- 新增文件拖拽/点击上传区域，格式预检（扩展名 + 大小）
- 上限 10MB，超过提示"文件过大，请压缩后重试"
- 文件选择后显示文件名、体积、[预览提取文本] [移除] 按钮
- 预览区：显示提取文本，可编辑，提交时使用编辑后文本
- 格式自动识别后设置 material_type

### 提交流程

1. 用户填表 + 可选上传文件
2. （可选）点击"预览提取文本"→ 调用 preview-text，显示结果供编辑
3. 点击"提交并审查"→ FormData 打包所有字段 + 文件 → POST /submit
4. 成功后跳转 ResultPage，失败显示错误信息
5. 文本提取失败时，引导用户移除文件、手动粘贴文本后重新提交

### 交互要点

- 拖拽区域支持 drag-over 视觉反馈
- 提取质量低（quality=minimal）时黄色警告标识
- 已选文件可随时移除，不影响已填写的文本内容

## 七、错误处理

| 场景 | HTTP 状态 | 消息 |
|------|----------|------|
| 不支持的格式 | 400 | "不支持的文件格式，支持：JPG/PNG/PDF/DOCX/DOC/PPTX/XLSX/TXT" |
| 文件 >10MB | 413 | "文件过大（上限 10MB），请压缩后重试" |
| 文件损坏/空文件 | 400 | "无法读取文件内容，请检查文件完整性" |
| 提取完全空白 | 200 | quality=minimal, text=""，前端提示"未能提取文字，请手动输入" |
| 任意解析异常 | 500 | "文件解析失败，请尝试手动粘贴文本" |

## 八、新增依赖

```diff
# backend/requirements.txt
+ PyMuPDF>=1.23.0
+ python-docx>=1.1.0
+ python-pptx>=0.6.21
+ openpyxl>=3.1.0
```

`Pillow`, `pytesseract` 已有。`python-multipart` 已有（用于 FormData 解析）。

## 九、文件变更清单

| 文件 | 操作 |
|------|------|
| `backend/requirements.txt` | 新增 4 个依赖 |
| `backend/app/schemas/material.py` | MaterialSubmit: raw_text 改可选 |
| `backend/app/api/v1/endpoints/materials.py` | submit 改为 async multipart，新增 preview-text |
| `backend/app/services/material_service.py` | create_material 集成文件提取 |
| `backend/app/services/file_extraction.py` | **新建** |
| `backend/app/services/parsers/image_parser.py` | **新建** |
| `backend/app/services/parsers/pdf_parser.py` | **新建** |
| `backend/app/services/parsers/office_parser.py` | **新建** |
| `backend/app/services/parsers/text_parser.py` | **新建** |
| `backend/app/services/parsers/__init__.py` | **新建** |
| `backend/app/storage/__init__.py` | 临时文件辅助函数 |
| `frontend/src/pages/SubmitPage.vue` | 新增文件上传、预览、编辑区域 |
| `frontend/src/api/materials.ts` | FormData 提交适配，新增 previewText |

## 十、不变更范围

- 数据库模型（Material 已有 image_path 字段但不使用）
- 审查引擎流水线（只消费 raw_text）
- 用户认证与权限
- 部署配置
