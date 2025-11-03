import requests
import json
import sseclient
import time
import os
from tqdm import tqdm
from datetime import datetime

# ======================================================
# 配置
# ======================================================

BASE_URL = "http://127.0.0.1:8000/api/content/generate-hierarchical"
USE_QWEN = True      
STREAM_MODE = True   
SAVE_DIR = "generated_content"  # 保存目录

# 确保保存目录存在
os.makedirs(SAVE_DIR, exist_ok=True)

# 测试输入：示例项目与大纲
payload = {
    "outline": {
         "details":[
            {
                "id": "1",
                "title": "项目理解与需求分析",
                "description": "阐述对钱塘区小额公共资源电子监管系统提升改造项目的背景、政策依据及需求解读。供应商提供对本项目的背景和需求的理解与分析报告，要求内容分析完整，有针对性。完全符合上述要求及采购需求的得5分，部分满足的得3分，满足度较差的得1分，完全不满足或未提及相关内容的不得分。字数5000字。",
                "children": [
                    {
                        "id": "1.1",
                        "title": "项目背景与政策依据",
                        "description": "分析《杭州市限额以下公共资源交易指引》等政策文件对系统建设的指导意义"
                    },
                    {
                        "id": "1.2",
                        "title": "系统建设必要性说明",
                        "description": "论证系统国产化改造与新增标后管理模块对监管效率和数据安全的提升价值"
                    }
                ]
            },
            {
                "id": "2",
                "title": "技术方案设计",
                "description": "提供系统总体架构、功能模块及关键技术实现的完整技术方案。响应方案总体设计、平台建设方案等，①体系架构、②功能模块、③实现思路和关键技术、④对功能设计和实施计划的建议、⑤可行性、⑥扩展性；要求内容全面、科学、合理。以上六项每小项完全符合上述要求及采购需求的得3分，部分满足的得2分，满足度较差的得1分，完全不满足或未提及相关内容的不得分。字数25000字。",
                "children": [
                    {
                        "id": "2.1",
                        "title": "系统架构设计",
                        "description": "展示国产化适配后的系统分层架构及各模块技术实现路径"
                    },
                    {
                        "id": "2.2",
                        "title": "功能模块实现",
                        "description": "细化线上审批、实时监管、标后管理等核心模块的技术实现方案",
                        "children": [
                            {
                                "id": "2.2.1",
                                "title": "线上审批业务系统",
                                "description": "说明审批流程自定义机制与15分钟响应时间保障方案"
                            },
                            {
                                "id": "2.2.2",
                                "title": "标后管理模块",
                                "description": "阐述竣工财务结算、审计等子模块的数据交互与业务逻辑设计"
                            }
                        ]
                    },
                    {
                        "id": "2.3",
                        "title": "关键技术指标",
                        "description": "明确国密算法加密、100用户/秒并发处理等核心性能参数实现方案"
                    },
                    {
                        "id": "2.4",
                        "title": "系统扩展性设计",
                        "description": "说明未来对接全省国资国企招采数据接口的架构预留与技术适配方案"
                    }
                ]
            },
            {
                "id": "3",
                "title": "实施与运维方案",
                "description": "制定系统改造实施计划及全周期运维保障体系。系统的实施方案设计合理，充分考虑用户实际使用需求，满足本项目的业务要求。完全符合上述要求及采购需求的得5分，部分符合的得3分，满足度较差的得1分，完全不满足或未提及相关内容的不得分。字数25000字。",
                "children": [
                    {
                        "id": "3.1",
                        "title": "项目实施进度计划",
                        "description": "按2025-11-30至2026-01-31关键节点制定分阶段实施计划"
                    },
                    {
                        "id": "3.2",
                        "title": "国产化适配实施方案",
                        "description": "包含数据库替换、浏览器兼容性测试等具体实施步骤与验证标准"
                    },
                    {
                        "id": "3.3",
                        "title": "运维服务保障体系",
                        "description": "构建5*12小时响应机制及三年免费维保服务的具体执行方案",
                        "children": [
                            {
                                "id": "3.3.1",
                                "title": "故障处理流程",
                                "description": "明确15分钟内解决一般性故障的响应机制与升级处理流程"
                            }
                        ]
                    }
                ]
            },
            {
                "id": "4",
                "title": "质量与安全保障体系",
                "description": "建立覆盖等保二级、数据加密及系统测评的全流程质量管控方案。供应商提供的质量保证方案设计合理，充分考虑采购人实际使用需求，满足本项目对当前和未来发展的要求。完全符合上述要求及采购需求的得4分，部分符合的得2分，满足度较差的得1分，完全不满足或未提及相关内容的不得分。字数25000字。",
                "children": [
                    {
                        "id": "4.1",
                        "title": "质量保证措施",
                        "description": "制定符合《杭州市政府采购履约验收办法》的阶段性质量验收标准"
                    },
                    {
                        "id": "4.2",
                        "title": "系统安全设计",
                        "description": "从安全策略、风险分析、防护措施三方面构建等保二级合规体系",
                        "children": [
                            {
                                "id": "4.2.1",
                                "title": "安全策略规划",
                                "description": "设计符合监管需求的权限控制、数据脱敏等安全策略"
                            },
                            {
                                "id": "4.2.2",
                                "title": "安全风险分析",
                                "description": "识别系统改造过程中的数据迁移、国密算法兼容性等风险点"
                            },
                            {
                                "id": "4.2.3",
                                "title": "安全防护措施",
                                "description": "说明防火墙配置、入侵检测等具体安全防护技术实现方案"
                            }
                        ]
                    }
                ]
            },
            {
                "id": "5",
                "title": "系统测试验证方案",
                "description": "制定系统全维度测试验证方案，包括功能测试、压力测试、兼容性测试等内容，确保系统在各类场景下稳定可靠。供应商提供的测试方案设计合理，充分考虑采购人实际使用需求，满足本项目的业务要求。完全符合上述要求及采购需求的得4分，部分符合的得2分，满足度较差的得1分，完全不满足或未提及相关内容的不得分。字数25000字。",
                "children": [
                    {
                        "id": "5.1",
                        "title": "系统测试计划",
                        "description": "包含功能测试、性能测试、兼容性测试、安全性测试等全流程测试内容，明确测试目标、方法、步骤与验收标准。"
                    },
                    {
                        "id": "5.2",
                        "title": "压力测试指标",
                        "description": "验证系统在100用户/秒并发下的稳定性与性能表现，确保系统具备高并发、高负载下的可靠运行能力。"
                    }
                ]
            },
            {
                "id": "6",
                "title": "系统应急处理方案",
                "description": "设计数据回滚、双机热备等应急机制及故障预警响应流程，确保系统在异常情况下的业务连续性与数据安全。供应商提供的应急方案设计合理，充分考虑采购人实际使用需求，满足本项目对当前和未来发展的要求。完全符合上述要求及采购需求的得4分，部分符合的得2分，满足度较差的得1分，完全不满足或未提及相关内容的不得分。字数25000字。",
                "children": [
                    {
                        "id": "6.1",
                        "title": "应急响应机制",
                        "description": "建立系统异常监测与自动告警机制，明确故障分级处理流程及责任分工。"
                    },
                    {
                        "id": "6.2",
                        "title": "数据与系统恢复策略",
                        "description": "制定数据回滚、双机热备、定期备份及灾备切换方案，确保在极端情况下系统快速恢复。"
                    },
                    {
                        "id": "6.3",
                        "title": "应急演练计划",
                        "description": "制定月度应急演练方案及历史故障案例复盘机制，持续优化应急响应能力。"
                    }
                ]
            },
            {
                "id": "7",
                "title": "培训方案",
                "description": "制定系统使用、运维及管理等多层次培训计划，确保采购人相关人员能够熟练掌握系统的操作与维护。培训方案：针对本项目制定培训方案，方案应包括培训安排、培训日程和教学方式；要求方案完整、科学、合理。完全符合上述要求及采购需求的得4分，部分满足得2分，满足度较差的得1分，完全不满足或未提及相关内容的不得分。字数10000字。",
                "children": [
                    {
                        "id": "7.1",
                        "title": "培训总体规划",
                        "description": "制定培训总体目标、培训周期及对象分层计划，覆盖系统管理员、运维人员及普通用户等角色。"
                    },
                    {
                        "id": "7.2",
                        "title": "培训内容与形式",
                        "description": "培训内容包括系统功能操作、常见问题处理、系统维护与安全管理。培训形式包含集中授课、线上课程、现场实操及问答环节。"
                    },
                    {
                        "id": "7.3",
                        "title": "培训资料与考核机制",
                        "description": "提供完整的培训教材、操作手册及视频教程，建立考核与反馈机制，确保培训效果可量化、可追踪。"
                    },
                    {
                        "id": "7.4",
                        "title": "培训实施与持续支持",
                        "description": "结合系统上线进度同步推进培训，提供后续跟踪辅导与技术支持，确保人员熟练掌握系统使用。"
                    }
                ]
            }
        ]
    },
    "project_overview": """
## 项目概述

**项目名称（含编号）**：钱塘区小额公共资源电子监管系统提升改造项目（项目编号：330114254160010000022）
**招标单位**：杭州市钱塘区行政审批局
**项目地址**：浙江省杭州市钱塘区义蓬街道江东大道3899号
**实施地点**：杭州市钱塘区下沙街道金沙大道600号东楼6楼3号开标室
**行业领域**：软件和信息技术服务业

---

### 一、项目背景

为落实《杭州市限额以下（小额）公共资源交易指引（试行）》及相关数据规范文件要求，钱塘区拟对现有小额公共资源电子监管系统进行提升改造。项目旨在优化营商环境，提升资源配置与监管效率，实现限额以下交易活动的数字化、规范化管理。
改造完成后，系统将实现数据自动归集与智能监管，预计可减少30%以上人工干预成本，显著提高业务处理效率和监管透明度。

---

### 二、建设规模与主要内容

项目计划对现有监管平台进行国产化适配改造，主要包括：

* 数据库替换与系统兼容性适配；
* 新增标后管理模块（竣工财务结算、竣工验收、项目审计）；
* 前端浏览器及终端适配；
* 系统性能与安全能力提升；
* 数据采集与监管接口优化。

**投资总额**：人民币 750,000 元（含税）。
**预算结构**：未明确硬件、软件、实施与运维分项，需供应商结合实际需求进行报价。

---

### 三、时间与交付节点

* **项目启动**：2025年11月7日
* **关键里程碑**：

  * 2025年11月30日：完成国产化改造主要内容；
  * 2026年1月31日：完成系统上线运行；
  * 2026年2月28日：完成试运行并通过验收。
* **交付要求**：2026年1月31日前完成上线；逾期须承担违约责任（每日万分之三，最高不超过合同价的20%）。

---

### 四、系统功能与架构

系统总体架构包括以下核心模块：

1. 线上审批业务系统

   * 支持自定义审批流
   * 响应时间≤15分钟
   * 数据存储容量≥1000条/日
2. 在线实时监管系统

   * 覆盖招标及标后监管
   * 数据更新频率≤1分钟
3. 供应商与专家库管理及抽取系统

   * 专家库动态更新
   * 抽取响应时间≤5分钟
4. 交易预警系统

   * 依据区级预警规则自动触发
   * 响应时间≤10分钟
5. 数据统计与分析系统

   * 支持信息查询与CSV/PDF导出
   * 导出速度≥100条/秒
6. 信用评价与反馈系统

---

### 五、技术要求

* **安全标准**：等保二级
* **加密算法**：国密算法（SM2/SM4）
* **并发处理能力**：≥100用户/秒
* **系统响应时间**：≤15分钟
* **符合标准**：《政府采购竞争性磋商采购方式管理暂行办法》（财库〔2014〕214号）、《浙江省政府采购项目电子交易管理暂行办法》等。

---

### 六、质量与运维要求

* **质量验收**：依据《杭州市政府采购履约验收暂行办法》及钱塘区信息化项目相关标准；
* **运维服务**：

  * 服务时间：每周5天，每天12小时；
  * 故障响应：15分钟内处理，一般性故障30分钟未解决需上报；
  * 免费维保期：3年；
* **安全合规**：通过国产化测评及密码测评。
"""
}

