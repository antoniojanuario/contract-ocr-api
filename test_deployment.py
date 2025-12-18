#!/usr/bin/env python3
"""
Script de teste rápido para verificar as otimizações de deployment
"""
import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.core.monitoring import resource_monitor, get_health_metrics
from app.main import app

async def test_deployment_features():
    """Testa as funcionalidades de deployment implementadas"""
    
    print("🚀 TESTE DAS OTIMIZAÇÕES DE DEPLOYMENT")
    print("=" * 50)
    
    # 1. Configurações do ambiente
    print("\n📋 CONFIGURAÇÕES DO AMBIENTE:")
    print(f"  Ambiente detectado: {settings.ENVIRONMENT}")
    print(f"  Plataforma gratuita: {'Sim' if settings.is_free_platform else 'Não'}")
    print(f"  Modo debug: {'Sim' if settings.DEBUG else 'Não'}")
    
    # 2. Otimizações de recursos
    print("\n⚡ OTIMIZAÇÕES DE RECURSOS:")
    print(f"  Tamanho máximo de arquivo: {settings.optimized_max_file_size/1024/1024:.0f}MB")
    print(f"  Timeout OCR otimizado: {settings.optimized_ocr_timeout}s")
    print(f"  Número de workers: {settings.WORKER_COUNT}")
    print(f"  Tarefas concorrentes máximas: {settings.MAX_CONCURRENT_TASKS}")
    
    # 3. Configurações de banco de dados
    print("\n🗄️ CONFIGURAÇÕES DE BANCO:")
    print(f"  URL do banco: {settings.DATABASE_URL[:50]}...")
    print(f"  Redis habilitado: {'Sim' if settings.USE_REDIS else 'Não'}")
    
    # 4. Métricas do sistema
    print("\n📊 MÉTRICAS DO SISTEMA:")
    try:
        metrics = await resource_monitor.get_system_metrics()
        print(f"  CPU: {metrics['cpu']['percent']:.1f}%")
        print(f"  Memória: {metrics['memory']['percent']:.1f}%")
        print(f"  Memória disponível: {metrics['memory']['available_mb']:.0f}MB")
        print(f"  Disco: {metrics['disk']['percent']:.1f}%")
        print(f"  Processos: {metrics['processes']}")
    except Exception as e:
        print(f"  ❌ Erro ao obter métricas: {e}")
    
    # 5. Health check
    print("\n🏥 HEALTH CHECK:")
    try:
        health = await get_health_metrics()
        print(f"  Status: {health['status']}")
        print(f"  Versão: {health['version']}")
        print(f"  Ambiente: {health['environment']}")
    except Exception as e:
        print(f"  ❌ Erro no health check: {e}")
    
    # 6. Configurações de segurança
    print("\n🔒 CONFIGURAÇÕES DE SEGURANÇA:")
    print(f"  Headers de segurança: {'Habilitados' if settings.ENABLE_SECURITY_HEADERS else 'Desabilitados'}")
    print(f"  Log de requisições: {'Habilitado' if settings.ENABLE_REQUEST_LOGGING else 'Desabilitado'}")
    print(f"  API Key obrigatória: {'Sim' if settings.REQUIRE_API_KEY else 'Não'}")
    
    # 7. Rate limiting
    print("\n🚦 RATE LIMITING:")
    print(f"  Requisições por minuto: {settings.RATE_LIMIT_REQUESTS_PER_MINUTE}")
    print(f"  Requisições por hora: {settings.RATE_LIMIT_REQUESTS_PER_HOUR}")
    
    # 8. Monitoramento
    print("\n📈 MONITORAMENTO:")
    print(f"  Métricas habilitadas: {'Sim' if settings.ENABLE_METRICS else 'Não'}")
    print(f"  Porta de métricas: {settings.METRICS_PORT}")
    print(f"  Threshold CPU: {settings.CPU_ALERT_THRESHOLD}%")
    print(f"  Threshold Memória: {settings.MEMORY_ALERT_THRESHOLD}%")
    
    print("\n✅ TESTE CONCLUÍDO COM SUCESSO!")
    print("=" * 50)

def test_files_exist():
    """Verifica se os arquivos de deployment existem"""
    print("\n📁 ARQUIVOS DE DEPLOYMENT:")
    
    files_to_check = [
        "Dockerfile",
        "docker-compose.yml", 
        "render.yaml",
        "railway.json",
        "Procfile",
        ".env.example",
        ".env.render",
        ".env.railway",
        "requirements-deployment.txt"
    ]
    
    for file_path in files_to_check:
        if Path(file_path).exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} (não encontrado)")

if __name__ == "__main__":
    print("🧪 INICIANDO TESTES DE DEPLOYMENT...")
    
    # Teste de arquivos
    test_files_exist()
    
    # Teste assíncrono
    try:
        asyncio.run(test_deployment_features())
    except Exception as e:
        print(f"❌ Erro durante os testes: {e}")
        sys.exit(1)