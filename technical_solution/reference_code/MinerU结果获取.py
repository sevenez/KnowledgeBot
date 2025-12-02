import requests
import zipfile
import os
import shutil
from urllib.parse import urlparse
import re
from os import environ
 
output_dir = "./result"  # 指定输出目录
images_dir = os.path.join(output_dir, "images")  # 图片输出目录
original_files_dir = "./originalFiles"  # 原始文件目录
os.makedirs(output_dir, exist_ok=True)  # 自动创建目录
os.makedirs(images_dir, exist_ok=True)  # 自动创建图片目录
os.makedirs(original_files_dir, exist_ok=True)  # 自动创建原始文件目录
idx='3985c016-4dd6-4fc0-ae56-cbea96c5719d' #之前代码的批次id
 
# 原始API请求
url = 'https://mineru.net/api/v4/extract-results/batch/'+idx
# 从环境变量获取API密钥
api_key = environ.get('MINERU_API_KEY')
if not api_key:
    print("错误：未设置MINERU_API_KEY环境变量")
    exit(1)

headers = {
    'Content-Type': 'application/json',
    "Authorization": f"Bearer {api_key}"  # 使用环境变量中的API密钥
}
 
response = requests.get(url, headers=headers)
batch_data = response.json()["data"]
 
# 正确访问数据路径
data_list = batch_data['extract_result']  # 从extract_result获取数据
 
for item in data_list:
    if item.get('state') == 'done' and 'full_zip_url' in item:
        zip_url = item['full_zip_url']
        original_name = item['file_name']
        
        # 生成最终路径
        base_name = os.path.splitext(original_name)[0]
        final_filename = f"{base_name}.md"
        output_path = os.path.join(output_dir, final_filename)
        
        try:
            # 创建临时目录
            temp_dir = os.path.join(output_dir, f"temp_{item['data_id']}")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 下载ZIP文件
            zip_response = requests.get(zip_url, stream=True)
            zip_response.raise_for_status()
            
            # 保存临时ZIP
            zip_name = os.path.basename(urlparse(zip_url).path)
            zip_path = os.path.join(temp_dir, zip_name)
            with open(zip_path, 'wb') as f:
                for chunk in zip_response.iter_content(1024 * 1024):  # 1MB chunks
                    f.write(chunk)
            
            # 解压并处理文件
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 搜索full.md文件
                target_file = None
                image_files = []
                
                # 遍历所有文件，找出full.md和图片文件
                for file_info in zip_ref.infolist():
                    filename = file_info.filename
                    if os.path.basename(filename) == 'full.md':
                        target_file = file_info
                    # 检查是否为图片文件（在images目录下）
                    if 'images/' in filename and (filename.lower().endswith('.png') or 
                                                 filename.lower().endswith('.jpg') or 
                                                 filename.lower().endswith('.jpeg') or 
                                                 filename.lower().endswith('.gif')):
                        image_files.append(file_info)
                
                # 处理full.md文件
                if target_file:
                    # 解压到临时目录
                    zip_ref.extract(target_file, temp_dir)
                    
                    # 构建完整路径
                    extracted_path = os.path.join(temp_dir, target_file.filename)
                    
                    # 移动并重命名
                    shutil.move(extracted_path, output_path)
                    print(f"成功处理：{original_name} -> {output_path}")
                else:
                    print(f"警告：{zip_name} 中未找到full.md文件")
                
                # 处理图片文件
                image_count = 0
                for img_file in image_files:
                    # 提取图片文件名，保持原始名称
                    img_filename = os.path.basename(img_file.filename)
                    # 解压图片到临时目录
                    zip_ref.extract(img_file, temp_dir)
                    # 构建图片源路径和目标路径
                    img_src_path = os.path.join(temp_dir, img_file.filename)
                    img_dst_path = os.path.join(images_dir, img_filename)
                    # 移动图片到images目录
                    shutil.move(img_src_path, img_dst_path)
                    image_count += 1
                
                if image_count > 0:
                    print(f"已保存 {image_count} 张图片到 {images_dir}")
            
        except requests.exceptions.RequestException as e:
            print(f"下载失败：{original_name} | 错误：{str(e)}")
        except zipfile.BadZipFile:
            print(f"损坏的ZIP文件：{original_name}")
        except Exception as e:
            print(f"处理异常：{original_name} | 错误类型：{type(e).__name__} | 详情：{str(e)}")
        finally:
            # 不再删除临时文件，而是移动到originalFiles目录
            if os.path.exists(temp_dir):
                # 删除临时目录中的images子目录（如果存在）
                images_subdir = os.path.join(temp_dir, "images")
                if os.path.exists(images_subdir):
                    shutil.rmtree(images_subdir)
                    print(f"已删除临时目录中的images子文件夹")
                
                # 创建目标目录（如果不存在）
                temp_dir_name = os.path.basename(temp_dir)
                target_dir = os.path.join(original_files_dir, temp_dir_name)
                
                # 如果目标目录已存在，先删除它
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir)
                
                # 移动临时目录到originalFiles目录
                shutil.move(temp_dir, original_files_dir)
                print(f"已将临时文件夹 {temp_dir_name} 移动到 {original_files_dir}")
            
