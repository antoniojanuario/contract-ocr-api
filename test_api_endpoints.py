#!/usr/bin/env python3
"""
Teste dos endpoints da API usando TestClient
"""
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from app.main import app

def test_api_endpoints():
    """Testa os principais endpoints da API"""
    
    print("🌐 TESTANDO ENDPOINTS DA API")
    print("=" * 40)
    
    client = TestClient(app)
    
    # 1. Health Check
    print("\n🏥 Testando Health Check...")
    try:
        response = client.get("/health")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Status da aplicação: {data.get('status', 'N/A')}")
            print(f"  Versão: {data.get('version', 'N/A')}")
            print(f"  ✅ Health check OK")
        else:
            print(f"  ❌ Health check falhou")
    except Exception as e:
        print(f"  ❌ Erro: {e}")
    
    # 2. Metrics
    print("\n📊 Testando Metrics...")
    try:
        response = client.get("/metrics")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  ✅ Métricas disponíveis")
            # Mostra primeiras linhas das métricas
            lines = response.text.split('\n')[:5]
            for line in lines:
                if line.strip():
                    print(f"    {line}")
        else:
            print(f"  ⚠️ Métricas não disponíveis (pode estar desabilitado)")
    except Exception as e:
        print(f"  ❌ Erro: {e}")
    
    # 3. Root endpoint
    print("\n🏠 Testando Root endpoint...")
    try:
        response = client.get("/", follow_redirects=False)
        print(f"  Status: {response.status_code}")
        if response.status_code in [307, 302]:
            print(f"  ✅ Redirecionamento para documentação OK")
        else:
            print(f"  ⚠️ Comportamento inesperado")
    except Exception as e:
        print(f"  ❌ Erro: {e}")
    
    # 4. OpenAPI Schema
    print("\n📋 Testando OpenAPI Schema...")
    try:
        response = client.get("/api/v1/openapi.json")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            schema = response.json()
            print(f"  ✅ Schema OpenAPI disponível")
            print(f"    Título: {schema.get('info', {}).get('title', 'N/A')}")
            print(f"    Versão: {schema.get('info', {}).get('version', 'N/A')}")
            print(f"    Endpoints: {len(schema.get('paths', {}))}")
        else:
            print(f"  ❌ Schema não disponível")
    except Exception as e:
        print(f"  ❌ Erro: {e}")
    
    # 5. Swagger UI
    print("\n📚 Testando Swagger UI...")
    try:
        response = client.get("/docs")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  ✅ Swagger UI disponível")
        else:
            print(f"  ❌ Swagger UI não disponível")
    except Exception as e:
        print(f"  ❌ Erro: {e}")
    
    # 6. CORS Headers
    print("\n🌍 Testando CORS...")
    try:
        response = client.options(
            "/api/v1/documents/upload",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST"
            }
        )
        print(f"  Status: {response.status_code}")
        if response.status_code in [200, 204]:
            print(f"  ✅ CORS configurado")
        else:
            print(f"  ⚠️ CORS pode não estar configurado corretamente")
    except Exception as e:
        print(f"  ❌ Erro: {e}")
    
    print("\n✅ TESTE DOS ENDPOINTS CONCLUÍDO!")
    print("=" * 40)

if __name__ == "__main__":
    test_api_endpoints()