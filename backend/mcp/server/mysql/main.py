from mcp.server.fastmcp import FastMCP
from mysql.connector import connect, Error
from dotenv import load_dotenv
import os
import re
import logging
from typing import List, Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("operateMysql", port=12345)

# 危险的SQL关键词（不允许执行的操作）
DANGEROUS_KEYWORDS = {
    'write_operations': [
        'INSERT', 'UPDATE', 'DELETE', 'REPLACE', 'TRUNCATE',
        'MERGE', 'UPSERT'
    ],
    'ddl_operations': [
        'CREATE', 'ALTER', 'DROP', 'RENAME', 'COMMENT'
    ],
    'admin_operations': [
        'GRANT', 'REVOKE', 'FLUSH', 'RESET', 'KILL', 'SET',
        'START', 'STOP', 'RESTART', 'SHUTDOWN', 'RELOAD'
    ],
    'dangerous_functions': [
        'LOAD_FILE', 'INTO OUTFILE', 'INTO DUMPFILE',
        'LOAD DATA', 'SOURCE'
    ]
}

# 允许的只读操作
ALLOWED_KEYWORDS = [
    'SELECT', 'SHOW', 'DESCRIBE', 'DESC', 'EXPLAIN',
    'USE', 'WITH'  # WITH用于CTE
]


def get_db_config():
    """从环境变量获取数据库配置信息

    返回:
        dict: 包含数据库连接所需的配置信息

    异常:
        ValueError: 当必需的配置信息缺失时抛出
    """
    load_dotenv()

    config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DATABASE"),
        "charset": "utf8mb4",
        "use_unicode": True,
        "autocommit": False  # 关闭自动提交，增加安全性
    }

    logger.info(f"数据库配置: {config['host']}:{config['port']}/{config['database']}")

    if not all([config["user"], config["password"], config["database"]]):
        raise ValueError("缺少必需的数据库配置: MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE")

    return config


def validate_sql_security(sql: str) -> tuple[bool, str]:
    """验证SQL语句的安全性，只允许只读操作

    参数:
        sql (str): 要验证的SQL语句

    返回:
        tuple[bool, str]: (是否安全, 错误信息)
    """
    # 去除注释和多余空格
    clean_sql = re.sub(r'--.*?\n|/\*.*?\*/', '', sql, flags=re.DOTALL)
    clean_sql = re.sub(r'\s+', ' ', clean_sql.strip()).upper()

    if not clean_sql:
        return False, "SQL语句不能为空"

    # 检查危险操作
    all_dangerous = []
    for category, keywords in DANGEROUS_KEYWORDS.items():
        all_dangerous.extend(keywords)

    for keyword in all_dangerous:
        # 使用单词边界确保精确匹配
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, clean_sql):
            return False, f"不允许执行 {keyword} 操作，此工具仅支持只读查询"

    # 检查是否包含允许的操作
    has_allowed_operation = False
    for keyword in ALLOWED_KEYWORDS:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, clean_sql):
            has_allowed_operation = True
            break

    if not has_allowed_operation:
        return False, f"SQL语句必须以允许的只读操作开始: {', '.join(ALLOWED_KEYWORDS)}"

    # 检查是否尝试访问系统表（额外安全检查）
    system_schemas = ['mysql', 'information_schema', 'performance_schema', 'sys']
    # 但information_schema和performance_schema的只读访问是允许的
    dangerous_system_access = ['mysql.user', 'mysql.db', 'mysql.tables_priv']

    for dangerous_table in dangerous_system_access:
        if dangerous_table.upper() in clean_sql:
            return False, f"不允许访问敏感系统表: {dangerous_table}"

    return True, ""


