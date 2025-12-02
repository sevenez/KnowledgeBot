"""
API配置文件
包含各种API的密钥和配置信息
"""

# MinerU API配置
MINERU_API = {
    'key': 'eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiI1MDMwNzUwNCIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc1NzUxMDI5NywiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiMTM4NTkwMjk0MzMiLCJvcGVuSWQiOm51bGwsInV1aWQiOiJjZjA1NGJkZS1mZDNhLTQwYTUtYjM4YS03YzZiMmJmYWM1MzciLCJlbWFpbCI6IiIsImV4cCI6MTc1ODcxOTg5N30.AoI-JfKePas3namMrP8AnYJK2NJZY3gA-kPDbHcq73fgJr7ek0sHXlP1c4heIXH-SN6QMdy8x6iaT2QHXn9ROw',  # 替换为实际的API密钥
    'url': 'https://mineru.net/api/v4/file-urls/batch',
    'max_files_per_batch': 200  # 每批最多200个文件（官网限制）
}