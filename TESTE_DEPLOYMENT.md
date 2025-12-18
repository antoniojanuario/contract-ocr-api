# 🧪 Guia de Testes - Otimizações de Deployment

Este guia mostra como testar todas as funcionalidades implementadas para deployment em plataformas gratuitas.

## ✅ O Que Foi Implementado

### 📦 Arquivos de Configuração de Deployment
- ✅ `Dockerfile` - Container Docker otimizado
- ✅ `docker-compose.yml` - Orquestração completa
- ✅ `render.yaml` - Configuração para Render
- ✅ `railway.json` - Configuração para Railway
- ✅ `Procfile` - Para Heroku e similares
- ✅ `.env.example`, `.env.render`, `.env.railway` - Templates de ambiente

### ⚙️ Otimizações Implementadas
- ✅ Detecção automática de ambiente (local, render, railway, heroku)
- ✅ Ajuste automático de recursos baseado na plataforma
- ✅ Monitoramento de CPU, memória e disco
- ✅ Sistema de alertas para recursos
- ✅ Health checks e métricas Prometheus
- ✅ Configuração otimizada de banco de dados
- ✅ Pool de conexões ajustado para plataformas gratuitas

### 🛠️ Scripts de Deployment
- ✅ `scripts/init_db.py` - Inicialização do banco
- ✅ `scripts/migrate_db.py` - Migrações
- ✅ `scripts/deployment_check.py` - Verificação de prontidão
- ✅ `scripts/start.py` - Startup otimizado

### 🧪 Testes de Integração
- ✅ `tests/test_deployment_integration.py` - Testes completos de deployment

---

## 🚀 Como Testar

### 1. Teste Rápido das Configurações

```bash
# Teste as configurações de deployment
python test_deployment.py
```

**O que este teste verifica:**
- ✅ Ambiente detectado corretamente
- ✅ Otimizações de recursos aplicadas
- ✅ Configurações de banco de dados
- ✅ Métricas do sistema
- ✅ Health check funcionando
- ✅ Configurações de segurança
- ✅ Rate limiting configurado
- ✅ Monitoramento habilitado

### 2. Teste dos Endpoints da API

```bash
# Teste todos os endpoints principais
python test_api_endpoints.py
```

**O que este teste verifica:**
- ✅ Health check endpoint (`/health`)
- ✅ Métricas endpoint (`/metrics`)
- ✅ Root endpoint redirecionando para docs
- ✅ OpenAPI schema disponível
- ✅ Swagger UI funcionando
- ✅ CORS configurado corretamente

### 3. Iniciar a Aplicação Localmente

```bash
# Inicia o servidor de desenvolvimento
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Depois acesse no navegador:**
- 📚 Documentação: http://127.0.0.1:8000/docs
- 🏥 Health Check: http://127.0.0.1:8000/health
- 📊 Métricas: http://127.0.0.1:8000/metrics
- 🏠 Página Inicial: http://127.0.0.1:8000/

### 4. Testes de Integração Completos

```bash
# Roda todos os testes de deployment
python -m pytest tests/test_deployment_integration.py -v

# Ou testes específicos:
python -m pytest tests/test_deployment_integration.py::TestApplicationStartup -v
python -m pytest tests/test_deployment_integration.py::TestEnvironmentConfiguration -v
python -m pytest tests/test_deployment_integration.py::TestResourceConstraints -v
```

### 5. Verificação de Prontidão para Deploy

```bash
# Verifica se está tudo pronto para deploy
python scripts/deployment_check.py
```

**Este script verifica:**
- ✅ Configurações de ambiente
- ✅ Conectividade do banco de dados
- ✅ Schema do banco inicializado
- ✅ Recursos do sistema
- ✅ Arquivos necessários presentes
- ✅ Dependências instaladas
- ✅ Configuração do Docker

---

## 🐳 Teste com Docker

### Construir a Imagem

```bash
docker build -t contract-ocr-api .
```

### Rodar o Container

```bash
# Rodar apenas a aplicação
docker run -p 8000:8000 contract-ocr-api

# Ou usar docker-compose (com Redis)
docker-compose up
```

### Testar o Container

```bash
# Health check
curl http://localhost:8000/health

