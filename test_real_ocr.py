#!/usr/bin/env python3
"""
Script para testar OCR com documento real
"""
import requests
import time
import json

def test_real_ocr():
    """Test OCR with a real document that has extractable text"""
    print("🧪 Testing OCR with real document...")
    
    # Use the document we know has text
    filename = "uploads/a6542039-9356-440e-bd46-a53002cca9f4/teste_original.pdf"
    
    try:
        with open(filename, "rb") as f:
            files = {"file": f}
            response = requests.post(
                "http://127.0.0.1:8000/api/v1/documents/upload",
                files=files
            )
        
        if response.status_code == 200:
            result = response.json()
            document_id = result["document_id"]
            print(f"✅ Upload successful! Document ID: {document_id}")
            
            # Wait for processing
            print("\n🔄 Waiting for processing...")
            time.sleep(30)  # Wait 30 seconds
            
            # Get results
            results_response = requests.get(
                f"http://127.0.0.1:8000/api/v1/documents/{document_id}/results"
            )
            
            if results_response.status_code == 200:
                results = results_response.json()
                print(f"✅ Results retrieved!")
                print(f"📊 Status: {results['status']}")
                print(f"📄 Pages: {len(results['pages'])}")
                print(f"🏷️ Legal terms: {results['legal_terms']}")
                
                # Show content from first page
                if results['pages']:
                    first_page = results['pages'][0]
                    print(f"\n📄 Page 1 Content:")
                    print(f"   📝 Raw text: {len(first_page['raw_text'])} chars")
                    
                    if len(first_page['raw_text']) > 50:
                        preview = first_page['raw_text'][:500]
                        print(f"   👀 Preview:\n{preview}...")
                    else:
                        print(f"   👀 Full text: {first_page['raw_text']}")
            else:
                print(f"❌ Failed to get results: {results_response.status_code}")
                print(results_response.text)
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(response.text)
            
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_real_ocr()