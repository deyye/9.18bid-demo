# import requests
# import time
# import json

# url = "http://localhost:8000/api/content/generate-stream"

# def call_deepseek_api(
#     api_key,
#     prompt,
#     model="deepseek-reasoner",
#     stream=False,
#     temperature=0.7,
#     max_tokens=64000
# ):
#     """
#     调用DeepSeek API的通用方法
    
#     参数:
#         api_key (str): DeepSeek API密钥
#         prompt (str): 输入提示词
#         model (str): 模型名称，如"deepseek-chat"、"deepseek-coder"等
#         stream (bool): 是否启用流式响应
#         temperature (float): 生成温度，0-1之间，值越高随机性越强
#         max_tokens (int): 最大生成 tokens 数
        
#     返回:
#         非流式: 完整响应内容(str)
#         流式: 生成器，逐步返回内容
#     """
#     url = "https://api.deepseek.com"  # 官方API端点
    
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {api_key}"
#     }
    
#     payload = {
#         "model": model,
#         "messages": [{"role": "user", "content": prompt}],
#         "temperature": temperature,
#         "max_tokens": max_tokens,
#         "stream": stream
#     }
    
#     try:
#         response = requests.post(
#             url,
#             headers=headers,
#             json=payload,
#             stream=stream,
#             timeout=6000
#         )
#         response.raise_for_status()  # 抛出HTTP错误
        
#         if not stream:
#             # 非流式响应处理
#             result = response.json()
#             return result["choices"][0]["message"]["content"]
#         else:
#             # 流式响应处理（返回生成器）
#             def stream_generator():
#                 full_content = ""
#                 for line in response.iter_lines(decode_unicode=True):
#                     if line:
#                         # 处理SSE格式（去除"data: "前缀）
#                         if line.startswith("data: "):
#                             data_line = line[6:]
#                             try:
#                                 json_data = json.loads(data_line)
#                                 chunk = json_data["choices"][0]["delta"].get("content", "")
#                                 full_content += chunk
#                                 yield chunk
#                             except (json.JSONDecodeError, KeyError):
#                                 continue
#                 return full_content
            
#             return stream_generator()
            
#     except requests.exceptions.RequestException as e:
#         print(f"API请求失败: {str(e)}")
#         return None
    