@mcp.tool()
def execute_sql(query: str) -> List[str]:
    """执行安全的SQL查询语句（仅支持只读操作）

    参数:
        query (str): 要执行的SQL语句，支持多条语句以分号分隔
                    仅支持: SELECT, SHOW, DESCRIBE, DESC, EXPLAIN, USE

    返回:
        list: 包含查询结果的列表
        - 对于SELECT查询：返回CSV格式的结果，包含列名和数据
        - 对于其他查询：返回执行状态
        - 多条语句的结果以"---"分隔
        - 包含查询优化建议（如果有）

    安全限制:
        - 不允许 INSERT, UPDATE, DELETE 等写操作
        - 不允许 CREATE, ALTER, DROP 等DDL操作
        - 不允许访问敏感系统表
        - 自动添加查询超时限制
    """
    logger.info(f"收到SQL查询请求: {query[:100]}...")

    # 安全验证
    is_safe, error_msg = validate_sql_security(query)
    if not is_safe:
        logger.warning(f"SQL安全检查失败: {error_msg}")
        return [f"安全检查失败: {error_msg}"]

    config = get_db_config()
    try:
        with connect(**config) as conn:
            # 设置查询超时（30秒）
            conn.cmd_query("SET SESSION max_execution_time = 30000")

            with conn.cursor() as cursor:
                statements = [stmt.strip() for stmt in query.split(";") if stmt.strip()]
                results = []

                for i, statement in enumerate(statements):
                    try:
                        logger.info(f"执行第 {i + 1} 条SQL: {statement[:50]}...")
                        cursor.execute(statement)

                        if cursor.description:
                            columns = [desc[0] for desc in cursor.description]
                            rows = cursor.fetchall()

                            if not rows:
                                results.append("查询成功，但没有返回数据")
                                continue

                            # 限制返回行数（最多1000行）
                            if len(rows) > 1000:
                                logger.warning(f"查询返回 {len(rows)} 行，截取前1000行")
                                rows = rows[:1000]
                                results.append(f"警告: 查询返回超过1000行数据，已截取前1000行显示")

                            # 格式化数据
                            formatted_rows = []
                            for row in rows:
                                formatted_row = [
                                    "NULL" if value is None else str(value).replace(',', '，')  # 替换逗号避免CSV格式问题
                                    for value in row
                                ]
                                formatted_rows.append(",".join(formatted_row))

                            csv_result = "\n".join([",".join(columns)] + formatted_rows)
                            results.append(f"查询成功 (返回 {len(rows)} 行):\n{csv_result}")

                        else:
                            results.append("命令执行成功")

                    except Error as stmt_error:
                        error_msg = f" 执行语句失败: {str(stmt_error)}"
                        logger.error(f"SQL执行错误: {stmt_error}")
                        results.append(error_msg)

                # 添加优化建议
                # if optimization_tips:
                #     results.append(f"优化建议: {optimization_tips}")

                return ["\n---\n".join(results)]

    except Error as e:
        error_msg = f"数据库连接或执行错误: {str(e)}"
        logger.error(f"数据库错误: {e}")
        return [error_msg]


@mcp.tool()
def smart_query_tables(keyword: str = "") -> List[str]:
    """智能查询数据库表信息

    参数:
        keyword (str): 搜索关键词，可以是表名或表注释的一部分（可选）

    返回:
        list: 包含表信息的列表，包括表名、注释和行数统计
    """
    config = get_db_config()

    if keyword:
        # 搜索包含关键词的表
        sql = f"""
        SELECT 
            t.TABLE_NAME as '表名',
            t.TABLE_COMMENT as '表注释',
            t.TABLE_ROWS as '估计行数',
            ROUND((t.DATA_LENGTH + t.INDEX_LENGTH) / 1024 / 1024, 2) as '大小(MB)'
        FROM information_schema.TABLES t
        WHERE t.TABLE_SCHEMA = '{config['database']}'
        AND (t.TABLE_NAME LIKE '%{keyword}%' OR t.TABLE_COMMENT LIKE '%{keyword}%')
        ORDER BY t.TABLE_ROWS DESC
        """
    else:
        # 显示所有表
        sql = f"""
        SELECT 
            t.TABLE_NAME as '表名',
            t.TABLE_COMMENT as '表注释',
            t.TABLE_ROWS as '估计行数',
            ROUND((t.DATA_LENGTH + t.INDEX_LENGTH) / 1024 / 1024, 2) as '大小(MB)'
        FROM information_schema.TABLES t
        WHERE t.TABLE_SCHEMA = '{config['database']}'
        ORDER BY t.TABLE_ROWS DESC
        LIMIT 50
        """

    return execute_sql(sql)


