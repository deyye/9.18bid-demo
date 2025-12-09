"""
Markdown到Word文档的专业解析器
用于将AI生成的Markdown内容转换为符合标书规范的Word格式
"""
import re
from typing import List, Dict, Tuple, Optional
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.table import _Cell


class MarkdownToWordParser:
    """Markdown转Word解析器（专业标书排版）"""
    
    # 标书标准配置
    FONT_NAME_CN = '宋体'          # 中文字体
    FONT_NAME_EN = 'Times New Roman'  # 英文字体
    
    FONT_SIZE_H1 = 22              # 一级标题（22pt = 三号）
    FONT_SIZE_H2 = 18              # 二级标题（18pt = 小三）
    FONT_SIZE_H3 = 16              # 三级标题（16pt = 四号）
    FONT_SIZE_H4 = 14              # 四级标题（14pt = 小四）
    FONT_SIZE_BODY = 12            # 正文（12pt = 小四）
    
    LINE_SPACING = 1.5             # 行间距（1.5倍）
    FIRST_LINE_INDENT = 24         # 首行缩进（2字符 = 24pt）
    
    COLOR_H1 = RGBColor(0, 0, 0)   # 一级标题颜色（黑色）
    COLOR_H2 = RGBColor(0, 0, 0)   # 二级标题颜色
    COLOR_BODY = RGBColor(0, 0, 0) # 正文颜色
    
    def __init__(self, doc: Document):
        """
        初始化解析器
        
        Args:
            doc: python-docx的Document对象
        """
        self.doc = doc
        self._init_styles()
    
    def _init_styles(self):
        """初始化自定义样式（标书专用）"""
        styles = self.doc.styles
        
        # 1. 正文样式
        try:
            body_style = styles['BodyText']
        except KeyError:
            body_style = styles.add_style('BodyText', WD_STYLE_TYPE.PARAGRAPH)
        
        body_style.font.name = self.FONT_NAME_EN
        body_style.font.size = Pt(self.FONT_SIZE_BODY)
        body_style.font.color.rgb = self.COLOR_BODY
        body_style.element.rPr.rFonts.set(qn('w:eastAsia'), self.FONT_NAME_CN)
        
        # 段落格式
        body_style.paragraph_format.line_spacing = self.LINE_SPACING
        body_style.paragraph_format.space_before = Pt(0)
        body_style.paragraph_format.space_after = Pt(6)
        body_style.paragraph_format.first_line_indent = Pt(self.FIRST_LINE_INDENT)
        body_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY  # 两端对齐
        
        # 2. 列表样式（无首行缩进）
        try:
            list_style = styles['ListParagraph']
        except KeyError:
            list_style = styles.add_style('ListParagraph', WD_STYLE_TYPE.PARAGRAPH)
        
        list_style.font.name = self.FONT_NAME_EN
        list_style.font.size = Pt(self.FONT_SIZE_BODY)
        list_style.element.rPr.rFonts.set(qn('w:eastAsia'), self.FONT_NAME_CN)
        list_style.paragraph_format.line_spacing = self.LINE_SPACING
        list_style.paragraph_format.first_line_indent = Pt(0)  # 列表无首行缩进
        list_style.paragraph_format.left_indent = Pt(21)       # 左缩进
    
    def parse(self, markdown_text: str):
        """
        解析Markdown文本并添加到Word文档
        
        Args:
            markdown_text: Markdown格式的文本
        """
        if not markdown_text or not markdown_text.strip():
            return
        
        # 预处理：标准化换行符
        markdown_text = markdown_text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 按行处理
        lines = markdown_text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 1. 处理标题
            if line.startswith('#'):
                self._parse_heading(line)
                i += 1
                continue
            
            # 2. 处理表格
            if self._is_table_line(line):
                table_lines, i = self._extract_table(lines, i)
                self._parse_table(table_lines)
                continue
            
            # 3. 处理代码块
            if line.strip().startswith('```'):
                code_lines, i = self._extract_code_block(lines, i)
                self._parse_code_block(code_lines)
                continue
            
            # 4. 处理引用块
            if line.strip().startswith('>'):
                quote_lines, i = self._extract_quote_block(lines, i)
                self._parse_quote_block(quote_lines)
                continue
            
            # 5. 处理有序列表
            if re.match(r'^\s*\d+\.\s+', line):
                list_lines, i = self._extract_list(lines, i, ordered=True)
                self._parse_list(list_lines, ordered=True)
                continue
            
            # 6. 处理无序列表
            if re.match(r'^\s*[-*+]\s+', line):
                list_lines, i = self._extract_list(lines, i, ordered=False)
                self._parse_list(list_lines, ordered=False)
                continue
            
            # 7. 处理分割线
            if re.match(r'^[\s]*[-*_]{3,}[\s]*$', line):
                self._parse_horizontal_rule()
                i += 1
                continue
            
            # 8. 处理普通段落
            if line.strip():
                para_lines, i = self._extract_paragraph(lines, i)
                self._parse_paragraph(para_lines)
            else:
                i += 1
    
    # ====================================================================
    # 标题解析
    # ====================================================================
    
    def _parse_heading(self, line: str):
        """解析标题行"""
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if not match:
            return
        
        level = len(match.group(1))
        text = match.group(2).strip()
        
        # 清理可能的尾部#号
        text = re.sub(r'\s*#+\s*$', '', text)
        
        # 根据层级设置样式
        if level == 1:
            p = self.doc.add_heading(level=1)
            run = p.add_run(text)
            self._set_font(run, self.FONT_NAME_CN, self.FONT_SIZE_H1, bold=True)
            p.paragraph_format.space_before = Pt(24)
            p.paragraph_format.space_after = Pt(12)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER  # 一级标题居中
            
        elif level == 2:
            p = self.doc.add_heading(level=2)
            run = p.add_run(text)
            self._set_font(run, self.FONT_NAME_CN, self.FONT_SIZE_H2, bold=True)
            p.paragraph_format.space_before = Pt(18)
            p.paragraph_format.space_after = Pt(10)
            
        elif level == 3:
            p = self.doc.add_heading(level=3)
            run = p.add_run(text)
            self._set_font(run, self.FONT_NAME_CN, self.FONT_SIZE_H3, bold=True)
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(8)
            
        else:  # level 4+
            p = self.doc.add_heading(level=min(level, 9))
            run = p.add_run(text)
            self._set_font(run, self.FONT_NAME_CN, self.FONT_SIZE_H4, bold=True)
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(6)
    
    # ====================================================================
    # 段落解析
    # ====================================================================
    
    def _extract_paragraph(self, lines: List[str], start: int) -> Tuple[List[str], int]:
        """提取连续的段落行"""
        para_lines = []
        i = start
        
        while i < len(lines):
            line = lines[i]
            
            # 遇到空行、标题、列表等，停止
            if (not line.strip() or 
                line.startswith('#') or
                self._is_table_line(line) or
                re.match(r'^\s*[-*+]\s+', line) or
                re.match(r'^\s*\d+\.\s+', line) or
                line.strip().startswith('```') or
                line.strip().startswith('>')):
                break
            
            para_lines.append(line)
            i += 1
        
        return para_lines, i
    
    def _parse_paragraph(self, lines: List[str]):
        """解析段落（支持行内样式）"""
        text = ' '.join(line.strip() for line in lines)
        
        if not text:
            return
        
        p = self.doc.add_paragraph(style='BodyText')
        
        # 解析行内样式：**粗体**、*斜体*、`代码`、[链接](url)
        self._parse_inline_styles(p, text)
    
    def _parse_inline_styles(self, paragraph, text: str):
        """
        解析并应用行内样式
        支持：**粗体**、*斜体*、`代码`、[链接](url)
        """
        # 正则匹配模式
        pattern = r'(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[([^\]]+)\]\(([^)]+)\))'
        
        last_end = 0
        
        for match in re.finditer(pattern, text):
            # 添加前面的普通文本
            if match.start() > last_end:
                run = paragraph.add_run(text[last_end:match.start()])
                self._set_font(run, self.FONT_NAME_CN, self.FONT_SIZE_BODY)
            
            matched_text = match.group(0)
            
            # 粗体
            if matched_text.startswith('**') and matched_text.endswith('**'):
                content = matched_text[2:-2]
                run = paragraph.add_run(content)
                self._set_font(run, self.FONT_NAME_CN, self.FONT_SIZE_BODY, bold=True)
            
            # 斜体
            elif matched_text.startswith('*') and matched_text.endswith('*'):
                content = matched_text[1:-1]
                run = paragraph.add_run(content)
                run.italic = True
                self._set_font(run, self.FONT_NAME_CN, self.FONT_SIZE_BODY)
            
            # 行内代码
            elif matched_text.startswith('`') and matched_text.endswith('`'):
                content = matched_text[1:-1]
                run = paragraph.add_run(content)
                run.font.name = 'Consolas'
                run.font.size = Pt(10)
                run.font.color.rgb = RGBColor(199, 37, 78)  # 代码红色
            
            # 链接
            elif match.group(2) and match.group(3):
                link_text = match.group(2)
                # url = match.group(3)  # 可用于添加超链接
                run = paragraph.add_run(link_text)
                run.font.color.rgb = RGBColor(0, 0, 255)  # 蓝色
                run.font.underline = True
                self._set_font(run, self.FONT_NAME_CN, self.FONT_SIZE_BODY)
            
            last_end = match.end()
        
        # 添加剩余的普通文本
        if last_end < len(text):
            run = paragraph.add_run(text[last_end:])
            self._set_font(run, self.FONT_NAME_CN, self.FONT_SIZE_BODY)
    
    # ====================================================================
    # 列表解析
    # ====================================================================
    
    def _extract_list(self, lines: List[str], start: int, ordered: bool) -> Tuple[List[str], int]:
        """提取列表项"""
        list_lines = []
        i = start
        
        pattern = r'^\s*\d+\.\s+' if ordered else r'^\s*[-*+]\s+'
        
        while i < len(lines):
            line = lines[i]
            
            if not re.match(pattern, line) and line.strip():
                break
            
            if re.match(pattern, line):
                list_lines.append(line)
            
            i += 1
        
        return list_lines, i
    
    def _parse_list(self, lines: List[str], ordered: bool):
        """解析列表"""
        pattern = r'^\s*(\d+\.|-|\*|\+)\s+(.+)$'
        
        for idx, line in enumerate(lines):
            match = re.match(pattern, line)
            if not match:
                continue
            
            content = match.group(2).strip()
            
            # 创建列表段落
            p = self.doc.add_paragraph(style='ListParagraph')
            
            if ordered:
                prefix = f"{idx + 1}. "
            else:
                prefix = "• "  # 使用圆点符号
            
            # 添加序号/符号
            run_prefix = p.add_run(prefix)
            self._set_font(run_prefix, self.FONT_NAME_CN, self.FONT_SIZE_BODY, bold=True)
            
            # 添加内容
            self._parse_inline_styles(p, content)
    
    # ====================================================================
    # 表格解析
    # ====================================================================
    
    def _is_table_line(self, line: str) -> bool:
        """判断是否为表格行"""
        return bool(re.match(r'^\s*\|.*\|\s*$', line))
    
    def _extract_table(self, lines: List[str], start: int) -> Tuple[List[str], int]:
        """提取表格行"""
        table_lines = []
        i = start
        
        while i < len(lines) and self._is_table_line(lines[i]):
            table_lines.append(lines[i])
            i += 1
        
        return table_lines, i
    
    def _parse_table(self, lines: List[str]):
        """
        解析Markdown表格并转换为Word表格
        
        示例：
        | 列1 | 列2 | 列3 |
        |-----|-----|-----|
        | 数据1 | 数据2 | 数据3 |
        """
        if len(lines) < 2:
            return
        
        # 解析表头
        header_cells = self._parse_table_row(lines[0])
        num_cols = len(header_cells)
        
        # 跳过分隔行（第二行）
        data_lines = lines[2:] if len(lines) > 2 else []
        
        # 解析数据行
        data_rows = []
        for line in data_lines:
            cells = self._parse_table_row(line)
            # 确保列数一致
            while len(cells) < num_cols:
                cells.append('')
            data_rows.append(cells[:num_cols])
        
        # 创建Word表格
        num_rows = 1 + len(data_rows)  # 表头 + 数据行
        table = self.doc.add_table(rows=num_rows, cols=num_cols)
        table.style = 'Light Grid Accent 1'  # 使用内置表格样式
        
        # 设置表头
        header_row = table.rows[0]
        for idx, cell_text in enumerate(header_cells):
            cell = header_row.cells[idx]
            self._set_table_cell(cell, cell_text, is_header=True)
        
        # 设置数据行
        for row_idx, row_data in enumerate(data_rows):
            row = table.rows[row_idx + 1]
            for col_idx, cell_text in enumerate(row_data):
                cell = row.cells[col_idx]
                self._set_table_cell(cell, cell_text, is_header=False)
    
    def _parse_table_row(self, line: str) -> List[str]:
        """解析表格行，返回单元格列表"""
        # 去除首尾的|符号
        line = line.strip().strip('|')
        
        # 按|分割
        cells = [cell.strip() for cell in line.split('|')]
        
        return cells
    
    def _set_table_cell(self, cell: _Cell, text: str, is_header: bool = False):
        """设置表格单元格样式"""
        cell.text = text
        
        # 设置段落居中
        paragraph = cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # 设置字体
        for run in paragraph.runs:
            run.font.name = self.FONT_NAME_EN
            run.font.size = Pt(self.FONT_SIZE_BODY if not is_header else self.FONT_SIZE_BODY)
            run.font.bold = is_header
            run.element.rPr.rFonts.set(qn('w:eastAsia'), self.FONT_NAME_CN)
        
        # 表头背景色（浅灰色）
        if is_header:
            shading_elm = OxmlElement('w:shd')
            shading_elm.set(qn('w:fill'), 'D9D9D9')
            cell._element.get_or_add_tcPr().append(shading_elm)
    
    # ====================================================================
    # 代码块解析
    # ====================================================================
    
    def _extract_code_block(self, lines: List[str], start: int) -> Tuple[List[str], int]:
        """提取代码块"""
        code_lines = []
        i = start + 1  # 跳过开始的```
        
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith('```'):
                i += 1
                break
            code_lines.append(line)
            i += 1
        
        return code_lines, i
    
    def _parse_code_block(self, lines: List[str]):
        """解析代码块"""
        code_text = '\n'.join(lines)
        
        p = self.doc.add_paragraph()
        p.paragraph_format.left_indent = Pt(21)
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(6)
        
        # 添加浅灰色背景
        pPr = p._element.get_or_add_pPr()
        shading = OxmlElement('w:shd')
        shading.set(qn('w:fill'), 'F5F5F5')
        pPr.append(shading)
        
        run = p.add_run(code_text)
        run.font.name = 'Consolas'
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(51, 51, 51)
    
    # ====================================================================
    # 引用块解析
    # ====================================================================
    
    def _extract_quote_block(self, lines: List[str], start: int) -> Tuple[List[str], int]:
        """提取引用块"""
        quote_lines = []
        i = start
        
        while i < len(lines) and lines[i].strip().startswith('>'):
            # 去除>符号
            content = re.sub(r'^\s*>\s?', '', lines[i])
            quote_lines.append(content)
            i += 1
        
        return quote_lines, i
    
    def _parse_quote_block(self, lines: List[str]):
        """解析引用块"""
        quote_text = '\n'.join(lines)
        
        p = self.doc.add_paragraph()
        p.paragraph_format.left_indent = Pt(42)  # 左缩进
        p.paragraph_format.right_indent = Pt(21) # 右缩进
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(6)
        
        # 添加竖线边框
        pPr = p._element.get_or_add_pPr()
        pBdr = OxmlElement('w:pBdr')
        left_border = OxmlElement('w:left')
        left_border.set(qn('w:val'), 'single')
        left_border.set(qn('w:sz'), '12')
        left_border.set(qn('w:color'), '1890FF')  # 蓝色竖线
        pBdr.append(left_border)
        pPr.append(pBdr)
        
        run = p.add_run(quote_text)
        run.font.italic = True
        self._set_font(run, self.FONT_NAME_CN, self.FONT_SIZE_BODY)
    
    # ====================================================================
    # 分割线解析
    # ====================================================================
    
    def _parse_horizontal_rule(self):
        """解析分割线"""
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(12)
        
        # 添加底部边框作为分割线
        pPr = p._element.get_or_add_pPr()
        pBdr = OxmlElement('w:pBdr')
        bottom_border = OxmlElement('w:bottom')
        bottom_border.set(qn('w:val'), 'single')
        bottom_border.set(qn('w:sz'), '6')
        bottom_border.set(qn('w:color'), 'CCCCCC')
        pBdr.append(bottom_border)
        pPr.append(pBdr)
    
    # ====================================================================
    # 工具方法
    # ====================================================================
    
    def _set_font(self, run, font_name: str, size: int, bold: bool = False):
        """设置字体样式"""
        run.font.name = self.FONT_NAME_EN
        run.font.size = Pt(size)
        run.font.bold = bold
        run.element.rPr.rFonts.set(qn('w:eastAsia'), font_name)