# data = {
#     "outline": {
#         "details": [
#             {
#                 "id": "1",
#                 "title": "项目整体认知与实施方案",
#                 "description": "阐述对项目需求的理解、方案设计合理性及针对性措施",
#                 "children": [
#                     {
#                         "id": "1.1",
#                         "title": "项目理解与需求分析",
#                         "description": "分析招标文件核心需求及清河坊街区配电设施现状特征"
#                     },
#                     {
#                         "id": "1.2",
#                         "title": "总体技术方案",
#                         "description": "提出智能化运维体系架构及设备全生命周期管理策略"
#                     },
#                     {
#                         "id": "1.3",
#                         "title": "方案针对性设计",
#                         "description": "结合16处配电设施分布特点制定定制化监控与维护策略"
#                     }
#                 ]
#             }
#         ]
#     },
#     "project_overview": "项目概述信息分析报告\n\n\n 1. 项目基础信息提取\n- 项目全称（含招标编号）：清河坊街区变配电设施管理服务【项目编号：SCWSLJT2025GKFW038】\n- 招标单位名称及地址：杭州清河坊资产管理有限公司（浙江省杭州市中山中路 153 号）\n- 项目实施地点：杭州市上城区清河坊街区（含十六处配电设施，具体点位见附件 1）\n- 项目所属行业领域：电力设施运维管理、智慧用电安全监管\n\n\n 2. 项目背景分析\n- 政策依据：\n  - 《杭州市限额以下(小额)公共资源交易指引(试行)》\n  - 《关于加强杭州市小额项目规范管理工作的通知》\n  - 《杭州市上城区限额以下公共资源交易管理实施意见的通知》\n- 建设必要性说明：清河坊街区现有十六处变配电设施，设备使用年份较久且位置分散，采用常规人工维护管理方式存在维护成本高、不便于统一管理、无法实时监控运行情况等问题，需通过第三方专业单位提供线上 24 小时监控与线下运维服务，确保设备正常运行和使用安全。\n- 预期社会效益：\n  - 服务人群数量：覆盖清河坊街区约 336 户自有物业及 16 处配电设施\n  - 效率提升百分比：通过智能化监控系统实现 24 小时实时监测，预计减少人工巡检频次 50%\n  - 安全保障：消除电气火灾安全隐患，降低故障发生率，延长设备使用寿命\n\n\n 3. 规模参数采集\n- 建设规模：\n  - 配电设施点位数量：16 处（含 10 处高配房、6 处箱变）\n  - 配电房设备数量：总计 12 台 800KVA 变压器、16 台 630KVA 变压器、10 台 400KVA 变压器、1 台 1000KVA 变压器、168 路失电报警装置\n  - 服务范围：涵盖配电智能化远程监控系统提升及配电设施设备全责维护保养\n- 投资总额：51.2480 万元/年（含税包干）\n- 分项预算构成：\n  - 硬件设备：远程电力监控软硬件设备安装维护\n  - 软件系统：智能远程监控系统及数据分析平台\n  - 实施费用：高配绝缘工具、绝缘垫校验检测费用\n  - 运维服务：维保人员费用、保养耗材费用、应急服务保障费用\n  - 其他费用：临时性应急任务费用、政府要求的电力设备预防性试验检测费用等\n\n\n 4. 时间节点解析\n- 项目启动日期：2025-07-14（招标文件发布日期）\n- 关键里程碑：\n  - 响应文件提交截止时间：2025-07-25 14:15:00\n  - 开标时间：2025-07-25 14:15:00\n  - 成交公示时间：自收到评审报告之日起 3 日内\n  - 成交确认时间：公示期满无异议后 15 日内\n- 最终交付期限：自合同签订之日起一年（2025-07-25 14:15:00 后一年内完成服务）\n  - 逾期处罚条款：未按合同要求完成服务或存在违约行为，将承担相应赔偿责任，包括支付代理费、专家评审费等\n\n\n 5. 实施内容拆解\n- 系统架构图：通过智能远程监控系统实现配电房设备的 24 小时实时在线监测、集中监控，结合大数据分析进行用电调度和监控，实现配电房优化值守、快速故障诊断和处理。\n- 功能模块清单：\n  - 实时数据监测、采集功能（12 只多功能表计）\n  - 失电报警服务（168 路失电报警装置）\n  - 专业技术巡检及报告（192 次/年/点位）\n  - 电气设备季度分析报告（64 次/年/点位）\n  - 24 小时应急抢修服务（16 个点位，20 分钟内响应）\n- 工程量清单：\n  - 800KVA 变压器（12 台）\n  - 630KVA 变压器（16 台）\n  - 400KVA 变压器（10 台）\n  - 1000KVA 变压器（1 台）\n  - 高压柜（12 台）\n  - 低压柜（12 台）\n  - 电容柜（12 台）\n  - 多功能表计（168 只）\n  - 失电报警装置（168 路）\n  - 安全用具校验（10kV 绝缘手套、绝缘靴、验电笔、接地线、绝缘地毯等）\n\n\n 6. 技术特征识别\n- 技术标准要求：\n  - 遵循《电力设备预防性试验规程》（GB/T 7252-2001）\n  - 遵循《杭州市推进智慧式用电安全隐患监管服务系统建设工作方案》\n- 关键技术指标：\n  - 响应时间：24 小时热线电话响应，电力中断时 20 分钟内抵达现场\n  - 故障处理效率：服务工程师 2 小时内到达现场，一般问题不过天，重要设备故障不过夜\n  - 数据采集精度：实时监测电流、电压、有功、无功、温度等电气设备数据\n- 创新技术应用：\n  - 现有技术：采用电力自动化控制技术、物联网技术、大数据分析技术\n  - 拟采用的专利技术：未明确提及，但需通过智能化远程监控系统实现电气火灾隐患的实时发现与预警\n\n\n 7. 额外约束条件\n- 质量验收标准：\n  - 遵循《配电智能化运维服务月度考核表》（附件 2）\n  - 验收标准包括设备运行状态、清洁度、绝缘性能、接地情况等\n- 安全合规要求：\n  - 网络安全等级：未明确，但需通过电子交易平台“尚小易”和“招必得”进行数据电文交易\n  - 数据加密标准：响应文件需使用“.加密投标书”格式，通过 CA 数字证书加密\n- 运维服务条款：\n  - 服务响应时间：24 小时热线电话支持，临时停电、跳电值班人员 10 分钟内到现场\n  - 故障处理时限：服务工程师 2 小时内到达现场，一般问题不过天，重要设备故障不过夜\n  - 人员资质要求：拟派项目负责人需具有机电工程专业二级及以上建造师执业资格\"\n\r\n----------------------------849158541297654875317063\r\nContent-Disposition: form-data; name=\"requirements\"\r\n\r\n【评分项名称】：对项目的整体认知是否全面、整体方案是否合理、是否具有针对性  \n【权重/分值】：8分 [原文：8分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：项目实施目的及关键风险点分析情况  \n【权重/分值】：6分 [原文：6分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：服务过程中的工作安排合理性、工作思路清晰性、质量保障措施完整性  \n【权重/分值】：7分 [原文：7分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：针对大型庆典、活动等特殊情况的故障处理措施、应急预案、响应时间  \n【权重/分值】：8分 [原文：8分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：拟派项目团队人员配置及证书齐全性（安全员证、继保证、高压试验员证、电缆试验员证、高低压电工操作证）  \n【权重/分值】：10分 [原文：10分]  \n【评分标准】：证书齐全得满分；少一证扣1分，分值扣完为止。  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：变配电设施的管理、检测及维护的管理制度及作业规程的完整性、合理性、可行性  \n【权重/分值】：7分 [原文：7分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：供应商安全文明作业措施（包括安全保障、培训教育、事故善后）的合理性、可靠性  \n【权重/分值】：8分 [原文：8分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：项目实施过程中的重点、难点、关键点分析及对应措施和建议  \n【权重/分值】：3分 [原文：3分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：供应商的专业程度、有利于采购人的有利条件及增值服务内容  \n【权重/分值】：3分 [原文：3分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n\r\n----------------------------849158541297654875317063--\r\n"
# }

