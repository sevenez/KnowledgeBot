# 文档解析服务 cURL 测试命令

## 1. 健康检查

```bash
curl -X GET "http://localhost:8271/health"
```

## 2. 单独文档解析

```bash
curl -X POST "http://localhost:8271/parse-document" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "knlgdocs/公司总部/pdf/sample.pdf",
    "timeout": 300
  }'
```

## 3. 批量文档处理

```bash
curl -X POST "http://localhost:8271/batch-process" \
  -H "Content-Type: application/json" \
  -d '{
    "file_paths": [
      "knlgdocs/公司总部/pdf/sample1.pdf",
      "knlgdocs/公司总部/docx/sample2.docx"
    ],
    "klg_base_code": "KB001",
    "timeout": 600
  }'
```

## 4. 查询批量处理状态

```bash
curl -X GET "http://localhost:8271/batch-status/DPS_1737510297_123456"
```

## 5. 删除文档

```bash
curl -X DELETE "http://localhost:8271/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "file_paths": [
      "knlgdocs/公司总部/pdf/sample.pdf"
    ]
  }'
```

## 测试说明

1. **文件路径**: 请将示例中的文件路径替换为实际存在的文件路径
2. **服务地址**: 确保FastAPI服务在 `localhost:8271` 上运行
3. **文件格式**: 支持 `.pdf`, `.doc`, `.docx`, `.ppt`, `.pptx` 格式
4. **状态码**: 
   - 200: 成功
   - 400: 请求参数错误
   - 404: 文件不存在
   - 500: 服务器内部错误

## 状态更新说明

修复后的服务会正确更新以下状态：

1. **is_parsed 字段**: 文档预处理完成后设置为 `TRUE`
2. **status 字段**: 
   - '0': 未解析
   - '1': 已解析
   - '2': 已向量化
3. **parsed_at 字段**: 记录解析完成时间
4. **updated_at 字段**: 记录最后更新时间

## 问题排查

如果状态仍未更新，请检查：

1. 数据库连接是否正常
2. 文件路径是否正确
3. API密钥是否有效
4. 服务日志中的错误信息