# 📄 Contract OCR API

Uma API especializada para extração e normalização de texto de documentos contratuais usando tecnologia OCR avançada.

**🚀 Deploy Pronto:** Otimizado para Render.com (gratuito)  
**🤖 Copilot Studio:** Endpoints dedicados para integração  
**⚡ Rápido:** Processamento em 30-180 segundos  
**🔒 Seguro:** HTTPS, CORS, Rate Limiting

## ✨ Funcionalidades

- 📤 **Upload de PDFs** com validação automática
- 🔍 **OCR Multi-Engine** com fallback inteligente  
- 📝 **Normalização de Texto** para documentos legais
- 📄 **Organização por Páginas** com coordenadas precisas
- ⚡ **Processamento Assíncrono** com tracking de status
- 🌐 **API RESTful** com documentação OpenAPI completa
- 🤖 **Integração Copilot Studio** com endpoints otimizados
- 🚀 **Deploy Gratuito** em plataformas como Render.com

## Quick Start

### Prerequisites

- Python 3.8+
- Virtual environment (recommended)
- C++ build tools (for OCR dependencies - optional for initial setup)

### Installation

1. Clone the repository
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   # Basic dependencies (recommended for initial setup)
   pip install -r requirements.txt
   
   # Full dependencies including OCR (requires C++ build tools)
   # pip install -r requirements-full.txt
   ```

4. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```

5. Initialize the database:
   ```bash
   alembic upgrade head
   ```

### Running the Application

Development server:
```bash
python run.py
```

Or using uvicorn directly:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`

## Project Structure

```
├── app/
│   ├── api/v1/          # API endpoints
│   ├── core/            # Core configuration and utilities
│   ├── db/              # Database configuration
│   ├── models/          # Data models
│   └── services/        # Business logic services
├── alembic/             # Database migrations
├── tests/               # Test suite
├── requirements.txt     # Python dependencies
└── run.py              # Development server runner
```

## Configuration

The application uses environment variables for configuration. See `.env.example` for available options.

## Testing

Run tests with pytest:
```bash
pytest
```

## 🚀 Deploy Rápido

### Render.com (Recomendado)

1. **Fork/Clone** este repositório
2. **Crie conta** em [Render.com](https://render.com)
3. **New Web Service** → Conecte seu repositório
4. **Configure:**
   - Build: `pip install -r requirements.txt`
   - Start: `chmod +x start_render.sh && ./start_render.sh`
5. **Adicione PostgreSQL** (Free tier)
6. **Deploy!** 🎉

**Documentação completa:** [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)

## 🤖 Integração com Copilot Studio

### Endpoints Otimizados

```http
POST /api/v1/copilot/extract-text  # Upload e processar PDF
GET  /api/v1/copilot/status/{id}   # Verificar status
GET  /api/v1/copilot/text/{id}     # Obter texto extraído
```

### Exemplo de Uso

```python
# 1. Upload
response = requests.post(
    "https://your-api.onrender.com/api/v1/copilot/extract-text",
    files={"file": open("contrato.pdf", "rb")}
)
document_id = response.json()["document_id"]

# 2. Aguardar processamento
while True:
    status = requests.get(f".../copilot/status/{document_id}").json()
    if status["is_complete"]:
        break
    time.sleep(10)

# 3. Obter texto
text = requests.get(f".../copilot/text/{document_id}").json()
print(text["text"])  # Texto completo extraído!
```

**Documentação completa:** [COPILOT_INTEGRATION.md](COPILOT_INTEGRATION.md)

## 📊 Limites do Plano Gratuito

- **Arquivo:** Máximo 25MB por PDF
- **Páginas:** Até 50 páginas por documento
- **Timeout:** 3 minutos de processamento
- **Concurrent:** 1 processamento simultâneo
- **Storage:** 1GB PostgreSQL

## 🛠️ Desenvolvimento Local

### Worker + API

```bash
# Terminal 1: API
python -m uvicorn app.main:app --reload

# Terminal 2: Worker
python integrated_worker.py
```

Ou use o script integrado:
```bash
chmod +x start_render.sh
./start_render.sh
```

## 📚 Documentação

- **Deploy:** [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)
- **Copilot Studio:** [COPILOT_INTEGRATION.md](COPILOT_INTEGRATION.md)
- **Worker:** [COMO_INICIAR_WORKER.md](COMO_INICIAR_WORKER.md)
- **API Docs:** `https://your-api.onrender.com/docs`

## 🎯 Casos de Uso

- ✅ Extração de texto de contratos bancários
- ✅ Análise de documentos legais
- ✅ Processamento de propostas comerciais
- ✅ Digitalização de arquivos físicos
- ✅ Integração com chatbots (Copilot Studio)
- ✅ Automação de workflows documentais

## 🔧 Tecnologias

- **FastAPI** - Framework web moderno
- **SQLAlchemy** - ORM para banco de dados
- **pdfplumber/pypdf** - Extração de texto de PDFs (sem compilação)
- **PostgreSQL** - Banco de dados em produção
- **Uvicorn** - Servidor ASGI de alta performance

## 📝 Licença

MIT License - Veja [LICENSE](LICENSE) para detalhes.

---

**🎉 Pronto para deploy! Siga o [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md) para colocar sua API no ar em minutos!**