headers = {
    "Content-Type": "application/json"
}

# ======================================================
# 测试函数
# ======================================================

def test_non_stream():
    """测试非流式生成"""
    print("🚀 正在测试非流式生成接口...")
    start_time = time.time()
    
    resp = requests.post(
        BASE_URL,
        headers=headers,
        params={"use_qwen": USE_QWEN, "stream": False},
        data=json.dumps(payload)
    )
    
    total_time = time.time() - start_time
    print(f"⏱ 接口请求总耗时: {total_time:.2f} 秒")

    if resp.status_code != 200:
        print(f"❌ 请求失败: {resp.status_code} - {resp.text}")
        return

    data = resp.json()
    content = data.get("content", "")
    
    # 保存完整内容
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_path = os.path.join(SAVE_DIR, f"full_content_{timestamp}.txt")
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ 生成完成：")
    print("="*80)
    print(content) 
    print("="*80)
    print(f"💾 完整内容已保存至: {full_path}")


def test_stream():
    """测试流式（SSE）生成，带计时和阶段性保存"""
    print("⚡ 正在测试流式生成接口...")
    total_start_time = time.time()
    current_chapter = None
    current_chapter_content = ""
    current_chapter_start_time = 0
    full_content = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # 本次生成的时间戳

    with requests.post(
        BASE_URL,
        headers=headers,
        params={"use_qwen": USE_QWEN, "stream": True},
        data=json.dumps(payload),
        stream=True
    ) as resp:
        if resp.status_code != 200:
            print(f"❌ 请求失败: {resp.status_code} - {resp.text}")
            return
        resp.raise_for_status()

        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            json_str = line.strip().lstrip("data: ").strip()
            if not json_str:
                continue
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"\n⚠️ JSON解析失败：无效字符串 -> {json_str[:50]}... | 错误：{str(e)}")
                continue
            try:
                status = data.get("status")
                if status == "streaming":
                    # 实时输出片段并积累内容
                    content_part = data.get("content", "")
                    print(content_part, end="", flush=True)
                    current_chapter_content += content_part
                    full_content.append(content_part)
                    
                elif status == "chapter_start":
                    # 记录章节开始时间
                    current_chapter = data.get("chapter")
                    current_chapter_content = ""
                    current_chapter_start_time = time.time()
                    print(f"\n\n📖 开始章节：{current_chapter}\n")
                    full_content.append(f"\n\n📖 开始章节：{current_chapter}\n\n")
                    
                elif status == "summary_streaming":
                    content_part = data.get('content')
                    print(content_part, end="", flush=True)
                    current_chapter_content += content_part
                    full_content.append(content_part)
                    
                elif status == "chapter_completed":
                    # 计算章节耗时并保存
                    chapter_time = time.time() - current_chapter_start_time
                    chapter_summary = data.get('summary')
                    print(f"\n✅ 章节完成：{current_chapter}")
                    print(f"⏱ 章节耗时: {chapter_time:.2f} 秒")
                    print(f"🧠 摘要：{chapter_summary}\n")
                    
                    # 保存当前章节内容
                    chapter_filename = f"{current_chapter.replace(' ', '_').replace(':', '')}_{timestamp}.txt"
                    chapter_path = os.path.join(SAVE_DIR, chapter_filename)
                    with open(chapter_path, "w", encoding="utf-8") as f:
                        f.write(current_chapter_content)
                        f.write(f"\n\n🧠 摘要：{chapter_summary}")
                    print(f"💾 章节内容已保存至: {chapter_path}")
                    
                    full_content.append(f"\n\n✅ 章节完成：{current_chapter}\n")
                    full_content.append(f"⏱ 章节耗时: {chapter_time:.2f} 秒\n")
                    # full_content.append(f"🧠 摘要：{chapter_summary}\n\n")
                    
                elif status == "completed":
                    total_time = time.time() - total_start_time
                    print("\n🎉 所有章节生成完成！")
                    print(f"⏱ 总耗时: {total_time:.2f} 秒")
                    
                    # 保存完整内容
                    full_path = os.path.join(SAVE_DIR, f"full_content_{timestamp}.txt")
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(''.join(full_content))
                    print(f"💾 完整内容已保存至: {full_path}")
                    
            except Exception as e:
                print(f"\n⚠️ 处理数据时出错: {str(e)}")
                continue


# ======================================================
# 执行测试
# ======================================================

if __name__ == "__main__":
    if STREAM_MODE:
        test_stream()
    else:
        test_non_stream()