@mcp.tool()
def get_table_structure(table_names: str) -> List[str]:
    """获取表的详细结构信息

    参数:
        table_names (str): 表名，多个表名用逗号分隔

    返回:
        list: 包含表结构信息的列表，包括字段名、类型、约束等详细信息
    """
    config = get_db_config()
    table_list = [name.strip() for name in table_names.split(",")]
    table_condition = "','".join(table_list)

    sql = f"""
    SELECT 
        c.TABLE_NAME as '表名',
        c.COLUMN_NAME as '字段名',
        c.COLUMN_TYPE as '字段类型',
        c.IS_NULLABLE as '允许空值',
        c.COLUMN_DEFAULT as '默认值',
        c.COLUMN_COMMENT as '字段注释',
        c.COLUMN_KEY as '键类型',
        c.EXTRA as '额外信息'
    FROM information_schema.COLUMNS c
    WHERE c.TABLE_SCHEMA = '{config['database']}'
    AND c.TABLE_NAME IN ('{table_condition}')
    ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION
    """

    return execute_sql(sql)


@mcp.tool()
def analyze_table_relationships(table_name: str = "") -> List[str]:
    """分析表的外键关系

    参数:
        table_name (str): 要分析的表名，为空则分析所有表的关系

    返回:
        list: 包含外键关系的列表
    """
    config = get_db_config()

    where_clause = f"AND kcu.TABLE_NAME = '{table_name}'" if table_name else ""

    sql = f"""
    SELECT 
        kcu.TABLE_NAME as '主表',
        kcu.COLUMN_NAME as '主表字段',
        kcu.REFERENCED_TABLE_NAME as '引用表',
        kcu.REFERENCED_COLUMN_NAME as '引用字段',
        rc.UPDATE_RULE as '更新规则',
        rc.DELETE_RULE as '删除规则'
    FROM information_schema.KEY_COLUMN_USAGE kcu
    JOIN information_schema.REFERENTIAL_CONSTRAINTS rc 
        ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
    WHERE kcu.TABLE_SCHEMA = '{config['database']}'
    AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
    {where_clause}
    ORDER BY kcu.TABLE_NAME, kcu.COLUMN_NAME
    """

    return execute_sql(sql)


@mcp.tool()
def get_database_overview() -> List[str]:
    """获取数据库概览信息

    返回:
        list: 包含数据库基本统计信息
    """
    config = get_db_config()

    sql = f"""
    SELECT 
        '{config['database']}' as '数据库名',
        COUNT(*) as '表数量',
        SUM(TABLE_ROWS) as '总行数估计',
        ROUND(SUM(DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as '总大小(MB)'
    FROM information_schema.TABLES 
    WHERE TABLE_SCHEMA = '{config['database']}'
    
    UNION ALL
    
    SELECT 
        '最大的表' as '统计项',
        TABLE_NAME as '表名',
        TABLE_ROWS as '行数',
        ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as '大小(MB)'
    FROM information_schema.TABLES 
    WHERE TABLE_SCHEMA = '{config['database']}'
    ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC
    LIMIT 1
    """

    return execute_sql(sql)