# ====================================================================
# 使用示例和测试
# ====================================================================

def example_usage():
    """示例：如何使用Markdown解析器"""
    from docx import Document
    
    # 创建Word文档
    doc = Document()
    
    # 设置页面（A4纸张）
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(3.17)
    section.right_margin = Cm(3.17)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    
    # 创建解析器
    parser = MarkdownToWordParser(doc)
    
    # 示例Markdown内容
    markdown_content = """
# 项目技术方案

## 1. 技术架构设计

### 1.1 总体架构

本项目采用**微服务架构**，具备高可用、高并发、易扩展的特点。系统遵循*前后端分离*原则，前端采用`React 18`框架，后端基于`FastAPI`构建。

核心技术栈包括：
- Python 3.8+（后端开发语言）
- React 18（前端框架）
- MySQL 8.0（关系型数据库）
- Redis 6.0（缓存中间件）

### 1.2 性能指标

| 指标名称 | 目标值 | 验证方式 |
|---------|--------|---------|
| 并发用户数 | ≥1000 | 压力测试 |
| 响应时间 | ≤2秒 | 接口监控 |
| 可用性 | 99.9% | 日志统计 |

## 2. 安全保障措施

> **重要提示**：所有敏感数据传输必须启用HTTPS加密，数据库访问需通过VPN专线。

### 2.1 访问控制

系统实现**基于角色的访问控制（RBAC）**，权限矩阵如下：

```python
# 权限配置示例
ROLE_PERMISSIONS = {
    'admin': ['read', 'write', 'delete'],
    'user': ['read', 'write'],
    'guest': ['read']
}
```

### 2.2 数据加密

1. 传输层加密：采用TLS 1.3协议
2. 存储层加密：敏感字段使用AES-256加密
3. 密钥管理：接入[阿里云KMS](https://www.aliyun.com/product/kms)服务

---

## 3. 项目实施计划

项目周期共**12周**，分为以下阶段：

1. 需求调研与设计（2周）
2. 开发与测试（6周）
3. 部署上线（2周）
4. 试运行与优化（2周）

"""
    
    # 解析Markdown并添加到文档
    parser.parse(markdown_content)
    
    # 保存文档
    doc.save('/home/claude/output.docx')
    print("✅ Word文档生成成功：/home/claude/output.docx")


if __name__ == "__main__":
    example_usage()