# # start_time = time.time()

# # 流式请求需要设置stream=True
# # response = requests.post(
# #     url,
# #     json=data,
# #     params={"use_qwen": True, "stream": True},
# #     stream=True
# # )

# # full_content = ""
# # try:
# #     for line in response.iter_lines(decode_unicode=True):
# #         if line:
# #             # 解析SSE格式数据（去除"data: "前缀）
# #             if line.startswith("data: "):
# #                 data_line = line[6:]
# #                 # if data_line == "[DONE]":
# #                     # break
# #                 try:
# #                     json_data = json.loads(data_line)
# #                     if json_data["status"] == "streaming":
# #                         full_content = json_data["full_content"]
# #                         # 打印实时进度（可选）
# #                         print(f"\r已接收: {len(full_content)}字符", end="")
# #                 except json.JSONDecodeError:
# #                     continue
# # finally:
# #     end_time = time.time()
# #     elapsed_time = end_time - start_time
# #     print(f"\n流式生成完成，耗时: {elapsed_time:.2f}秒")
# #     print(f"总内容长度: {len(full_content)}字符")
# #     print(f"生成的文本内容如下：{full_content}")

# if __name__ == "__main__":
#     API_KEY = "sk-b39d9a64aadf4d65bbb913ebfa7b02f8"  # 替换为实际API密钥
#     data = {
#         "outline": {
#             "details": [
#                 {
#                     "id": "1",
#                     "title": "项目整体认知与实施方案",
#                     "description": "阐述对项目需求的理解、方案设计合理性及针对性措施",
#                     "children": [
#                         {
#                             "id": "1.1",
#                             "title": "项目理解与需求分析",
#                             "description": "分析招标文件核心需求及清河坊街区配电设施现状特征"
#                         },
#                         {
#                             "id": "1.2",
#                             "title": "总体技术方案",
#                             "description": "提出智能化运维体系架构及设备全生命周期管理策略"
#                         },
#                         {
#                             "id": "1.3",
#                             "title": "方案针对性设计",
#                             "description": "结合16处配电设施分布特点制定定制化监控与维护策略"
#                         }
#                     ]
#                 }
#             ]
#         },
#         "project_overview": "项目概述信息分析报告\n\n\n 1. 项目基础信息提取\n- 项目全称（含招标编号）：清河坊街区变配电设施管理服务【项目编号：SCWSLJT2025GKFW038】\n- 招标单位名称及地址：杭州清河坊资产管理有限公司（浙江省杭州市中山中路 153 号）\n- 项目实施地点：杭州市上城区清河坊街区（含十六处配电设施，具体点位见附件 1）\n- 项目所属行业领域：电力设施运维管理、智慧用电安全监管\n\n\n 2. 项目背景分析\n- 政策依据：\n  - 《杭州市限额以下(小额)公共资源交易指引(试行)》\n  - 《关于加强杭州市小额项目规范管理工作的通知》\n  - 《杭州市上城区限额以下公共资源交易管理实施意见的通知》\n- 建设必要性说明：清河坊街区现有十六处变配电设施，设备使用年份较久且位置分散，采用常规人工维护管理方式存在维护成本高、不便于统一管理、无法实时监控运行情况等问题，需通过第三方专业单位提供线上 24 小时监控与线下运维服务，确保设备正常运行和使用安全。\n- 预期社会效益：\n  - 服务人群数量：覆盖清河坊街区约 336 户自有物业及 16 处配电设施\n  - 效率提升百分比：通过智能化监控系统实现 24 小时实时监测，预计减少人工巡检频次 50%\n  - 安全保障：消除电气火灾安全隐患，降低故障发生率，延长设备使用寿命\n\n\n 3. 规模参数采集\n- 建设规模：\n  - 配电设施点位数量：16 处（含 10 处高配房、6 处箱变）\n  - 配电房设备数量：总计 12 台 800KVA 变压器、16 台 630KVA 变压器、10 台 400KVA 变压器、1 台 1000KVA 变压器、168 路失电报警装置\n  - 服务范围：涵盖配电智能化远程监控系统提升及配电设施设备全责维护保养\n- 投资总额：51.2480 万元/年（含税包干）\n- 分项预算构成：\n  - 硬件设备：远程电力监控软硬件设备安装维护\n  - 软件系统：智能远程监控系统及数据分析平台\n  - 实施费用：高配绝缘工具、绝缘垫校验检测费用\n  - 运维服务：维保人员费用、保养耗材费用、应急服务保障费用\n  - 其他费用：临时性应急任务费用、政府要求的电力设备预防性试验检测费用等\n\n\n 4. 时间节点解析\n- 项目启动日期：2025-07-14（招标文件发布日期）\n- 关键里程碑：\n  - 响应文件提交截止时间：2025-07-25 14:15:00\n  - 开标时间：2025-07-25 14:15:00\n  - 成交公示时间：自收到评审报告之日起 3 日内\n  - 成交确认时间：公示期满无异议后 15 日内\n- 最终交付期限：自合同签订之日起一年（2025-07-25 14:15:00 后一年内完成服务）\n  - 逾期处罚条款：未按合同要求完成服务或存在违约行为，将承担相应赔偿责任，包括支付代理费、专家评审费等\n\n\n 5. 实施内容拆解\n- 系统架构图：通过智能远程监控系统实现配电房设备的 24 小时实时在线监测、集中监控，结合大数据分析进行用电调度和监控，实现配电房优化值守、快速故障诊断和处理。\n- 功能模块清单：\n  - 实时数据监测、采集功能（12 只多功能表计）\n  - 失电报警服务（168 路失电报警装置）\n  - 专业技术巡检及报告（192 次/年/点位）\n  - 电气设备季度分析报告（64 次/年/点位）\n  - 24 小时应急抢修服务（16 个点位，20 分钟内响应）\n- 工程量清单：\n  - 800KVA 变压器（12 台）\n  - 630KVA 变压器（16 台）\n  - 400KVA 变压器（10 台）\n  - 1000KVA 变压器（1 台）\n  - 高压柜（12 台）\n  - 低压柜（12 台）\n  - 电容柜（12 台）\n  - 多功能表计（168 只）\n  - 失电报警装置（168 路）\n  - 安全用具校验（10kV 绝缘手套、绝缘靴、验电笔、接地线、绝缘地毯等）\n\n\n 6. 技术特征识别\n- 技术标准要求：\n  - 遵循《电力设备预防性试验规程》（GB/T 7252-2001）\n  - 遵循《杭州市推进智慧式用电安全隐患监管服务系统建设工作方案》\n- 关键技术指标：\n  - 响应时间：24 小时热线电话响应，电力中断时 20 分钟内抵达现场\n  - 故障处理效率：服务工程师 2 小时内到达现场，一般问题不过天，重要设备故障不过夜\n  - 数据采集精度：实时监测电流、电压、有功、无功、温度等电气设备数据\n- 创新技术应用：\n  - 现有技术：采用电力自动化控制技术、物联网技术、大数据分析技术\n  - 拟采用的专利技术：未明确提及，但需通过智能化远程监控系统实现电气火灾隐患的实时发现与预警\n\n\n 7. 额外约束条件\n- 质量验收标准：\n  - 遵循《配电智能化运维服务月度考核表》（附件 2）\n  - 验收标准包括设备运行状态、清洁度、绝缘性能、接地情况等\n- 安全合规要求：\n  - 网络安全等级：未明确，但需通过电子交易平台“尚小易”和“招必得”进行数据电文交易\n  - 数据加密标准：响应文件需使用“.加密投标书”格式，通过 CA 数字证书加密\n- 运维服务条款：\n  - 服务响应时间：24 小时热线电话支持，临时停电、跳电值班人员 10 分钟内到现场\n  - 故障处理时限：服务工程师 2 小时内到达现场，一般问题不过天，重要设备故障不过夜\n  - 人员资质要求：拟派项目负责人需具有机电工程专业二级及以上建造师执业资格\"\n\r\n----------------------------849158541297654875317063\r\nContent-Disposition: form-data; name=\"requirements\"\r\n\r\n【评分项名称】：对项目的整体认知是否全面、整体方案是否合理、是否具有针对性  \n【权重/分值】：8分 [原文：8分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：项目实施目的及关键风险点分析情况  \n【权重/分值】：6分 [原文：6分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：服务过程中的工作安排合理性、工作思路清晰性、质量保障措施完整性  \n【权重/分值】：7分 [原文：7分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：针对大型庆典、活动等特殊情况的故障处理措施、应急预案、响应时间  \n【权重/分值】：8分 [原文：8分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：拟派项目团队人员配置及证书齐全性（安全员证、继保证、高压试验员证、电缆试验员证、高低压电工操作证）  \n【权重/分值】：10分 [原文：10分]  \n【评分标准】：证书齐全得满分；少一证扣1分，分值扣完为止。  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：变配电设施的管理、检测及维护的管理制度及作业规程的完整性、合理性、可行性  \n【权重/分值】：7分 [原文：7分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：供应商安全文明作业措施（包括安全保障、培训教育、事故善后）的合理性、可靠性  \n【权重/分值】：8分 [原文：8分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：项目实施过程中的重点、难点、关键点分析及对应措施和建议  \n【权重/分值】：3分 [原文：3分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：供应商的专业程度、有利于采购人的有利条件及增值服务内容  \n【权重/分值】：3分 [原文：3分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n\r\n----------------------------849158541297654875317063--\r\n"
#     }
#     PROMPT = f"""你是一名专业的内容生成助手，负责根据大纲生成项目文档。项目概述：{data["project_overview"]}\n\n目录大纲：{data['outline']}\n\n请逐条生成内容,每个二级子目录不少于3000字。"""
    
