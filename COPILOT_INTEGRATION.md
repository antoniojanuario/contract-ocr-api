# 🤖 Integração com Microsoft Copilot Studio

## 🎯 Endpoints Otimizados para Copilot Studio

### Base URL (após deploy)
```
https://contract-ocr-api.onrender.com
```

## 📋 Fluxo Completo de Integração

### 1. Upload e Processamento
```http
POST /api/v1/copilot/extract-text
Content-Type: multipart/form-data

file: [PDF_FILE]
```

**Resposta:**
```json
{
  "success": true,
  "document_id": "uuid-here",
  "status": "queued",
  "message": "Document uploaded and queued for OCR processing",
  "estimated_processing_time": "30-180 seconds",
  "status_check_url": "/api/v1/copilot/status/uuid-here",
  "results_url": "/api/v1/copilot/text/uuid-here"
}
```

### 2. Verificar Status
```http
GET /api/v1/copilot/status/{document_id}
```

**Resposta:**
```json
{
  "document_id": "uuid-here",
  "status": "completed",
  "progress": 100,
  "is_complete": true,
  "is_failed": false,
  "estimated_remaining_seconds": 0,
  "page_count": 15,
  "processing_time": 45.2
}
```

### 3. Obter Texto Extraído
```http
GET /api/v1/copilot/text/{document_id}?format=combined
```

**Resposta:**
```json
{
  "document_id": "uuid-here",
  "text": "--- Página 1 ---\nCONTRATO DE MÚTUO BANCÁRIO\n...",
  "page_count": 15,
  "format": "combined",
  "legal_terms": ["contrato", "acordo", "partes"],
  "metadata": {
    "filename": "contrato.pdf",
    "processing_time": 45.2,
    "ocr_confidence": 0.95
  }
}
```

## 🔧 Configuração no Copilot Studio

### 1. Criar Custom Connector

1. **Power Platform Admin Center**
2. **Custom Connectors** → **New Custom Connector**
3. **Import from OpenAPI**
4. **URL:** `https://contract-ocr-api.onrender.com/api/v1/openapi.json`

### 2. Ações Disponíveis

#### ExtractText
- **Método:** POST
- **URL:** `/api/v1/copilot/extract-text`
- **Input:** File (PDF)
- **Output:** document_id, status, URLs

#### GetStatus
- **Método:** GET
- **URL:** `/api/v1/copilot/status/{document_id}`
- **Input:** document_id
- **Output:** status, progress, is_complete

#### GetText
- **Método:** GET
- **URL:** `/api/v1/copilot/text/{document_id}`
- **Input:** document_id, format
- **Output:** extracted text, legal_terms

### 3. Fluxo no Copilot Studio

```yaml
Trigger: User uploads document
↓
Action: ExtractText
  Input: uploaded_file
  Output: document_id
↓
Loop: GetStatus
  Condition: is_complete = false
  Wait: 10 seconds
  Max iterations: 30
↓
Action: GetText
  Input: document_id, format="combined"
  Output: extracted_text
↓
Response: "Texto extraído: {extracted_text}"
```

## 📝 Exemplo de Implementação

### Power Automate Flow

```json
{
  "definition": {
    "triggers": {
      "manual": {
        "type": "Request",
        "inputs": {
          "schema": {
            "type": "object",
            "properties": {
              "file": {"type": "string", "format": "binary"}
            }
          }
        }
      }
    },
    "actions": {
      "ExtractText": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "https://contract-ocr-api.onrender.com/api/v1/copilot/extract-text",
          "body": "@triggerBody()",
          "headers": {
            "Content-Type": "multipart/form-data"
          }
        }
      },
      "WaitForCompletion": {
        "type": "Until",
        "expression": "@equals(body('GetStatus')['is_complete'], true)",
        "actions": {
          "GetStatus": {
            "type": "Http",
            "inputs": {
              "method": "GET",
              "uri": "https://contract-ocr-api.onrender.com/api/v1/copilot/status/@{body('ExtractText')['document_id']}"
            }
          },
          "Delay": {
            "type": "Wait",
            "inputs": {
              "interval": {
                "count": 10,
                "unit": "Second"
              }
            }
          }
        }
      },
      "GetText": {
        "type": "Http",
        "inputs": {
          "method": "GET",
          "uri": "https://contract-ocr-api.onrender.com/api/v1/copilot/text/@{body('ExtractText')['document_id']}?format=combined"
        }
      }
    }
  }
}
```

### Copilot Studio Topic

```yaml
Name: "Extrair Texto de PDF"

Trigger Phrases:
- "extrair texto do pdf"
- "fazer ocr do documento"
- "ler documento"

Flow:
1. Message: "Por favor, envie o arquivo PDF que deseja processar."
2. Wait for user input (file)
3. Call ExtractText action with uploaded file
4. Message: "Processando documento... Isso pode levar até 3 minutos."
5. Loop GetStatus until complete
6. Call GetText to get extracted content
7. Message: "Texto extraído com sucesso! Aqui está o conteúdo: {extracted_text}"
8. If legal_terms found: "Termos legais identificados: {legal_terms}"
```

## 🚀 Formatos de Resposta

### Format: "combined" (Recomendado para Copilot)
- Texto completo em string única
- Páginas separadas por "--- Página X ---"
- Ideal para processamento em conversas

### Format: "pages"
- Array com texto de cada página
- Útil para análise página por página
- Inclui confidence score por página

### Format: "blocks"
- Blocos de texto detalhados
- Inclui coordenadas e formatação
- Para análise avançada de layout

## ⚡ Otimizações para Copilot Studio

### Timeouts Recomendados
- **Upload:** 30 segundos
- **Status Check:** 5 segundos
- **Text Retrieval:** 10 segundos
- **Total Flow:** 5 minutos

### Tratamento de Erros
```yaml
If status = "failed":
  Message: "Erro no processamento: {error_message}"
  Suggest: "Tente com um PDF menor ou de melhor qualidade"

If timeout:
  Message: "Processamento demorou mais que esperado"
  Action: Check status manually
```

### Limites do Plano Gratuito
- **Arquivo:** Máximo 25MB
- **Páginas:** Até 50 páginas
- **Timeout:** 3 minutos
- **Concurrent:** 1 processamento simultâneo

## 🔍 Monitoramento

### Health Check
```http
GET /api/v1/copilot/health
```

### Logs e Debug
- **Render Dashboard:** Logs em tempo real
- **Status Endpoint:** Progresso detalhado
- **Error Messages:** Descrições específicas

---

**🎉 Com essa integração, seu Copilot Studio poderá extrair texto de qualquer PDF automaticamente!**