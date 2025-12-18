#!/usr/bin/env python3
"""
Script para testar upload e processamento
"""
import requests
import time
import json

def test_upload_and_processing():
    """Test upload and processing workflow"""
    print("🧪 Testing upload and processing...")
    
    # Upload file
    print("\n📤 Uploading file...")
    
    try:
        with open("Contracto ALFA 5.pdf", "rb") as f:
            files = {"file": f}
            response = requests.post(
                "http://127.0.0.1:8000/api/v1/documents/upload",
                files=files
            )
        
        if response.status_code == 200:
            result = response.json()
            document_id = result["document_id"]
            print(f"✅ Upload successful! Document ID: {document_id}")
            
            # Monitor processing
            print("\n🔄 Monitoring processing...")
            
            for i in range(30):  # Wait up to 5 minutes
                status_response = requests.get(
                    f"http://127.0.0.1:8000/api/v1/documents/{document_id}/status"
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data["status"]
                    progress = status_data["progress"]
                    
                    print(f"📊 Status: {status} ({progress}%)")
                    
                    if status == "completed":
                        print("🎉 Processing completed!")
                        
                        # Get results
                        results_response = requests.get(
                            f"http://127.0.0.1:8000/api/v1/documents/{document_id}/results"
                        )
                        
                        if results_response.status_code == 200:
                            results = results_response.json()
                            print(f"📄 Pages processed: {len(results.get('pages', []))}")
                            print(f"📊 Metadata: {results.get('metadata', {})}")
                        
                        break
                    elif status == "failed":
                        print(f"❌ Processing failed: {status_data.get('error_message')}")
                        break
                    
                    time.sleep(10)  # Wait 10 seconds
                else:
                    print(f"❌ Status check failed: {status_response.status_code}")
                    break
            
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(response.text)
            
    except FileNotFoundError:
        print("❌ File 'Contracto ALFA 5.pdf' not found")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_upload_and_processing()