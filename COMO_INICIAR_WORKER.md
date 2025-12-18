# 🔄 Como Iniciar o Worker para Processar OCR

## ❓ **Por que fica em "queued"?**

O documento fica em status "queued" porque **o worker de processamento não está rodando**!

### 📊 **Arquitetura do Sistema:**

```
📤 Upload → 📋 Fila → 🔄 Worker → 🔍 OCR → 📄 Resultados
   ✅        ✅        ❌        ❌       ❌
```

**Situação atual:**
- ✅ **API rodando** - recebe uploads e salva na fila
- ❌ **Worker parado** - não processa a fila

---

## 🚀 **SOLUÇÃO: Iniciar o Worker**

### **Método 1: Dois Terminais (Recomendado)**

#### **Terminal 1: API (já rodando)**
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### **Terminal 2: Worker (novo)**
```bash
python run_worker.py
```

### **Método 2: Docker Compose (Automático)**
```bash
docker-compose up
```
*Inicia API + Worker + Redis automaticamente*

### **Método 3: Background Process**
```bash
# Windows
start python run_worker.py

# Linux/Mac
python run_worker.py &
```

---

## ⏱️ **Tempos de Processamento:**

### **Após iniciar o worker:**

| Tamanho do Arquivo | Tempo Esperado |
|-------------------|----------------|
| **Pequeno (< 1MB)** | 10-30 segundos |
| **Médio (1-5MB)** | 30-90 segundos |
| **Grande (5-25MB)** | 1-5 minutos |

### **Status do Processamento:**

1. **`queued`** → Na fila (instantâneo)
2. **`processing`** → Sendo processado (10s-5min)
3. **`completed`** → Pronto! ✅

---

## 🔍 **Como Verificar se o Worker Está Funcionando:**

### **1. Logs do Worker:**
Quando você rodar `python run_worker.py`, deve ver:
```
2025-12-18 12:30:00 - app.services.task_worker - INFO - Starting worker manager with 1 workers
2025-12-18 12:30:00 - app.services.task_worker - INFO - Worker 1 started
2025-12-18 12:30:00 - app.services.task_worker - INFO - Waiting for tasks...
```

### **2. Quando Processar um Documento:**
```
2025-12-18 12:30:15 - app.services.task_worker - INFO - Processing task abc123 for document def456
2025-12-18 12:30:45 - app.services.task_worker - INFO - Task abc123 completed successfully
```

### **3. Verificar Status via API:**
```bash
# Substitua abc123 pelo seu document_id
curl http://127.0.0.1:8000/api/v1/documents/abc123/status
```

---

## 🛠️ **Troubleshooting:**

### **Problema: "ModuleNotFoundError"**
**Solução:**
```bash
# Certifique-se que está no diretório correto
cd /caminho/para/seu/projeto

# Ative o ambiente virtual
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Execute o worker
python run_worker.py
```

### **Problema: Worker não processa**
**Verificações:**
1. ✅ Worker está rodando?
2. ✅ Banco de dados conectado?
3. ✅ Dependências instaladas? (`pip install -r requirements.txt`)

### **Problema: Erro de dependências OCR**
**Solução:**
```bash
# Instalar dependências de OCR
pip install easyocr paddlepaddle paddleocr pytesseract
```

---

## 📋 **Passo a Passo Completo:**

### **1. Preparar Ambiente:**
```bash
# Ativar ambiente virtual
.venv\Scripts\activate

# Instalar dependências (se necessário)
pip install -r requirements.txt
```

### **2. Iniciar Serviços:**

**Terminal 1 - API:**
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 - Worker:**
```bash
python run_worker.py
```

### **3. Testar:**

1. **Upload:** http://127.0.0.1:8000/docs → `POST /api/v1/documents/upload`
2. **Status:** `GET /api/v1/documents/{document_id}/status`
3. **Aguardar:** Status muda de `queued` → `processing` → `completed`
4. **Resultados:** `GET /api/v1/documents/{document_id}/results`

---

## 🎯 **Exemplo Prático:**

### **Cenário Típico:**

```bash
# 1. Upload (retorna document_id)
curl -X POST "http://127.0.0.1:8000/api/v1/documents/upload" \
  -F "file=@contrato.pdf"
# Resultado: {"document_id": "abc123", "status": "queued"}

# 2. Verificar status (repetir até completed)
curl http://127.0.0.1:8000/api/v1/documents/abc123/status
# queued → processing → completed (30-60 segundos)

# 3. Obter resultados
curl http://127.0.0.1:8000/api/v1/documents/abc123/results
# Texto extraído do PDF!
```

---

## ⚡ **Dica Rápida:**

**Para testar rapidamente:**

1. **Abra 2 terminais**
2. **Terminal 1:** `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`
3. **Terminal 2:** `python run_worker.py`
4. **Faça upload no Swagger UI:** http://127.0.0.1:8000/docs
5. **Aguarde 30-60 segundos**
6. **Verifique resultados!**

**Agora seus documentos vão sair de "queued" e serem processados!** 🎉