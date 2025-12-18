#!/usr/bin/env python3
"""
Teste simples de upload para diagnosticar o problema
"""
import sys
import tempfile
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

import requests

def test_upload():
    """Testa o upload de um arquivo simples"""
    
    print("🧪 TESTE DE UPLOAD SIMPLES")
    print("=" * 40)
    
    # Criar um arquivo PDF falso para teste
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(pdf_content)
        tmp_file.flush()
        
        try:
            print(f"📄 Arquivo criado: {tmp_file.name}")
            print(f"📏 Tamanho: {len(pdf_content)} bytes")
            
            # Teste 1: Health check primeiro
            print(f"\n🏥 Testando health check...")
            health_response = requests.get("http://127.0.0.1:8000/health")
            print(f"  Status: {health_response.status_code}")
            if health_response.status_code == 200:
                print(f"  ✅ Health check OK")
            else:
                print(f"  ❌ Health check falhou")
                return
            
            # Teste 2: Upload do arquivo
            print(f"\n📤 Testando upload...")
            
            with open(tmp_file.name, 'rb') as f:
                files = {'file': ('test.pdf', f, 'application/pdf')}
                
                try:
                    response = requests.post(
                        "http://127.0.0.1:8000/api/v1/documents/upload",
                        files=files,
                        timeout=30
                    )
                    
                    print(f"  Status Code: {response.status_code}")
                    print(f"  Headers: {dict(response.headers)}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f"  ✅ Upload bem-sucedido!")
                        print(f"  Document ID: {data.get('document_id', 'N/A')}")
                        print(f"  Status: {data.get('status', 'N/A')}")
                        print(f"  Mensagem: {data.get('message', 'N/A')}")
                    else:
                        print(f"  ❌ Upload falhou")
                        print(f"  Resposta: {response.text}")
                        
                        # Tentar parsear como JSON
                        try:
                            error_data = response.json()
                            print(f"  Erro JSON: {error_data}")
                        except:
                            print(f"  Resposta não é JSON válido")
                    
                except requests.exceptions.RequestException as e:
                    print(f"  ❌ Erro de conexão: {e}")
                except Exception as e:
                    print(f"  ❌ Erro inesperado: {e}")
            
        finally:
            # Limpar arquivo temporário
            import os
            try:
                os.unlink(tmp_file.name)
            except:
                pass

if __name__ == "__main__":
    test_upload()