#!/usr/bin/env python3
"""
Debug script para verificar endpoints registrados
"""
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.main import app

def debug_endpoints():
    """Debug dos endpoints registrados"""
    
    print("🔍 DEBUG DOS ENDPOINTS REGISTRADOS")
    print("=" * 50)
    
    print(f"\n📋 Configuração da aplicação:")
    print(f"  Título: {app.title}")
    print(f"  Versão: {app.version}")
    print(f"  OpenAPI URL: {app.openapi_url}")
    print(f"  Docs URL: {app.docs_url}")
    print(f"  Redoc URL: {app.redoc_url}")
    
    print(f"\n🛣️ Rotas registradas:")
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = ', '.join(route.methods) if route.methods else 'N/A'
            print(f"  {methods:10} {route.path}")
        elif hasattr(route, 'path'):
            print(f"  {'MOUNT':10} {route.path}")
    
    print(f"\n📊 Total de rotas: {len(app.routes)}")
    
    # Verificar se o OpenAPI schema está sendo gerado
    try:
        schema = app.openapi()
        paths_count = len(schema.get('paths', {}))
        print(f"\n📋 OpenAPI Schema:")
        print(f"  Versão OpenAPI: {schema.get('openapi', 'N/A')}")
        print(f"  Título: {schema.get('info', {}).get('title', 'N/A')}")
        print(f"  Número de paths: {paths_count}")
        
        if paths_count > 0:
            print(f"\n🛤️ Paths no OpenAPI:")
            for path in schema.get('paths', {}):
                methods = list(schema['paths'][path].keys())
                print(f"  {', '.join(methods):15} {path}")
        else:
            print(f"\n⚠️ PROBLEMA: Nenhum path encontrado no OpenAPI schema!")
            
    except Exception as e:
        print(f"\n❌ ERRO ao gerar OpenAPI schema: {e}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    debug_endpoints()