@mcp.tool()
def query_employee_qualifications(emp_name: str = "", qual_type: str = "") -> List[str]:
    """查询员工的资质证书信息
    
    参数:
        emp_name (str): 员工姓名（可选，支持模糊查询）
        qual_type (str): 资质类型（可选，支持模糊查询）
    
    返回:
        list: 包含员工资质信息的查询结果
    """
    conditions = []
    params = []
    
    if emp_name:
        conditions.append("e.emp_name LIKE %s")
        params.append(f"%{emp_name}%")
    
    if qual_type:
        conditions.append("eq.qual_name LIKE %s")
        params.append(f"%{qual_type}%")
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    sql = f"""
    SELECT 
        e.emp_name AS '员工姓名',
        e.position AS '职位',
        eq.qual_name AS '资质名称',
        eq.issue_date AS '颁发日期',
        eq.expire_date AS '过期日期',
        eq.qual_no AS '资质编号'
    FROM emp_qualification eq
    JOIN employee e ON eq.emp_id = e.id
    {where_clause}
    ORDER BY eq.expire_date ASC
    """
    
    # 处理参数化查询
    formatted_sql = sql % tuple(params) if params else sql
    return execute_sql(formatted_sql)


@mcp.tool()
def query_project_team(project_name: str = "") -> List[str]:
    """查询项目团队成员信息
    
    参数:
        project_name (str): 项目名称（可选，支持模糊查询）
    
    返回:
        list: 包含项目及参与人员信息的查询结果
    """
    condition = "WHERE p.project_name LIKE %s" if project_name else ""
    param = f"%{project_name}%" if project_name else ""
    
    sql = f"""
    SELECT 
        p.project_name AS '项目名称',
        p.project_no AS '项目编号',
        p.start_date AS '开始日期',
        p.end_date AS '结束日期',
        e.emp_name AS '团队成员',
        e.position AS '成员职位',
        epe.role AS '项目角色',
        epe.start_date AS '参与开始日期',
        epe.end_date AS '参与结束日期'
    FROM project p
    JOIN emp_project_experience epe ON p.id = epe.project_id
    JOIN employee e ON epe.emp_id = e.id
    {condition}
    ORDER BY p.project_name, epe.role
    """
    
    formatted_sql = sql % (param,) if project_name else sql
    return execute_sql(formatted_sql)


@mcp.tool()
def query_company_assets(expire_soon: bool = False) -> List[str]:
    """查询公司资质、专利和著作权等无形资产
    
    参数:
        expire_soon (bool): 是否只查询即将过期的资产（3个月内）
    
    返回:
        list: 包含公司无形资产信息的查询结果
    """
    expire_condition = """
    AND expire_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 3 MONTH)
    """ if expire_soon else ""
    
    # 资质查询
    qual_sql = f"""
    SELECT 
        '资质' AS '资产类型',
        company_name AS '公司名称',
        qual_name AS '资产名称',
        qual_no AS '编号',
        issue_date AS '颁发日期',
        expire_date AS '过期日期',
        '资质证书' AS '备注'
    FROM company_qualification
    WHERE 1=1 {expire_condition}
    """
    
    # 专利查询
    patent_sql = """
    SELECT 
        CONCAT('专利-', patent_type) AS '资产类型',
        company_name AS '公司名称',
        patent_name AS '资产名称',
        patent_no AS '编号',
        apply_date AS '申请日期',
        authorize_date AS '授权日期',
        IF(authorize_date IS NULL, '未授权', '已授权') AS '备注'
    FROM company_patent
    """
    
    # 著作权查询
    copyright_sql = """
    SELECT 
        CONCAT('著作权-', copyright_type) AS '资产类型',
        company_name AS '公司名称',
        copyright_name AS '资产名称',
        copyright_no AS '编号',
        apply_date AS '申请日期',
        authorize_date AS '授权日期',
        IF(authorize_date IS NULL, '未授权', '已授权') AS '备注'
    FROM company_copyright
    """
    
    # 组合查询并排序
    sql = f"""
    ({qual_sql}) UNION ALL
    ({patent_sql}) UNION ALL
    ({copyright_sql})
    ORDER BY 
        CASE WHEN expire_date IS NOT NULL THEN expire_date ELSE authorize_date END ASC,
        资产类型
    """
    
    return execute_sql(sql)


