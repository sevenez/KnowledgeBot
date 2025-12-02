import requests
import os
from glob import glob
from os import environ
 
# 配置参数
 
file_dir="../Documents" #输入你的文件路径（上级目录）
max_files_per_batch = 200  # 每批最多200个文件 这是官网限制
 
# 获取所有支持的文件
file_patterns = ["*.pdf", "*.dot", "*.doc", "*.docx", "*.ppt", "*.ppa", "*.pptx", "*.png", 
                "*.jfif", "*.pjpeg", "*.jpeg", "*.pjp", "*.jpg"]
all_files = []
for pattern in file_patterns:
    all_files.extend(glob(os.path.join(file_dir, pattern)))

if not all_files:
    print(f"未在 {file_dir} 中找到任何支持的文件")
    exit()
 
# 从环境变量获取API密钥
api_key = environ.get('MINERU_API_KEY')
if not api_key:
    print("错误：未设置MINERU_API_KEY环境变量")
    exit(1)

# API配置
url = 'https://mineru.net/api/v4/file-urls/batch'
header = {
    'Content-Type': 'application/json',
    "Authorization": f"Bearer {api_key}"  # 使用环境变量中的API密钥
}
 
# 
i=0
print(i)
batch_idx = max_files_per_batch * i  # 第二批次的起始索引（200）
batch_files = all_files[batch_idx : batch_idx + max_files_per_batch]
 
if not batch_files:
    print("第二批没有文件可处理")
    exit()
 
# 构建文件数据
files_data = [{
    "name": os.path.basename(file_path),
    "is_ocr": True,
    "data_id": f"{os.path.splitext(os.path.basename(file_path))[0]}_b2",
    "language": "ch",  # 批次号固定为2
} for file_path in batch_files]
 
# print(f"\n正在处理第"+i+"批次（共 {len(batch_files)} 个文件）")
 
try:
    # 获取上传URL
    response = requests.post(url, headers=header, json={
        "enable_formula": True,
        "language": "en",
        "layout_model": "doclayout_yolo",
        "enable_table": True,
        "files": files_data
    })
 
    if response.status_code != 200:
        print(f"请求失败，状态码：{response.status_code}")
        exit()
 
    result = response.json()
    if result["code"] != 0:
        print(f'申请失败，原因：{result.get("msg", "未知错误")}')
        exit()
 
    # 上传文件
    batch_id = result["data"]["batch_id"]
    urls = result["data"]["file_urls"]
    success_count = 0
    
    for idx, (url, file_path) in enumerate(zip(urls, batch_files)):
        with open(file_path, 'rb') as f:
            res = requests.put(url, data=f)
            if res.status_code in [200, 201]:
                success_count += 1
            else:
                print(f"失败文件：{os.path.basename(file_path)}，状态码：{res.status_code}")
    
    print(f"第二批次完成 | 成功：{success_count}/{len(batch_files)} | 批次ID：{batch_id}")
#这个批次id一会会用到
 
except Exception as e:
    print(f"发生异常：{str(e)}")