# Métricas
curl http://localhost:8000/metrics
```

---

## ☁️ Deploy em Plataformas Gratuitas

### Deploy no Render

1. **Conecte seu repositório ao Render**
2. **O arquivo `render.yaml` será detectado automaticamente**
3. **Configure as variáveis de ambiente (se necessário)**
4. **Deploy automático!**

**Configurações aplicadas automaticamente:**
- Tamanho máximo de arquivo: 24MB
- Timeout OCR: 3 minutos
- Workers: 1
- Rate limiting reduzido

### Deploy no Railway

1. **Conecte seu repositório ao Railway**
2. **O arquivo `railway.json` será detectado automaticamente**
3. **Adicione um banco PostgreSQL (opcional)**
4. **Deploy automático!**

**Configurações aplicadas automaticamente:**
- Tamanho máximo de arquivo: 20MB
- Timeout OCR: 2 minutos
- Workers: 1
- Redis desabilitado (usa fila em memória)

### Deploy no Heroku

1. **Conecte seu repositório ao Heroku**
2. **O `Procfile` será detectado automaticamente**
3. **Configure as variáveis de ambiente**
4. **Deploy!**

```bash
# Via CLI do Heroku
heroku create contract-ocr-api
git push heroku main
```

---

## 📊 Monitoramento em Produção

### Endpoints de Monitoramento

1. **Health Check:** `GET /health`
   ```json
   {
     "status": "healthy",
     "version": "1.0.0",
     "environment": "production",
     "metrics": {
       "cpu": {"percent": 45.2},
       "memory": {"percent": 67.8},
       "disk": {"percent": 42.1}
     }
   }
   ```

2. **Métricas Prometheus:** `GET /metrics`
   ```
   # HELP cpu_usage_percent CPU usage percentage
   # TYPE cpu_usage_percent gauge
   cpu_usage_percent 45.2
   
   # HELP memory_usage_percent Memory usage percentage
   # TYPE memory_usage_percent gauge
   memory_usage_percent 67.8
   ```

### Alertas Automáticos

O sistema monitora automaticamente:
- ✅ CPU > 80% → Alerta de warning
- ✅ CPU > 95% → Alerta crítico
- ✅ Memória > 85% → Alerta de warning
- ✅ Memória < 100MB disponível → Alerta crítico
- ✅ Disco > 90% → Alerta de warning

Configure webhook para receber alertas:
```bash
export ALERT_WEBHOOK_URL="https://seu-webhook.com/alerts"
```

---

## 🔧 Variáveis de Ambiente Importantes

### Para Plataformas Gratuitas

```bash
# Otimizações de recursos
MAX_FILE_SIZE=25165824          # 24MB
OCR_TIMEOUT=180                 # 3 minutos
MAX_CONCURRENT_TASKS=1          # 1 tarefa por vez
WORKER_COUNT=1                  # 1 worker

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=30
RATE_LIMIT_REQUESTS_PER_HOUR=500

# Monitoramento
ENABLE_METRICS=true
CPU_ALERT_THRESHOLD=75.0
MEMORY_ALERT_THRESHOLD=80.0
```

### Para Produção (Servidor Dedicado)

```bash
# Recursos completos
MAX_FILE_SIZE=52428800          # 50MB
OCR_TIMEOUT=300                 # 5 minutos
MAX_CONCURRENT_TASKS=4          # 4 tarefas simultâneas
WORKER_COUNT=4                  # 4 workers

# Rate limiting normal
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_REQUESTS_PER_HOUR=1000
```

---

## ✅ Checklist de Deploy

Antes de fazer deploy, verifique:

- [ ] Todos os testes passando (`pytest`)
- [ ] Health check funcionando
- [ ] Variáveis de ambiente configuradas
- [ ] Banco de dados configurado
- [ ] Arquivos de deployment presentes
- [ ] Docker build funcionando (se usar Docker)
- [ ] Verificação de deployment OK (`python scripts/deployment_check.py`)

---

## 🆘 Troubleshooting

### Problema: "Memória insuficiente"
**Solução:** Reduza `MAX_CONCURRENT_TASKS` e `WORKER_COUNT` para 1

### Problema: "Timeout no OCR"
**Solução:** Reduza `OCR_TIMEOUT` ou `MAX_FILE_SIZE`

### Problema: "Banco de dados não conecta"
**Solução:** Verifique `DATABASE_URL` e rode `python scripts/init_db.py`

### Problema: "Rate limit muito restritivo"
**Solução:** Ajuste `RATE_LIMIT_REQUESTS_PER_MINUTE` conforme necessário

---

## 📚 Recursos Adicionais

- **Documentação da API:** http://localhost:8000/docs
- **Logs:** Verifique `logs/app.log`
- **Métricas:** http://localhost:8000/metrics
- **Health Check:** http://localhost:8000/health

---

## 🎉 Conclusão

Todas as otimizações para deployment em plataformas gratuitas foram implementadas com sucesso! A aplicação está pronta para ser deployada no Render, Railway, Heroku ou qualquer outra plataforma.

**Principais benefícios:**
- ✅ Detecção automática de ambiente
- ✅ Otimização automática de recursos
- ✅ Monitoramento em tempo real
- ✅ Alertas automáticos
- ✅ Configuração simplificada
- ✅ Pronto para produção