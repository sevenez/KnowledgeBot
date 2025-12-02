"""
文档切片模块
负责将文档切分为适合向量化的小片段
"""
import os
import re
import json
from typing import List, Dict, Any, Tuple, Optional
import warnings

class DocumentChunker:
    """文档切片器，负责将文档切分为适合向量化的小片段"""
    
    def __init__(self, 
                 chunk_size: int = 500, 
                 chunk_overlap: int = 50,
                 min_chunk_size: int = 50):
        """
        初始化文档切片器
        
        Args:
            chunk_size: 切片大小（字符数）
            chunk_overlap: 切片重叠大小（字符数）
            min_chunk_size: 最小切片大小（字符数）
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def chunk_document(self, 
                      content: str, 
                      file_path: str, 
                      file_id: int) -> List[Dict[str, Any]]:
        """
        将文档切分为小片段
        
        Args:
            content: 文档内容
            file_path: 文件路径
            file_id: 文件ID
            
        Returns:
            切片列表，每个切片包含文本内容和元数据
        """
        # 清理文档内容
        content = self._clean_document(content)
        
        # 根据文件类型选择切片方法
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in ['.md', '.markdown']:
            # Markdown文档，尝试结构化切片
            return self._chunk_text_document(content, file_path, file_id, prefer_structure=True)
        elif file_ext in ['.txt', '.text']:
            # 纯文本文档，尝试段落切片
            return self._chunk_text_document(content, file_path, file_id, prefer_structure=False)
        else:
            # 其他类型文档，使用固定长度切片
            return self._chunk_by_fixed_length(content, file_path, file_id)
    
    def _clean_document(self, content: str) -> str:
        """
        清理文档内容
        
        Args:
            content: 原始文档内容
            
        Returns:
            清理后的文档内容
        """
        # 替换多个空白字符为单个空格
        content = re.sub(r'\s+', ' ', content)
        
        # 替换多个换行符为两个换行符
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 移除特殊字符 (使用更简单的正则表达式，避免使用\p{P}和\p{S})
        # 只移除极少数特殊控制字符，保留绝大部分标点符号
        # 移除控制字符但保留所有可见字符和标点符号
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
        
        return content.strip()
    
    def _create_chunk(self, 
                     text: str, 
                     file_path: str, 
                     file_id: int, 
                     chunk_id: int, 
                     chunk_type: str = "text") -> Dict[str, Any]:
        """
        创建文档切片
        
        Args:
            text: 切片文本内容
            file_path: 文件路径
            file_id: 文件ID
            chunk_id: 切片ID
            chunk_type: 切片类型
            
        Returns:
            包含文本内容和元数据的切片字典
        """
        return {
            "content": text,
            "metadata": {
                "source": os.path.basename(file_path),
                "file_path": file_path,
                "file_id": file_id,
                "chunk_id": chunk_id,
                "chunk_type": chunk_type
            }
        }
    
    def _process_text_unit(self, 
                          text_unit: str, 
                          file_path: str, 
                          file_id: int, 
                          chunk_id: int, 
                          chunk_type: str) -> List[Dict[str, Any]]:
        """
        处理文本单元（段落或句子）
        
        Args:
            text_unit: 文本单元内容
            file_path: 文件路径
            file_id: 文件ID
            chunk_id: 起始切片ID
            chunk_type: 切片类型
            
        Returns:
            切片列表
        """
        chunks = []
        
        # 如果文本单元长度超过chunk_size，则进行分割
        if len(text_unit) > self.chunk_size:
            # 分割长文本单元
            split_chunks = self._split_long_text(text_unit)
            for i, split_text in enumerate(split_chunks):
                chunks.append(self._create_chunk(
                    split_text, 
                    file_path, 
                    file_id, 
                    chunk_id + i, 
                    f"{chunk_type}_split"
                ))
        else:
            # 文本单元长度合适，直接创建切片
            chunks.append(self._create_chunk(
                text_unit, 
                file_path, 
                file_id, 
                chunk_id, 
                chunk_type
            ))
        
        return chunks
    
    def _split_long_text(self, text: str) -> List[str]:
        """
        将长文本按固定长度切分
        
        Args:
            text: 长文本
            
        Returns:
            切分后的文本列表
        """
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            # 计算当前切片的结束位置
            end = start + self.chunk_size
            
            if end >= text_len:
                # 最后一个切片
                chunks.append(text[start:])
                break
            
            # 尝试在单词边界处切分
            while end > start + self.min_chunk_size:
                if text[end] in [' ', '\n', '.', '!', '?', ',', ';', ':', '，', '。', '！', '？', '；', '：']:
                    break
                end -= 1
            
            # 如果没有找到合适的边界，就在原位置切分
            if end <= start + self.min_chunk_size:
                end = start + self.chunk_size
            
            # 添加当前切片
            chunks.append(text[start:end+1])
            
            # 更新下一个切片的起始位置，考虑重叠
            start = end + 1 - self.chunk_overlap
        
        return chunks
    
    def _chunk_text_document(self, 
                            content: str, 
                            file_path: str, 
                            file_id: int,
                            prefer_structure: bool = True) -> List[Dict[str, Any]]:
        """
        对文本文档进行切片
        
        Args:
            content: 文档内容
            file_path: 文件路径
            file_id: 文件ID
            prefer_structure: 是否优先使用结构化切片
            
        Returns:
            切片列表，每个切片包含文本内容和元数据
        """
        # 检查文档是否有明显的结构（标题、章节等）
        has_structure = self._has_markdown_structure(content)
        
        if has_structure and prefer_structure:
            # 基于结构切片（章节级）
            return self._chunk_by_structure(content, file_path, file_id)
        elif self._has_paragraphs(content):
            # 基于结构切片（段落级）
            return self._chunk_by_paragraph(content, file_path, file_id)
        else:
            # 尝试语义切片
            try:
                return self._chunk_by_semantic(content, file_path, file_id)
            except Exception as e:
                # 如果语义切片失败，回退到固定长度切片
                print(f"语义切片失败，回退到固定长度切片: {e}")
                return self._chunk_by_fixed_length(content, file_path, file_id)
    
    def _has_markdown_structure(self, content: str) -> bool:
        """
        检查文档是否有Markdown结构
        
        Args:
            content: 文档内容
            
        Returns:
            是否有Markdown结构
        """
        # 检查是否有Markdown标题
        header_pattern = r'^#{1,6}\s+.+$'
        headers = re.findall(header_pattern, content, re.MULTILINE)
        
        # 如果有多个标题，认为有结构
        return len(headers) >= 2
    
    def _has_paragraphs(self, content: str) -> bool:
        """
        检查文档是否有明显的段落结构
        
        Args:
            content: 文档内容
            
        Returns:
            是否有段落结构
        """
        # 按空行分割，检查是否有多个段落
        paragraphs = re.split(r'\n\s*\n', content)
        return len(paragraphs) >= 2
    
    def _chunk_by_structure(self, 
                           content: str, 
                           file_path: str, 
                           file_id: int) -> List[Dict[str, Any]]:
        """
        基于文档结构（标题、章节）进行切片
        
        Args:
            content: 文档内容
            file_path: 文件路径
            file_id: 文件ID
            
        Returns:
            切片列表
        """
        chunks = []
        chunk_id = 0
        
        # 按标题分割文档
        header_pattern = r'^(#{1,6}\s+.+)$'
        sections = re.split(header_pattern, content, flags=re.MULTILINE)
        
        current_header = "开始"
        current_content = ""
        
        for i, section in enumerate(sections):
            if i % 2 == 0:  # 内容部分
                current_content = section.strip()
                if current_content and current_header:
                    # 处理当前章节
                    section_text = f"{current_header}\n\n{current_content}"
                    section_chunks = self._process_text_unit(
                        section_text, 
                        file_path, 
                        file_id, 
                        chunk_id, 
                        "section"
                    )
                    chunks.extend(section_chunks)
                    chunk_id += len(section_chunks)
            else:  # 标题部分
                current_header = section.strip()
        
        # 处理最后一个章节
        if current_content and current_header:
            section_text = f"{current_header}\n\n{current_content}"
            section_chunks = self._process_text_unit(
                section_text, 
                file_path, 
                file_id, 
                chunk_id, 
                "section"
            )
            chunks.extend(section_chunks)
        
        return chunks
    
    def _chunk_by_paragraph(self, 
                           content: str, 
                           file_path: str, 
                           file_id: int) -> List[Dict[str, Any]]:
        """
        基于段落进行切片
        
        Args:
            content: 文档内容
            file_path: 文件路径
            file_id: 文件ID
            
        Returns:
            切片列表
        """
        chunks = []
        chunk_id = 0
        
        # 按空行分割段落
        paragraphs = re.split(r'\n\s*\n', content)
        
        # 处理每个段落
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # 处理段落
            paragraph_chunks = self._process_text_unit(
                paragraph, 
                file_path, 
                file_id, 
                chunk_id, 
                "paragraph"
            )
            chunks.extend(paragraph_chunks)
            chunk_id += len(paragraph_chunks)
        
        return chunks
    
    def _chunk_by_semantic(self, 
                          content: str, 
                          file_path: str, 
                          file_id: int) -> List[Dict[str, Any]]:
        """
        基于语义（句子）进行切片
        
        Args:
            content: 文档内容
            file_path: 文件路径
            file_id: 文件ID
            
        Returns:
            切片列表
        """
        chunks = []
        chunk_id = 0
        
        try:
            # 使用正则表达式分割句子
            sentence_pattern = r'([.!?。！？]+[\s\n]+)'
            sentences_with_separators = re.split(sentence_pattern, content)
            
            # 重新组合句子和分隔符
            sentences = []
            for i in range(0, len(sentences_with_separators), 2):
                sentence = sentences_with_separators[i]
                separator = sentences_with_separators[i+1] if i+1 < len(sentences_with_separators) else ""
                sentences.append(sentence + separator)
            
            # 合并短句子
            current_chunk = ""
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # 如果当前块加上新句子不超过chunk_size，则添加到当前块
                if len(current_chunk) + len(sentence) <= self.chunk_size:
                    current_chunk += " " + sentence if current_chunk else sentence
                else:
                    # 当前块已满，创建新切片
                    if current_chunk:
                        chunk_chunks = self._process_text_unit(
                            current_chunk, 
                            file_path, 
                            file_id, 
                            chunk_id, 
                            "semantic"
                        )
                        chunks.extend(chunk_chunks)
                        chunk_id += len(chunk_chunks)
                    
                    # 开始新块
                    current_chunk = sentence
            
            # 处理最后一个块
            if current_chunk:
                chunk_chunks = self._process_text_unit(
                    current_chunk, 
                    file_path, 
                    file_id, 
                    chunk_id, 
                    "semantic"
                )
                chunks.extend(chunk_chunks)
            
        except Exception as e:
            print(f"语义切片过程中出错: {e}")
            # 如果解析失败，将整个内容作为一个切片
            chunks.append(self._create_chunk(
                content, 
                file_path, 
                file_id, 
                0, 
                "full_text"
            ))
        
        return chunks
    
    def _chunk_by_fixed_length(self, 
                              content: str, 
                              file_path: str, 
                              file_id: int) -> List[Dict[str, Any]]:
        """
        基于固定长度进行切片
        
        Args:
            content: 文档内容
            file_path: 文件路径
            file_id: 文件ID
            
        Returns:
            切片列表
        """
        chunks = []
        
        # 直接使用_split_long_text方法切分
        split_chunks = self._split_long_text(content)
        
        # 创建切片
        for i, chunk_text in enumerate(split_chunks):
            chunks.append(self._create_chunk(
                chunk_text, 
                file_path, 
                file_id, 
                i, 
                "fixed_length"
            ))
        
        return chunks


# 模块标识
if __name__ == "__main__":
    print("文档切片模块")