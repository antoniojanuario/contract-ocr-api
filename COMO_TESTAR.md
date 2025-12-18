# 🧪 Como Testar a API - Guia Rápido

## ✅ Problema Resolvido!

O problema da página em branco no Swagger UI foi causado pelos **headers de segurança muito restritivos** (Content Security Policy). Isso foi corrigido!

---

## 🚀 Passo a Passo para Testar

### 1. **Certifique-se que o servidor está rodando**

Se o servidor não estiver rodando, inicie com:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Você verá algo como:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using StatReload
INFO:     Started server process [xxxxx]
INFO:     Application startup complete.
```

### 2. **Acesse a Documentação Swagger UI**

Abra seu navegador e acesse:

**http://127.0.0.1:8000/docs**

Agora você deve ver a interface completa do Swagger UI com todos os endpoints!

### 3. **Endpoints Disponíveis para Testar**

#### 📚 **Documentação:**
- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc
- **OpenAPI JSON:** http://127.0.0.1:8000/api/v1/openapi.json

#### 🏥 **Monitoramento:**
- **Health Check:** http://127.0.0.1:8000/health
- **Métricas:** http://127.0.0.1:8000/metrics

#### 📄 **Documentos (API):**
- **Upload:** `POST /api/v1/documents/upload`
- **Status:** `GET /api/v1/documents/{document_id}/status`
- **Resultados:** `GET /api/v1/documents/{document_id}/results`
- **Histórico:** `GET /api/v1/documents/history`

#### 🔗 **Integração:**
- **Exemplos Copilot Studio:** `GET /api/v1/integration/copilot-studio/examples`
- **Guia de Integração:** `GET /api/v1/integration/integration-guide`

---

## 🧪 Testes Automatizados

### Teste Rápido das Configurações
```bash
python test_deployment.py
```

### Teste dos Endpoints
```bash
python test_api_endpoints.py
```

### Debug dos Endpoints
```bash
python debug_endpoints.py
```

### Testes de Integração
```bash
python -m pytest tests/test_deployment_integration.py -v
```

---

## 🌐 Testando no Navegador

### 1. **Health Check**
Acesse: http://127.0.0.1:8000/health

Você verá algo como:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "local",
  "metrics": {
    "cpu": {"percent": 15.2},
    "memory": {"percent": 45.8},
    "disk": {"percent": 38.1}
  }
}
```

### 2. **Swagger UI**
Acesse: http://127.0.0.1:8000/docs

Você verá:
- ✅ Lista completa de endpoints
- ✅ Documentação de cada endpoint
- ✅ Botão "Try it out" para testar
- ✅ Exemplos de requisições e respostas

### 3. **Testar Upload de Documento**

No Swagger UI:
1. Clique em `POST /api/v1/documents/upload`
2. Clique em "Try it out"
3. Clique em "Choose File" e selecione um PDF
4. Clique em "Execute"
5. Veja a resposta com o `document_id`

---

## 🔧 Testando via cURL

### Health Check
```bash
curl http://127.0.0.1:8000/health
```

### Métricas
```bash
curl http://127.0.0.1:8000/metrics
```

### Upload de Documento
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/documents/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@seu_documento.pdf"
```

### Status do Documento
```bash
curl http://127.0.0.1:8000/api/v1/documents/{document_id}/status
```

---

## 🐍 Testando via Python

```python
import requests

# Health check
response = requests.get("http://127.0.0.1:8000/health")
print(response.json())

# Upload de documento
with open("documento.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post(
        "http://127.0.0.1:8000/api/v1/documents/upload",
        files=files
    )
    print(response.json())
```

---

## ❓ Troubleshooting

### Problema: "Página em branco no Swagger UI"
**Solução:** ✅ JÁ CORRIGIDO! Os headers de segurança foram ajustados.

### Problema: "Cannot connect to server"
**Solução:** Certifique-se que o servidor está rodando:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Problema: "Port 8000 already in use"
**Solução:** Use outra porta:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### Problema: "Module not found"
**Solução:** Ative o ambiente virtual:
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

---

## 📊 O Que Foi Corrigido

### Antes (Problema):
- ❌ Content Security Policy muito restritivo
- ❌ Bloqueava recursos do CDN do Swagger UI
- ❌ Página em branco no navegador

### Depois (Solução):
- ✅ CSP ajustado para permitir Swagger UI
- ✅ Headers diferentes para docs vs API
- ✅ Swagger UI funcionando perfeitamente

### Mudanças Aplicadas:
1. **Headers de Segurança Ajustados** (`app/middleware/security_headers.py`)
   - CSP mais permissivo para `/docs` e `/redoc`
   - Permite recursos do CDN (jsdelivr.net, unpkg.com)
   - Mantém segurança para endpoints da API

2. **X-Frame-Options**
   - Mudado de `DENY` para `SAMEORIGIN` em docs
   - Permite que o Swagger UI funcione corretamente

---

## ✅ Checklist de Teste

- [ ] Servidor iniciado com sucesso
- [ ] Health check retorna status "healthy"
- [ ] Swagger UI carrega completamente
- [ ] Todos os endpoints aparecem no Swagger UI
- [ ] Botão "Try it out" funciona
- [ ] Métricas acessíveis
- [ ] OpenAPI JSON válido

---

## 🎉 Pronto!

Agora você pode testar completamente a API! O Swagger UI deve estar funcionando perfeitamente em:

**http://127.0.0.1:8000/docs**

Se tiver qualquer problema, execute:
```bash
python debug_endpoints.py
```

Para ver todos os endpoints registrados e diagnosticar problemas.