#     # 非流式调用
#     # print("===== 非流式响应 =====")
#     # start_time = time.time()
#     # result = call_deepseek_api(API_KEY, PROMPT, stream=False)
#     # if result:
#     #     print(f"耗时: {time.time() - start_time:.2f}秒")
#     #     print(result)
    
#     # 流式调用
#     print("\n===== 流式响应 =====")
#     start_time = time.time()
#     stream = call_deepseek_api(API_KEY, PROMPT, stream=True)
#     if stream:
#         full_content = ""
#         for chunk in stream:
#             print(chunk, end="", flush=True)
#             full_content += chunk
#         print(f"\n耗时: {time.time() - start_time:.2f}秒")
#         print(f"总长度: {len(full_content)}字符")


import requests
import json
import time
import argparse
from tqdm import tqdm
import os

# 配置API基础URL
BASE_URL = "http://localhost:8000/api/content"

def generate_chapter_content(chapter, overview, target_words, use_qwen=True):
    """
    生成单章节内容，保持 project_data 格式:
    {
        "project_overview": "...",
        "outline": { "details": [chapter] }
    }
    """
    project_data = {
        "project_overview": overview,
        "outline": {
            "details": [chapter]
        }
    }

    params = {"use_qwen": use_qwen, "stream": True}
    start_time = time.time()
    full_content = ""

    try:
        with requests.post(
            f"{BASE_URL}/generate-stream",
            json=project_data,
            params=params,
            stream=True,
            headers={"Content-Type": "application/json"}
        ) as r:
            r.raise_for_status()
            pbar = tqdm(total=target_words, unit="字", desc=f"生成 {chapter['title']}")
            last_length = 0

            for line in r.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:]
                try:
                    json_data = json.loads(data)
                    if json_data["status"] == "streaming":
                        full_content = json_data["full_content"]
                        current_length = len(full_content)
                        progress = current_length - last_length
                        if progress > 0:
                            pbar.update(progress)
                            last_length = current_length
                        # if current_length >= target_words:
                        #     break
                    elif json_data["status"] == "error":
                        raise Exception(json_data["message"])
                except json.JSONDecodeError:
                    continue
            pbar.close()

            final_length = len(full_content)
            if final_length < target_words:
                print(f"⚠️ 章节 {chapter['title']} 生成字数不足（{final_length}/{target_words}字），已接收API返回的全部内容")

    except requests.exceptions.ConnectionError as conn_e:
    # 针对性捕获“连接错误”，输出详细信息
        error_msg = f"网络连接失败（检查BASE_URL是否正确）: {str(conn_e)}"
        print(f"❌ 章节 {chapter['title']} 生成失败: {error_msg}")
        return full_content, False, time.time() - start_time
    except requests.exceptions.Timeout as timeout_e:
        # 针对性捕获“超时错误”
        error_msg = f"API请求超时（可能服务繁忙）: {str(timeout_e)}"
        print(f"❌ 章节 {chapter['title']} 生成失败: {error_msg}")
        return full_content, False, time.time() - start_time
    except Exception as e:
        # 捕获其他所有异常，确保错误信息完整
        print(f"❌ 章节 {chapter['title']} 生成失败: {str(e)}")
        return full_content, False, time.time() - start_time

    return full_content, True, time.time() - start_time



