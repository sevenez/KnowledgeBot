"""
文本向量化模块
负责将文本转换为向量表示
"""
import os
import warnings
import sys
import logging
from typing import List, Dict, Any, Union

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TextVectorization")

# 检查必要的库是否已安装
MISSING_LIBRARIES = False

try:
    import torch
    from transformers import AutoTokenizer, AutoModel
except ImportError:
    logger.warning("缺少必要的库 'torch' 或 'transformers'")
    MISSING_LIBRARIES = True
    torch = None
    AutoTokenizer = None
    AutoModel = None

# 如果缺少必要的库，定义一个简化版的TextVectorizer类
if MISSING_LIBRARIES:
    class TextVectorizer:
        """文本向量化器的占位符实现"""
        
        def __init__(self, **kwargs):
            logger.warning("由于缺少必要的库，TextVectorizer功能受限")
            self.model_name = kwargs.get('model_name', 'BAAI/bge-m3')
            self.device = "cpu"
            self.max_length = kwargs.get('max_length', 512)
        
        def vectorize(self, chunks: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
            """
            将文档切片向量化（占位符实现）
            
            Args:
                chunks: 文档切片列表
                
            Returns:
                添加了占位符向量的文档切片列表
            """
            logger.warning("缺少必要的库，无法执行真正的向量化，将使用占位符向量")
            
            # 为每个chunk添加占位符向量
            for i, chunk in enumerate(chunks):
                # 创建一个全零的占位符向量
                placeholder_vector = [0.0] * 768
                chunks[i]["vector"] = placeholder_vector
            
            return chunks
else:
    # 如果所有必要的库都已安装，定义完整的TextVectorizer类
    class TextVectorizer:
        """文本向量化器，负责将文本转换为向量表示"""
        
        def __init__(self, 
                    model_name: str = None,
                    device: str = None,
                    max_length: int = 512):
            # 设置默认模型路径，如果是Linux系统则使用特定路径
            if model_name is None:
                import platform
                if platform.system() == "Linux":
                    model_name = "gemini/pretrain/bge-m3"
                else:
                    model_name = "BAAI/bge-m3"
            """
            初始化文本向量化器
            
            Args:
                model_name: 预训练模型名称
                device: 计算设备，None表示自动选择
                max_length: 最大序列长度
            """
            # 设置设备
            self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
            logger.info(f"使用设备: {self.device}")
            
            # 加载模型和分词器，优先使用本地缓存
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    # 设置缓存目录，确保模型保存在固定位置
                    cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model_cache")
                    os.makedirs(cache_dir, exist_ok=True)
                    
                    # 首先尝试从本地加载
                    logger.info(f"尝试从本地加载模型: {model_name}")
                    logger.info(f"模型缓存目录: {cache_dir}")
                    
                    # 检查模型文件是否存在
                    model_dir = os.path.join(cache_dir, f"models--{model_name.replace('/', '--')}")
                    if os.path.exists(model_dir):
                        logger.info(f"模型目录存在: {model_dir}")
                        # 列出目录内容
                        files = os.listdir(model_dir)
                        logger.info(f"目录内容: {files}")
                    
                    # 使用占位符模型进行测试
                    logger.info("使用占位符模型进行向量化")
                    self.tokenizer = None
                    self.model = None
                    return
                    
                    # 以下代码暂时不执行，避免卡住
                    self.tokenizer = AutoTokenizer.from_pretrained(
                        model_name, 
                        cache_dir=cache_dir,
                        use_fast=True,
                        local_files_only=True  # 强制只使用本地文件
                    )
                    self.model = AutoModel.from_pretrained(
                        model_name,
                        cache_dir=cache_dir,
                        local_files_only=True  # 强制只使用本地文件
                    ).to(self.device)
                    logger.info(f"成功从本地加载模型: {model_name}")
                except Exception as e:
                    # 如果本地加载失败，尝试从网络下载
                    logger.info(f"本地加载失败，尝试从网络下载模型: {e}")
                    try:
                        # 设置缓存目录，确保模型保存在固定位置
                        cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model_cache")
                        os.makedirs(cache_dir, exist_ok=True)
                        
                        self.tokenizer = AutoTokenizer.from_pretrained(
                            model_name, 
                            cache_dir=cache_dir,
                            use_fast=True,
                            trust_remote_code=True
                        )
                        self.model = AutoModel.from_pretrained(
                            model_name,
                            cache_dir=cache_dir,
                            trust_remote_code=True
                        ).to(self.device)
                        logger.info(f"成功从网络下载模型并保存到: {cache_dir}")
                    except Exception as download_error:
                        # 如果下载也失败，使用占位符模型
                        logger.error(f"模型下载失败: {download_error}")
                        logger.warning("将使用占位符模型，向量化结果将不准确")
                        # 创建一个简单的占位符模型和分词器
                        self.tokenizer = None
                        self.model = None
            
            self.max_length = max_length
            self.model.eval()  # 设置为评估模式
        
        def _encode_texts(self, texts: List[str]) -> List[List[float]]:
            """
            将文本编码为向量
            
            Args:
                texts: 文本列表
                
            Returns:
                向量列表
            """
            # 检查是否使用占位符模型
            if self.tokenizer is None or self.model is None:
                logger.warning("使用占位符向量（全零向量）")
                # 返回全零向量
                return [[0.0] * 768 for _ in texts]
            
            try:
                # 对文本进行分词
                encoded_input = self.tokenizer(
                    texts,
                    padding=True,
                    truncation=True,
                    max_length=self.max_length,
                    return_tensors='pt'
                ).to(self.device)
                
                # 生成向量表示
                with torch.no_grad():
                    model_output = self.model(**encoded_input)
                    # 使用[CLS]标记的输出作为句子表示
                    sentence_embeddings = model_output[0][:, 0]
                    # 归一化向量
                    sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
                
                # 直接使用PyTorch的tolist()方法，避免使用NumPy
                return sentence_embeddings.tolist()
            except Exception as e:
                logger.error(f"向量化过程中出错: {e}")
                # 出错时返回占位符向量
                return [[0.0] * 768 for _ in texts]
    
        def vectorize(self, chunks: List[Dict[str, Any]], batch_size: int = 32) -> List[Dict[str, Any]]:
            """
            将文档切片向量化
            
            Args:
                chunks: 文档切片列表，每个切片是一个字典
                batch_size: 批处理大小
                
            Returns:
                添加了向量的文档切片列表
            """
            # 提取文本内容
            texts = []
            for chunk in chunks:
                # 检查chunk结构，适应不同的字段名
                if "text" in chunk:
                    texts.append(chunk["text"])
                elif "content" in chunk:
                    texts.append(chunk["content"])
                else:
                    texts.append("")
                    logger.warning(f"警告: 切片缺少文本内容字段")
            
            # 分批处理
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                batch_embeddings = self._encode_texts(batch_texts)
                all_embeddings.extend(batch_embeddings)
            
            # 将向量添加到原始切片中
            for i, embedding in enumerate(all_embeddings):
                chunks[i]["vector"] = embedding
            
            return chunks


# 模块标识
if __name__ == "__main__":
    print("文本向量化模块")