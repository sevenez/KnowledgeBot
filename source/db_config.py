"""
数据库配置文件
包含连接到MySQL数据库所需的配置信息
"""

# MySQL数据库配置（远程模式）
DB_CONFIG = {
    'host': 'direct.virtaicloud.com',
    'port': 28487,
    'user': 'mysql',
    'password': 'D8a)en(Yh1',
    'database': 'knowledge',
    'charset': 'utf8mb4'
}

# MySQL数据库配置（本地模式）
# DB_CONFIG = {
#     'host': 'localhost',
#     'port': 3306,
#     'user': 'mysql',
#     'password': 'D8a)en(Yh1',
#     'database': 'knowledge',
#     'charset': 'utf8mb4'
# }

# MySQL数据库配置（本地2）
# DB_CONFIG = {
#     'host': 'localhost',
#     'port': 3306,
#     'user': 'root',
#     'password': 'root',
#     'database': '企业知识库问答系统',
#     'charset': 'utf8mb4'
# }