@mcp.tool()
def query_employee_education(education_level: str = "", major: str = "") -> List[str]:
    """查询员工学历信息
    
    参数:
        education_level (str): 学历层次（如"本科"、"硕士"，可选）
        major (str): 专业（可选，支持模糊查询）
    
    返回:
        list: 包含员工学历信息的查询结果
    """
    conditions = []
    params = []
    
    if education_level:
        conditions.append("ee.education = %s")
        params.append(education_level)
    
    if major:
        conditions.append("ee.major LIKE %s")
        params.append(f"%{major}%")
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    sql = f"""
    SELECT 
        e.emp_name AS '员工姓名',
        e.position AS '职位',
        ee.education AS '学历',
        ee.major AS '专业',
        ee.school AS '毕业院校',
        ee.grad_date AS '毕业日期',
        ee.diploma_no AS '毕业证编号'
    FROM emp_education ee
    JOIN employee e ON ee.emp_id = e.id
    {where_clause}
    ORDER BY ee.education DESC, ee.grad_date DESC
    """
    
    formatted_sql = sql % tuple(params) if params else sql
    return execute_sql(formatted_sql)


@mcp.tool()
def query_project_contracts(amount_min: float = None, sign_date_start: str = "", sign_date_end: str = "") -> List[str]:
    """查询项目合同信息
    
    参数:
        amount_min (float): 最小合同金额（可选）
        sign_date_start (str): 签订日期起始（格式YYYY-MM-DD，可选）
        sign_date_end (str): 签订日期结束（格式YYYY-MM-DD，可选）
    
    返回:
        list: 包含项目合同信息的查询结果
    """
    conditions = []
    params = []
    
    if amount_min is not None:
        conditions.append("pc.amount >= %s")
        params.append(amount_min)
    
    if sign_date_start:
        conditions.append("pc.sign_date >= %s")
        params.append(sign_date_start)
    
    if sign_date_end:
        conditions.append("pc.sign_date <= %s")
        params.append(sign_date_end)
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    sql = f"""
    SELECT 
        p.project_name AS '项目名称',
        pc.contract_no AS '合同编号',
        pc.party_a AS '甲方',
        pc.party_b AS '乙方',
        pc.sign_date AS '签订日期',
        pc.amount AS '合同金额(元)',
        p.start_date AS '项目开始日期',
        p.end_date AS '项目结束日期'
    FROM project_contract pc
    JOIN project p ON pc.project_id = p.id
    {where_clause}
    ORDER BY pc.amount DESC, pc.sign_date DESC
    """
    
    formatted_sql = sql % tuple(params) if params else sql
    return execute_sql(formatted_sql)


@mcp.tool()
def query_expiring_qualifications(days: int = 90) -> List[str]:
    """查询即将过期的资质（公司和个人）
    
    参数:
        days (int): 未来天数内即将过期（默认90天）
    
    返回:
        list: 包含即将过期资质信息的查询结果
    """
    sql = f"""
    -- 公司资质
    SELECT 
        '公司' AS '所属类型',
        company_name AS '名称',
        qual_name AS '资质名称',
        qual_no AS '编号',
        expire_date AS '过期日期',
        DATEDIFF(expire_date, CURDATE()) AS '剩余天数'
    FROM company_qualification
    WHERE expire_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL {days} DAY)
    
    UNION ALL
    
    -- 员工资质
    SELECT 
        '个人' AS '所属类型',
        e.emp_name AS '名称',
        eq.qual_name AS '资质名称',
        eq.qual_no AS '编号',
        eq.expire_date AS '过期日期',
        DATEDIFF(eq.expire_date, CURDATE()) AS '剩余天数'
    FROM emp_qualification eq
    JOIN employee e ON eq.emp_id = e.id
    WHERE eq.expire_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL {days} DAY)
    
    ORDER BY 剩余天数 ASC, 所属类型
    """
    
    return execute_sql(sql)

if __name__ == "__main__":
    logger.info("启动MySQL MCP服务器 (只读模式)")
    mcp.run(transport="stdio")