def generate_large_content(use_qwen=True, target_words=250000):
    """分章节动态生成长文内容"""

    # ===== 项目目录结构 =====
    project_data = {
        "outline": {
            "details": [
                {
                    "id": "1",
                    "title": "项目整体认知与实施方案",
                    "description": "阐述对项目需求的理解、方案设计合理性及针对性措施",
                    "children": [
                        {
                            "id": "1.1",
                            "title": "项目理解与需求分析",
                            "description": "分析招标文件核心需求及清河坊街区配电设施现状特征"
                        },
                        {
                            "id": "1.2",
                            "title": "总体技术方案",
                            "description": "提出智能化运维体系架构及设备全生命周期管理策略"
                        },
                        {
                            "id": "1.3",
                            "title": "方案针对性设计",
                            "description": "结合16处配电设施分布特点制定定制化监控与维护策略"
                        }
                    ]
                },
                {
                    "id": "2",
                    "title": "实施目标与风险管控",
                    "description": "明确项目实施目的及关键风险识别与应对措施",
                    "children": [
                        {
                            "id": "2.1",
                            "title": "项目实施目标",
                            "description": "实现设备运行状态实时监测与故障率降低30%的量化目标"
                        },
                        {
                            "id": "2.2",
                            "title": "关键风险点分析",
                            "description": "识别老旧设备改造风险、多点位协同管理风险及应急响应风险"
                        },
                        {
                            "id": "2.3",
                            "title": "风险应对策略",
                            "description": "制定设备兼容性测试方案、多点位巡检优化方案及应急资源预置计划"
                        }
                    ]
                },
                {
                    "id": "3",
                    "title": "服务执行体系设计",
                    "description": "构建覆盖全周期的服务流程与质量保障机制",
                    "children": [
                        {
                            "id": "3.1",
                            "title": "工作安排与执行思路",
                            "description": "规划24小时值守、季度巡检、年度预防性试验等标准化作业流程"
                        },
                        {
                            "id": "3.2",
                            "title": "质量保障措施",
                            "description": "建立三级质量检查制度（自检/专检/抽检）及月度考核机制"
                        },
                        {
                            "id": "3.3",
                            "title": "服务标准体系",
                            "description": "制定设备清洁度、绝缘性能、接地电阻等12项具体验收指标"
                        }
                    ]
                },
                {
                    "id": "4",
                    "title": "专项应急保障方案",
                    "description": "针对特殊场景的故障处理机制与快速响应体系",
                    "children": [
                        {
                            "id": "4.1",
                            "title": "大型活动保障预案",
                            "description": "制定节假日/庆典期间双倍值守、备用电源接入等专项保障措施"
                        },
                        {
                            "id": "4.2",
                            "title": "应急响应机制",
                            "description": "明确10分钟现场响应、2小时工程师到场、故障处理不过夜的三级响应标准"
                        },
                        {
                            "id": "4.3",
                            "title": "应急资源储备",
                            "description": "配置16处点位专用应急工具包及24小时备件供应体系"
                        }
                    ]
                },
                {
                    "id": "5",
                    "title": "技术团队与资质体系",
                    "description": "展示项目团队专业资质与证书完备性",
                    "children": [
                        {
                            "id": "5.1",
                            "title": "核心人员配置",
                            "description": "配置具备机电工程二级建造师资质的项目经理及持证技术团队"
                        },
                        {
                            "id": "5.2",
                            "title": "资质证书清单",
                            "description": "列明安全员证、继保证、高压试验员证等5类必备证书的持证情况"
                        },
                        {
                            "id": "5.3",
                            "title": "团队培训机制",
                            "description": "建立年度安全操作规程培训及应急演练考核制度"
                        }
                    ]
                },
                {
                    "id": "6",
                    "title": "运维管理制度建设",
                    "description": "构建符合电力行业规范的运维管理体系",
                    "children": [
                        {
                            "id": "6.1",
                            "title": "设备管理制度",
                            "description": "制定变压器/高压柜/低压柜等设备的差异化运维管理规范"
                        },
                        {
                            "id": "6.2",
                            "title": "作业规程体系",
                            "description": "编制包含绝缘工具校验、接地电阻测试等18项标准作业流程"
                        },
                        {
                            "id": "6.3",
                            "title": "质量追溯机制",
                            "description": "建立设备故障记录、维修档案、预防性试验数据的全周期追溯系统"
                        }
                    ]
                },
                {
                    "id": "7",
                    "title": "安全文明作业体系",
                    "description": "保障运维过程中的安全规范与文明施工标准",
                    "children": [
                        {
                            "id": "7.1",
                            "title": "安全防护措施",
                            "description": "配置10kV绝缘防护装备及智能监控系统安全接入方案"
                        },
                        {
                            "id": "7.2",
                            "title": "培训教育机制",
                            "description": "实施季度安全操作培训及年度应急演练考核制度"
                        },
                        {
                            "id": "7.3",
                            "title": "事故处理预案",
                            "description": "制定设备故障导致的电气火灾应急处置流程与责任追溯机制"
                        }
                    ]
                },
                {
                    "id": "8",
                    "title": "实施难点与优化建议",
                    "description": "分析项目实施中的技术难点与管理挑战",
                    "children": [
                        {
                            "id": "8.1",
                            "title": "重点难点识别",
                            "description": "识别老旧设备兼容性、多点位协同调度、数据实时性等关键技术难点"
                        },
                        {
                            "id": "8.2",
                            "title": "技术应对措施",
                            "description": "提出设备改造兼容性测试、边缘计算节点部署等解决方案"
                        },
                        {
                            "id": "8.3",
                            "title": "管理优化建议",
                            "description": "建议建立智能巡检路径优化算法及多部门协同响应机制"
                        }
                    ]
                },
                {
                    "id": "9",
                    "title": "技术优势与增值服务",
                    "description": "展示供应商技术实力与附加价值创造能力",
                    "children": [
                        {
                            "id": "9.1",
                            "title": "专业能力证明",
                            "description": "提供电力设施运维相关专利技术及成功案例佐证材料"
                        },
                        {
                            "id": "9.2",
                            "title": "增值服务方案",
                            "description": "包含设备健康度预测分析、能效优化建议等延伸服务内容"
                        },
                        {
                            "id": "9.3",
                            "title": "技术保障承诺",
                            "description": "承诺采用GB/T 7252-2001标准实施预防性试验检测服务"
                        }
                    ]
                }
            ]
        },
        "project_overview": "项目概述信息分析报告\n\n\n 1. 项目基础信息提取\n- 项目全称（含招标编号）：清河坊街区变配电设施管理服务【项目编号：SCWSLJT2025GKFW038】\n- 招标单位名称及地址：杭州清河坊资产管理有限公司（浙江省杭州市中山中路 153 号）\n- 项目实施地点：杭州市上城区清河坊街区（含十六处配电设施，具体点位见附件 1）\n- 项目所属行业领域：电力设施运维管理、智慧用电安全监管\n\n\n 2. 项目背景分析\n- 政策依据：\n  - 《杭州市限额以下(小额)公共资源交易指引(试行)》\n  - 《关于加强杭州市小额项目规范管理工作的通知》\n  - 《杭州市上城区限额以下公共资源交易管理实施意见的通知》\n- 建设必要性说明：清河坊街区现有十六处变配电设施，设备使用年份较久且位置分散，采用常规人工维护管理方式存在维护成本高、不便于统一管理、无法实时监控运行情况等问题，需通过第三方专业单位提供线上 24 小时监控与线下运维服务，确保设备正常运行和使用安全。\n- 预期社会效益：\n  - 服务人群数量：覆盖清河坊街区约 336 户自有物业及 16 处配电设施\n  - 效率提升百分比：通过智能化监控系统实现 24 小时实时监测，预计减少人工巡检频次 50%\n  - 安全保障：消除电气火灾安全隐患，降低故障发生率，延长设备使用寿命\n\n\n 3. 规模参数采集\n- 建设规模：\n  - 配电设施点位数量：16 处（含 10 处高配房、6 处箱变）\n  - 配电房设备数量：总计 12 台 800KVA 变压器、16 台 630KVA 变压器、10 台 400KVA 变压器、1 台 1000KVA 变压器、168 路失电报警装置\n  - 服务范围：涵盖配电智能化远程监控系统提升及配电设施设备全责维护保养\n- 投资总额：51.2480 万元/年（含税包干）\n- 分项预算构成：\n  - 硬件设备：远程电力监控软硬件设备安装维护\n  - 软件系统：智能远程监控系统及数据分析平台\n  - 实施费用：高配绝缘工具、绝缘垫校验检测费用\n  - 运维服务：维保人员费用、保养耗材费用、应急服务保障费用\n  - 其他费用：临时性应急任务费用、政府要求的电力设备预防性试验检测费用等\n\n\n 4. 时间节点解析\n- 项目启动日期：2025-07-14（招标文件发布日期）\n- 关键里程碑：\n  - 响应文件提交截止时间：2025-07-25 14:15:00\n  - 开标时间：2025-07-25 14:15:00\n  - 成交公示时间：自收到评审报告之日起 3 日内\n  - 成交确认时间：公示期满无异议后 15 日内\n- 最终交付期限：自合同签订之日起一年（2025-07-25 14:15:00 后一年内完成服务）\n  - 逾期处罚条款：未按合同要求完成服务或存在违约行为，将承担相应赔偿责任，包括支付代理费、专家评审费等\n\n\n 5. 实施内容拆解\n- 系统架构图：通过智能远程监控系统实现配电房设备的 24 小时实时在线监测、集中监控，结合大数据分析进行用电调度和监控，实现配电房优化值守、快速故障诊断和处理。\n- 功能模块清单：\n  - 实时数据监测、采集功能（12 只多功能表计）\n  - 失电报警服务（168 路失电报警装置）\n  - 专业技术巡检及报告（192 次/年/点位）\n  - 电气设备季度分析报告（64 次/年/点位）\n  - 24 小时应急抢修服务（16 个点位，20 分钟内响应）\n- 工程量清单：\n  - 800KVA 变压器（12 台）\n  - 630KVA 变压器（16 台）\n  - 400KVA 变压器（10 台）\n  - 1000KVA 变压器（1 台）\n  - 高压柜（12 台）\n  - 低压柜（12 台）\n  - 电容柜（12 台）\n  - 多功能表计（168 只）\n  - 失电报警装置（168 路）\n  - 安全用具校验（10kV 绝缘手套、绝缘靴、验电笔、接地线、绝缘地毯等）\n\n\n 6. 技术特征识别\n- 技术标准要求：\n  - 遵循《电力设备预防性试验规程》（GB/T 7252-2001）\n  - 遵循《杭州市推进智慧式用电安全隐患监管服务系统建设工作方案》\n- 关键技术指标：\n  - 响应时间：24 小时热线电话响应，电力中断时 20 分钟内抵达现场\n  - 故障处理效率：服务工程师 2 小时内到达现场，一般问题不过天，重要设备故障不过夜\n  - 数据采集精度：实时监测电流、电压、有功、无功、温度等电气设备数据\n- 创新技术应用：\n  - 现有技术：采用电力自动化控制技术、物联网技术、大数据分析技术\n  - 拟采用的专利技术：未明确提及，但需通过智能化远程监控系统实现电气火灾隐患的实时发现与预警\n\n\n 7. 额外约束条件\n- 质量验收标准：\n  - 遵循《配电智能化运维服务月度考核表》（附件 2）\n  - 验收标准包括设备运行状态、清洁度、绝缘性能、接地情况等\n- 安全合规要求：\n  - 网络安全等级：未明确，但需通过电子交易平台“尚小易”和“招必得”进行数据电文交易\n  - 数据加密标准：响应文件需使用“.加密投标书”格式，通过 CA 数字证书加密\n- 运维服务条款：\n  - 服务响应时间：24 小时热线电话支持，临时停电、跳电值班人员 10 分钟内到现场\n  - 故障处理时限：服务工程师 2 小时内到达现场，一般问题不过天，重要设备故障不过夜\n  - 人员资质要求：拟派项目负责人需具有机电工程专业二级及以上建造师执业资格\"\n\r\n----------------------------849158541297654875317063\r\nContent-Disposition: form-data; name=\"requirements\"\r\n\r\n【评分项名称】：对项目的整体认知是否全面、整体方案是否合理、是否具有针对性  \n【权重/分值】：8分 [原文：8分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：项目实施目的及关键风险点分析情况  \n【权重/分值】：6分 [原文：6分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：服务过程中的工作安排合理性、工作思路清晰性、质量保障措施完整性  \n【权重/分值】：7分 [原文：7分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：针对大型庆典、活动等特殊情况的故障处理措施、应急预案、响应时间  \n【权重/分值】：8分 [原文：8分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：拟派项目团队人员配置及证书齐全性（安全员证、继保证、高压试验员证、电缆试验员证、高低压电工操作证）  \n【权重/分值】：10分 [原文：10分]  \n【评分标准】：证书齐全得满分；少一证扣1分，分值扣完为止。  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：变配电设施的管理、检测及维护的管理制度及作业规程的完整性、合理性、可行性  \n【权重/分值】：7分 [原文：7分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：供应商安全文明作业措施（包括安全保障、培训教育、事故善后）的合理性、可靠性  \n【权重/分值】：8分 [原文：8分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：项目实施过程中的重点、难点、关键点分析及对应措施和建议  \n【权重/分值】：3分 [原文：3分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n【评分项名称】：供应商的专业程度、有利于采购人的有利条件及增值服务内容  \n【权重/分值】：3分 [原文：3分]  \n【评分标准】：未提及  \n【数据来源】：第四章 评审办法→技术部分（60分） [原文：第24页]  \n\r\n----------------------------849158541297654875317063--\r\n"
    }

    overview = project_data["project_overview"]
    outline = project_data["outline"]["details"]

    # ======== 动态分配章节字数 ========
    total_weight = sum(len(ch["children"]) + len(ch["description"]) / 20 for ch in outline)
    for ch in outline:
        ch["weight"] = len(ch["children"]) + len(ch["description"]) / 20

    print(f"计划生成总字数: {target_words}字，共 {len(outline)} 章。")

    output_file = "generated_large_content.txt"
    if os.path.exists(output_file):
        os.remove(output_file)

    total_start = time.time()
    total_words = 0

    # ======== 逐章节生成 ========
    for i, chapter in enumerate(outline, 1):
        chapter_target = int(target_words * (chapter["weight"] / total_weight))
        print(f"\n=== [{i}/{len(outline)}] 开始生成章节: {chapter['title']} (目标约 {chapter_target} 字) ===")

        content, success, elapsed = generate_chapter_content(
            chapter, overview, chapter_target, use_qwen=use_qwen
        )

        # 保存拼接结果
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"\n\n# {chapter['title']}\n\n")
            # if success:
            #     f.write(content)
            #     total_words += len(content)
            #     print(f"✅ 已完成 {chapter['title']}，耗时 {elapsed:.2f} 秒。")
            # else:
            #     f.write("【本章节生成失败，请手动补充】\n")
            #     print(f"⚠️ 跳过 {chapter['title']}。")
            f.write(content)
            total_words += len(content)
            print(f"✅ 已完成 {chapter['title']}，耗时 {elapsed:.2f} 秒。")

    total_elapsed = time.time() - total_start

    print(f"\n✅ 全部章节生成完成！总字数约 {total_words} 字，用时 {total_elapsed:.2f} 秒。")
    print(f"📄 输出文件: {output_file}")

    return {
        "success": True,
        "total_words": total_words,
        "time_elapsed": total_elapsed,
        "file_saved": output_file
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="分章节生成大篇幅内容（保持统一project_data结构）")
    parser.add_argument("--model", choices=["qwen", "openai"], default="qwen", help="选择使用的模型")
    parser.add_argument("--target", type=int, default=250000, help="目标生成字数")
    args = parser.parse_args()

    print(f"开始生成约{args.target}字的内容，使用{'Qwen' if args.model == 'qwen' else 'OpenAI'}模型...")
    result = generate_large_content(use_qwen=(args.model == 'qwen'), target_words=args.target)

    if result["success"]:
        print(f"\n🎉 生成完成，总字数: {result['total_words']}，用时: {result['time_elapsed']:.2f} 秒。")
    else:
        print(f"\n❌ 生成失败。")