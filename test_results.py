#!/usr/bin/env python3
"""
Script para testar o endpoint de resultados e ver o texto OCR
"""
import requests
import json

def test_results():
    """Test results endpoint to see OCR text"""
    document_id = "8b39bf9c-88fd-476c-b2c5-6999d64807bb"  # multi_page_contract.pdf com 3 páginas
    
    print(f"🔍 Getting results for document: {document_id}")
    
    try:
        response = requests.get(f"http://127.0.0.1:8000/api/v1/documents/{document_id}/results")
        
        if response.status_code == 200:
            results = response.json()
            
            print(f"✅ Results retrieved successfully!")
            print(f"📊 Status: {results['status']}")
            print(f"📄 Pages: {len(results['pages'])}")
            print(f"🏷️ Legal terms: {results['legal_terms']}")
            
            # Show first page content
            if results['pages']:
                first_page = results['pages'][0]
                print(f"\n📄 Page 1:")
                print(f"   📝 Raw text length: {len(first_page['raw_text'])} characters")
                print(f"   🔧 Normalized text length: {len(first_page['normalized_text'])} characters")
                print(f"   🎯 Text blocks: {len(first_page['text_blocks'])}")
                
                # Show preview of text
                if first_page['raw_text']:
                    preview = first_page['raw_text'][:500].replace('\n', ' ')
                    print(f"   👀 Preview: {preview}...")
                
                # Show text blocks
                if first_page['text_blocks']:
                    print(f"\n🔤 Text Blocks:")
                    for i, block in enumerate(first_page['text_blocks'][:3]):  # Show first 3 blocks
                        print(f"   Block {i+1}: {block['text'][:100]}...")
                        print(f"   Confidence: {block['confidence']}")
            
        else:
            print(f"❌ Failed to get results: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_results()