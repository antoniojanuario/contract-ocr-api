# 🚀 Deploy Guide - Contract OCR API

## 📋 Pré-requisitos

1. **Conta no GitHub** (gratuita)
2. **Conta no Render.com** (gratuita)
3. **Repositório Git** com o código

## 🔧 Passo a Passo para Deploy

### 1. Preparar Repositório

```bash
# Adicionar arquivos ao Git
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### 2. Deploy no Render.com

1. **Acesse:** https://render.com
2. **Faça login** com GitHub
3. **Clique em "New +"** → **"Web Service"**
4. **Conecte seu repositório** GitHub
5. **Configure:**
   - **Name:** `contract-ocr-api`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements-render.txt`
   - **Start Command:** `chmod +x start_render.sh && ./start_render.sh`
   - **Plan:** `Free`

### 3. Configurar Banco de Dados

1. **No dashboard Render**, clique **"New +"** → **"PostgreSQL"**
2. **Configure:**
   - **Name:** `contract-ocr-db`
   - **Database:** `contract_ocr`
   - **User:** `contract_ocr_user`
   - **Plan:** `Free`

3. **Conectar ao Web Service:**
   - Vá em **Environment Variables**
   - Adicione: `DATABASE_URL` = `[PostgreSQL Connection String]`

### 4. Variáveis de Ambiente

Adicione no Render:

```
ENVIRONMENT=render
DEBUG=false
REQUIRE_API_KEY=false
MAX_FILE_SIZE=25000000
WORKER_COUNT=1
LOG_LEVEL=INFO
ALLOWED_ORIGINS=*
```

## 🌐 URLs Após Deploy

- **API Base:** `https://contract-ocr-api.onrender.com`
- **Swagger UI:** `https://contract-ocr-api.onrender.com/docs`
- **Health Check:** `https://contract-ocr-api.onrender.com/health`

## 🤖 Integração com Copilot Studio

### Endpoints para Copilot Studio:

#### 1. Upload de Documento
```
POST https://contract-ocr-api.onrender.com/api/v1/documents/upload
Content-Type: multipart/form-data
Body: file=@documento.pdf
```

#### 2. Verificar Status
```
GET https://contract-ocr-api.onrender.com/api/v1/documents/{document_id}/status
```

#### 3. Obter Texto OCR
```
GET https://contract-ocr-api.onrender.com/api/v1/documents/{document_id}/results
```

### Fluxo no Copilot Studio:

1. **Upload:** Enviar PDF para `/upload`
2. **Aguardar:** Verificar status até `completed`
3. **Extrair:** Obter texto de `/results`
4. **Processar:** Usar `pages[].raw_text` ou `pages[].normalized_text`

### Exemplo de Resposta:

```json
{
  "pages": [
    {
      "page_number": 1,
      "raw_text": "CONTRATO DE MÚTUO BANCÁRIO...",
      "normalized_text": "CONTRATO DE MÚTUO BANCÁRIO...",
      "text_blocks": [...]
    }
  ],
  "legal_terms": ["contrato", "acordo", "partes"],
  "metadata": {
    "page_count": 15,
    "processing_time": 30.5,
    "ocr_confidence": 0.95
  }
}
```

## 🔧 Configuração no Copilot Studio

### 1. Criar Connector Personalizado

1. **Power Platform** → **Custom Connectors**
2. **Import from OpenAPI**
3. **URL:** `https://contract-ocr-api.onrender.com/api/v1/openapi.json`

### 2. Ações Disponíveis

- **UploadDocument:** Upload de PDF
- **GetStatus:** Verificar processamento
- **GetResults:** Obter texto extraído

### 3. Fluxo Recomendado

```
1. User uploads PDF
2. Call UploadDocument → get document_id
3. Loop: Call GetStatus until status = "completed"
4. Call GetResults → extract text
5. Process extracted text in conversation
```

## 📊 Limites do Plano Gratuito

- **Render:** 750 horas/mês, 512MB RAM
- **PostgreSQL:** 1GB storage, 97 conexões
- **Arquivos:** 25MB máximo por PDF
- **Processamento:** ~3 minutos timeout

## 🔧 OCR Engine Otimizado

Para garantir compatibilidade com o plano gratuito do Render, a API usa:
- **pdfplumber** ou **pypdf** para extração de texto
- Sem dependências de compilação C++
- Processamento rápido e eficiente
- Funciona com PDFs que contêm texto nativo

## 🛠️ Troubleshooting

### Problema: Deploy falha
**Solução:** Verificar logs no Render dashboard

### Problema: Worker não inicia
**Solução:** Verificar variáveis de ambiente

### Problema: OCR lento
**Solução:** Reduzir tamanho do PDF (<10MB)

### Problema: Timeout
**Solução:** Aumentar timeout ou dividir documento

## 📞 Suporte

- **Logs:** Render Dashboard → Service → Logs
- **Health:** `GET /health`
- **Metrics:** `GET /metrics`

---

**🎉 Após o deploy, sua API estará disponível 24/7 para integração com Copilot Studio!**