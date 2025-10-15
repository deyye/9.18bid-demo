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


def optimize_query_suggestion(sql: str) -> str:
    """为查询提供优化建议

    参数:
        sql (str): SQL查询语句

    返回:
        str: 优化建议
    """
    suggestions = []
    clean_sql = sql.upper().strip()

    # 检查是否使用了LIMIT
    if 'SELECT' in clean_sql and 'LIMIT' not in clean_sql:
        suggestions.append("建议添加 LIMIT 子句以避免返回过多数据")

    # 检查是否使用了SELECT *
    if 'SELECT *' in clean_sql:
        suggestions.append("建议指定具体的列名而不是使用 SELECT *")

    # 检查是否有WHERE条件
    if 'SELECT' in clean_sql and 'WHERE' not in clean_sql and 'LIMIT' not in clean_sql:
        suggestions.append("建议添加 WHERE 条件以缩小查询范围")

    return "; ".join(suggestions) if suggestions else ""


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

    # 获取优化建议
    # optimization_tips = optimize_query_suggestion(query)

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


if __name__ == "__main__":
    logger.info("启动MySQL MCP服务器 (只读模式)")
    mcp.run(transport="stdio")