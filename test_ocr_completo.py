#!/usr/bin/env python3
"""
Teste completo do fluxo de OCR - Upload → Status → Resultados
"""
import sys
import time
import tempfile
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

import requests

def test_fluxo_ocr_completo():
    """Testa o fluxo completo de OCR"""
    
    print("🔄 TESTE COMPLETO DO FLUXO DE OCR")
    print("=" * 50)
    
    # Criar um arquivo PDF de teste
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(CONTRATO DE TESTE) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \n0000000179 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n274\n%%EOF"
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(pdf_content)
        tmp_file.flush()
        
        try:
            # PASSO 1: UPLOAD
            print(f"\n📤 PASSO 1: FAZENDO UPLOAD...")
            
            with open(tmp_file.name, 'rb') as f:
                files = {'file': ('contrato_teste.pdf', f, 'application/pdf')}
                
                response = requests.post(
                    "http://127.0.0.1:8000/api/v1/documents/upload",
                    files=files,
                    timeout=30
                )
                
                if response.status_code != 200:
                    print(f"❌ Upload falhou: {response.status_code}")
                    print(f"Resposta: {response.text}")
                    return
                
                upload_data = response.json()
                document_id = upload_data.get('document_id')
                
                print(f"✅ Upload bem-sucedido!")
                print(f"   Document ID: {document_id}")
                print(f"   Status inicial: {upload_data.get('status')}")
            
            # PASSO 2: ACOMPANHAR STATUS
            print(f"\n📊 PASSO 2: ACOMPANHANDO STATUS...")
            
            max_tentativas = 10
            tentativa = 0
            
            while tentativa < max_tentativas:
                tentativa += 1
                
                status_response = requests.get(
                    f"http://127.0.0.1:8000/api/v1/documents/{document_id}/status",
                    timeout=10
                )
                
                if status_response.status_code != 200:
                    print(f"❌ Erro ao verificar status: {status_response.status_code}")
                    break
                
                status_data = status_response.json()
                current_status = status_data.get('status')
                progress = status_data.get('progress', 0)
                
                print(f"   Tentativa {tentativa}: Status = {current_status}, Progresso = {progress}%")
                
                if current_status == 'completed':
                    print(f"✅ Processamento concluído!")
                    break
                elif current_status == 'failed':
                    print(f"❌ Processamento falhou!")
                    error_msg = status_data.get('error_message', 'Erro desconhecido')
                    print(f"   Erro: {error_msg}")
                    return
                elif current_status in ['queued', 'processing']:
                    print(f"⏳ Aguardando... (Status: {current_status})")
                    time.sleep(2)  # Aguarda 2 segundos
                else:
                    print(f"⚠️ Status desconhecido: {current_status}")
                    time.sleep(2)
            
            if tentativa >= max_tentativas:
                print(f"⏰ Timeout - processamento ainda não terminou após {max_tentativas} tentativas")
                print(f"💡 Você pode verificar manualmente o status mais tarde")
                return
            
            # PASSO 3: OBTER RESULTADOS
            print(f"\n📄 PASSO 3: OBTENDO RESULTADOS DO OCR...")
            
            results_response = requests.get(
                f"http://127.0.0.1:8000/api/v1/documents/{document_id}/results",
                timeout=10
            )
            
            if results_response.status_code != 200:
                print(f"❌ Erro ao obter resultados: {results_response.status_code}")
                print(f"Resposta: {results_response.text}")
                return
            
            results_data = results_response.json()
            
            print(f"✅ Resultados obtidos com sucesso!")
            print(f"\n📋 RESUMO DOS RESULTADOS:")
            print(f"   Document ID: {results_data.get('document_id')}")
            print(f"   Status: {results_data.get('status')}")
            
            pages = results_data.get('pages', [])
            print(f"   Total de páginas: {len(pages)}")
            
            for i, page in enumerate(pages, 1):
                print(f"\n   📄 PÁGINA {i}:")
                print(f"      Texto bruto: {page.get('raw_text', 'N/A')[:100]}...")
                print(f"      Texto normalizado: {page.get('normalized_text', 'N/A')[:100]}...")
                
                text_blocks = page.get('text_blocks', [])
                print(f"      Blocos de texto: {len(text_blocks)}")
                
                for j, block in enumerate(text_blocks[:3], 1):  # Mostra apenas os 3 primeiros
                    print(f"         Bloco {j}: '{block.get('text', 'N/A')}' (confiança: {block.get('confidence', 0):.2f})")
            
            metadata = results_data.get('metadata', {})
            if metadata:
                print(f"\n   📊 METADADOS:")
                print(f"      Tempo de processamento: {metadata.get('processing_time', 'N/A')}s")
                print(f"      Confiança média do OCR: {metadata.get('ocr_confidence', 'N/A')}")
                print(f"      Total de páginas: {metadata.get('total_pages', 'N/A')}")
            
            print(f"\n🎉 TESTE COMPLETO FINALIZADO COM SUCESSO!")
            print(f"📝 Para testar no Swagger UI:")
            print(f"   1. Acesse: http://127.0.0.1:8000/docs")
            print(f"   2. Use o Document ID: {document_id}")
            print(f"   3. Teste os endpoints de status e results")
            
        finally:
            # Limpar arquivo temporário
            import os
            try:
                os.unlink(tmp_file.name)
            except:
                pass

if __name__ == "__main__":
    test_fluxo_ocr_completo()