"""
Integration examples and templates for external systems
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse
from typing import Dict, Any

router = APIRouter()


@router.get("/copilot-studio/examples", tags=["integration"])
async def get_copilot_studio_examples():
    """
    Get Copilot Studio integration examples and templates
    
    Returns comprehensive examples for integrating the Contract OCR API with Microsoft Copilot Studio,
    including Power Automate flows, custom connectors, and bot conversation templates.
    """
    examples = {
        "power_automate_flow": {
            "description": "Complete Power Automate flow for document processing",
            "flow_definition": {
                "trigger": {
                    "type": "manual",
                    "inputs": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "file_content": {"type": "string", "format": "binary"},
                                "filename": {"type": "string"}
                            }
                        }
                    }
                },
                "actions": [
                    {
                        "name": "Upload_Document",
                        "type": "Http",
                        "inputs": {
                            "method": "POST",
                            "uri": "https://api.contractocr.com/api/v1/documents/upload",
                            "headers": {
                                "X-API-Key": "@parameters('api_key')",
                                "Content-Type": "multipart/form-data"
                            },
                            "body": {
                                "file": "@triggerBody()['file_content']"
                            }
                        }
                    },
                    {
                        "name": "Wait_For_Processing",
                        "type": "Until",
                        "expression": "@or(equals(body('Check_Status')['status'], 'completed'), equals(body('Check_Status')['status'], 'failed'))",
                        "actions": [
                            {
                                "name": "Check_Status",
                                "type": "Http",
                                "inputs": {
                                    "method": "GET",
                                    "uri": "https://api.contractocr.com/api/v1/documents/@{body('Upload_Document')['document_id']}/status",
                                    "headers": {
                                        "X-API-Key": "@parameters('api_key')"
                                    }
                                }
                            },
                            {
                                "name": "Delay",
                                "type": "Wait",
                                "inputs": {
                                    "interval": {
                                        "count": 10,
                                        "unit": "Second"
                                    }
                                }
                            }
                        ]
                    },
                    {
                        "name": "Get_Results",
                        "type": "Http",
                        "inputs": {
                            "method": "GET",
                            "uri": "https://api.contractocr.com/api/v1/documents/@{body('Upload_Document')['document_id']}/results",
                            "headers": {
                                "X-API-Key": "@parameters('api_key')"
                            }
                        }
                    }
                ]
            }
        },
        "custom_connector": {
            "description": "Custom connector definition for Power Platform",
            "swagger_definition": {
                "swagger": "2.0",
                "info": {
                    "title": "Contract OCR API",
                    "description": "OCR processing for contract documents",
                    "version": "1.0.0"
                },
                "host": "api.contractocr.com",
                "basePath": "/api/v1",
                "schemes": ["https"],
                "consumes": ["application/json", "multipart/form-data"],
                "produces": ["application/json"],
                "securityDefinitions": {
                    "API Key": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key"
                    }
                },
                "security": [{"API Key": []}],
                "paths": {
                    "/documents/upload": {
                        "post": {
                            "summary": "Upload document for OCR processing",
                            "operationId": "UploadDocument",
                            "consumes": ["multipart/form-data"],
                            "parameters": [
                                {
                                    "name": "file",
                                    "in": "formData",
                                    "type": "file",
                                    "required": True,
                                    "description": "PDF document to process"
                                }
                            ],
                            "responses": {
                                "200": {
                                    "description": "Document uploaded successfully",
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "document_id": {"type": "string"},
                                            "status": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "copilot_conversation_templates": {
            "description": "Conversation templates for Copilot Studio bots",
            "templates": [
                {
                    "name": "Contract Analysis Bot",
                    "trigger_phrases": [
                        "analyze contract",
                        "process document",
                        "extract contract terms"
                    ],
                    "conversation_flow": [
                        {
                            "step": 1,
                            "bot_message": "I'll help you analyze your contract document. Please upload the PDF file.",
                            "user_action": "file_upload",
                            "power_automate_action": "Upload_Document"
                        },
                        {
                            "step": 2,
                            "bot_message": "Processing your document... This may take a few minutes.",
                            "power_automate_action": "Wait_For_Processing"
                        },
                        {
                            "step": 3,
                            "bot_message": "Analysis complete! Here's what I found in your contract:",
                            "power_automate_action": "Get_Results",
                            "response_template": "**Document Summary:**\n- Pages: {page_count}\n- Processing Time: {processing_time}s\n- Confidence: {ocr_confidence}%\n\n**Key Terms Found:**\n{legal_terms}\n\n**Full Text Available:** Yes"
                        }
                    ]
                },
                {
                    "name": "Document Status Checker",
                    "trigger_phrases": [
                        "check document status",
                        "processing status",
                        "is my document ready"
                    ],
                    "conversation_flow": [
                        {
                            "step": 1,
                            "bot_message": "Please provide your document ID to check the processing status.",
                            "user_action": "text_input",
                            "validation": "uuid_format"
                        },
                        {
                            "step": 2,
                            "power_automate_action": "Check_Status",
                            "response_template": "**Document Status:** {status}\n**Progress:** {progress}%\n{status_message}"
                        }
                    ]
                }
            ]
        },
        "webhook_integration": {
            "description": "Webhook configuration for real-time notifications",
            "example_configuration": {
                "webhook_url": "https://your-power-automate-flow-url.com",
                "events": ["completed", "failed"],
                "headers": {
                    "Authorization": "Bearer your-token",
                    "Content-Type": "application/json"
                }
            },
            "payload_examples": {
                "completed": {
                    "event": "document.completed",
                    "document_id": "123e4567-e89b-12d3-a456-426614174000",
                    "status": "completed",
                    "processing_time": 45.2,
                    "ocr_confidence": 0.95,
                    "page_count": 12,
                    "timestamp": "2024-01-15T10:30:00Z"
                },
                "failed": {
                    "event": "document.failed",
                    "document_id": "123e4567-e89b-12d3-a456-426614174000",
                    "status": "failed",
                    "error_message": "OCR processing failed: corrupted PDF",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            }
        }
    }
    
    return examples


@router.get("/openapi-examples", tags=["integration"])
async def get_openapi_examples():
    """
    Get comprehensive OpenAPI usage examples
    
    Returns detailed examples for all API endpoints with sample requests and responses,
    including error scenarios and best practices.
    """
    examples = {
        "authentication": {
            "description": "API key authentication examples",
            "examples": {
                "curl": 'curl -H "X-API-Key: your-api-key-here" https://api.contractocr.com/api/v1/documents/upload',
                "javascript": '''
fetch('https://api.contractocr.com/api/v1/documents/upload', {
    method: 'POST',
    headers: {
        'X-API-Key': 'your-api-key-here'
    },
    body: formData
});''',
                "python": '''
import requests

headers = {'X-API-Key': 'your-api-key-here'}
response = requests.post(
    'https://api.contractocr.com/api/v1/documents/upload',
    headers=headers,
    files={'file': open('contract.pdf', 'rb')}
)'''
            }
        },
        "document_upload": {
            "description": "Document upload examples with different file types and error handling",
            "examples": {
                "successful_upload": {
                    "request": {
                        "method": "POST",
                        "url": "/api/v1/documents/upload",
                        "headers": {"X-API-Key": "your-api-key"},
                        "body": "multipart/form-data with PDF file"
                    },
                    "response": {
                        "status": 200,
                        "body": {
                            "document_id": "123e4567-e89b-12d3-a456-426614174000",
                            "status": "queued",
                            "message": "Document uploaded successfully and queued for processing"
                        }
                    }
                },
                "file_too_large": {
                    "request": {
                        "method": "POST",
                        "url": "/api/v1/documents/upload",
                        "headers": {"X-API-Key": "your-api-key"},
                        "body": "PDF file > 50MB"
                    },
                    "response": {
                        "status": 400,
                        "body": {
                            "error": {
                                "code": "FILE_TOO_LARGE",
                                "message": "File size exceeds maximum limit of 50MB",
                                "details": {"file_size": 52428800, "max_size": 52428800}
                            }
                        }
                    }
                },
                "invalid_format": {
                    "request": {
                        "method": "POST",
                        "url": "/api/v1/documents/upload",
                        "headers": {"X-API-Key": "your-api-key"},
                        "body": "Non-PDF file (e.g., .docx, .jpg)"
                    },
                    "response": {
                        "status": 400,
                        "body": {
                            "error": {
                                "code": "INVALID_FILE_FORMAT",
                                "message": "Only PDF files are supported",
                                "details": {"detected_format": "image/jpeg", "expected_format": "application/pdf"}
                            }
                        }
                    }
                }
            }
        },
        "status_tracking": {
            "description": "Document processing status tracking examples",
            "examples": {
                "queued": {
                    "request": {
                        "method": "GET",
                        "url": "/api/v1/documents/123e4567-e89b-12d3-a456-426614174000/status",
                        "headers": {"X-API-Key": "your-api-key"}
                    },
                    "response": {
                        "status": 200,
                        "body": {
                            "document_id": "123e4567-e89b-12d3-a456-426614174000",
                            "status": "queued",
                            "progress": 0,
                            "message": "Document is queued"
                        }
                    }
                },
                "processing": {
                    "response": {
                        "status": 200,
                        "body": {
                            "document_id": "123e4567-e89b-12d3-a456-426614174000",
                            "status": "processing",
                            "progress": 45,
                            "message": "Document is processing"
                        }
                    }
                },
                "completed": {
                    "response": {
                        "status": 200,
                        "body": {
                            "document_id": "123e4567-e89b-12d3-a456-426614174000",
                            "status": "completed",
                            "progress": 100,
                            "message": "Document is completed"
                        }
                    }
                }
            }
        },
        "results_retrieval": {
            "description": "Document results retrieval examples",
            "examples": {
                "successful_retrieval": {
                    "request": {
                        "method": "GET",
                        "url": "/api/v1/documents/123e4567-e89b-12d3-a456-426614174000/results",
                        "headers": {"X-API-Key": "your-api-key"}
                    },
                    "response": {
                        "status": 200,
                        "body": {
                            "document_id": "123e4567-e89b-12d3-a456-426614174000",
                            "status": "completed",
                            "progress": 100,
                            "pages": [
                                {
                                    "page_number": 1,
                                    "text_blocks": [
                                        {
                                            "text": "CONTRACT AGREEMENT",
                                            "confidence": 0.98,
                                            "bounding_box": {"x": 100, "y": 50, "width": 200, "height": 30},
                                            "is_title": True
                                        }
                                    ],
                                    "raw_text": "CONTRACT AGREEMENT\n\nThis agreement is made between...",
                                    "normalized_text": "CONTRACT AGREEMENT\n\nThis agreement is made between..."
                                }
                            ],
                            "metadata": {
                                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                                "filename": "contract.pdf",
                                "file_size": 1048576,
                                "page_count": 5,
                                "processing_time": 45.2,
                                "ocr_confidence": 0.95,
                                "created_at": "2024-01-15T10:00:00Z",
                                "updated_at": "2024-01-15T10:01:00Z"
                            },
                            "legal_terms": ["agreement", "contract", "party", "terms", "conditions"]
                        }
                    }
                }
            }
        }
    }
    
    return examples


@router.get("/sdk-examples", tags=["integration"])
async def get_sdk_examples():
    """
    Get SDK and client library examples
    
    Returns code examples for popular programming languages and frameworks
    for integrating with the Contract OCR API.
    """
    examples = {
        "python": {
            "description": "Python client examples using requests library",
            "installation": "pip install requests",
            "examples": {
                "basic_client": '''
import requests
import time
import json

class ContractOCRClient:
    def __init__(self, api_key, base_url="https://api.contractocr.com/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
    
    def upload_document(self, file_path):
        """Upload a document for processing"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{self.base_url}/documents/upload",
                headers=self.headers,
                files=files
            )
        return response.json()
    
    def get_status(self, document_id):
        """Get processing status"""
        response = requests.get(
            f"{self.base_url}/documents/{document_id}/status",
            headers=self.headers
        )
        return response.json()
    
    def get_results(self, document_id):
        """Get processing results"""
        response = requests.get(
            f"{self.base_url}/documents/{document_id}/results",
            headers=self.headers
        )
        return response.json()
    
    def process_document(self, file_path, timeout=300):
        """Complete document processing workflow"""
        # Upload
        upload_result = self.upload_document(file_path)
        document_id = upload_result['document_id']
        
        # Wait for completion
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_status(document_id)
            if status['status'] == 'completed':
                return self.get_results(document_id)
            elif status['status'] == 'failed':
                raise Exception(f"Processing failed: {status.get('error_message')}")
            time.sleep(10)
        
        raise TimeoutError("Processing timeout")

# Usage example
client = ContractOCRClient("your-api-key")
results = client.process_document("contract.pdf")
print(json.dumps(results, indent=2))
''',
                "async_client": '''
import aiohttp
import asyncio
import json

class AsyncContractOCRClient:
    def __init__(self, api_key, base_url="https://api.contractocr.com/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
    
    async def upload_document(self, file_path):
        """Upload a document for processing"""
        async with aiohttp.ClientSession() as session:
            with open(file_path, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename=file_path)
                
                async with session.post(
                    f"{self.base_url}/documents/upload",
                    headers=self.headers,
                    data=data
                ) as response:
                    return await response.json()
    
    async def process_multiple_documents(self, file_paths):
        """Process multiple documents concurrently"""
        tasks = [self.upload_document(path) for path in file_paths]
        results = await asyncio.gather(*tasks)
        return results

# Usage example
async def main():
    client = AsyncContractOCRClient("your-api-key")
    files = ["contract1.pdf", "contract2.pdf", "contract3.pdf"]
    results = await client.process_multiple_documents(files)
    print(json.dumps(results, indent=2))

asyncio.run(main())
'''
            }
        },
        "javascript": {
            "description": "JavaScript/Node.js client examples",
            "installation": "npm install axios form-data",
            "examples": {
                "node_client": '''
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

class ContractOCRClient {
    constructor(apiKey, baseUrl = 'https://api.contractocr.com/api/v1') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.headers = { 'X-API-Key': apiKey };
    }
    
    async uploadDocument(filePath) {
        const form = new FormData();
        form.append('file', fs.createReadStream(filePath));
        
        const response = await axios.post(
            `${this.baseUrl}/documents/upload`,
            form,
            {
                headers: {
                    ...this.headers,
                    ...form.getHeaders()
                }
            }
        );
        
        return response.data;
    }
    
    async getStatus(documentId) {
        const response = await axios.get(
            `${this.baseUrl}/documents/${documentId}/status`,
            { headers: this.headers }
        );
        return response.data;
    }
    
    async getResults(documentId) {
        const response = await axios.get(
            `${this.baseUrl}/documents/${documentId}/results`,
            { headers: this.headers }
        );
        return response.data;
    }
    
    async processDocument(filePath, timeout = 300000) {
        // Upload
        const uploadResult = await this.uploadDocument(filePath);
        const documentId = uploadResult.document_id;
        
        // Wait for completion
        const startTime = Date.now();
        while (Date.now() - startTime < timeout) {
            const status = await this.getStatus(documentId);
            
            if (status.status === 'completed') {
                return await this.getResults(documentId);
            } else if (status.status === 'failed') {
                throw new Error(`Processing failed: ${status.error_message}`);
            }
            
            await new Promise(resolve => setTimeout(resolve, 10000));
        }
        
        throw new Error('Processing timeout');
    }
}

// Usage example
async function main() {
    const client = new ContractOCRClient('your-api-key');
    try {
        const results = await client.processDocument('contract.pdf');
        console.log(JSON.stringify(results, null, 2));
    } catch (error) {
        console.error('Error:', error.message);
    }
}

main();
''',
                "browser_client": '''
// Browser-based client for web applications
class ContractOCRWebClient {
    constructor(apiKey, baseUrl = 'https://api.contractocr.com/api/v1') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.headers = { 'X-API-Key': apiKey };
    }
    
    async uploadDocument(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${this.baseUrl}/documents/upload`, {
            method: 'POST',
            headers: this.headers,
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    async getStatus(documentId) {
        const response = await fetch(
            `${this.baseUrl}/documents/${documentId}/status`,
            { headers: this.headers }
        );
        
        if (!response.ok) {
            throw new Error(`Status check failed: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    async processDocumentWithProgress(file, onProgress) {
        // Upload
        const uploadResult = await this.uploadDocument(file);
        const documentId = uploadResult.document_id;
        
        // Poll for progress
        return new Promise((resolve, reject) => {
            const checkStatus = async () => {
                try {
                    const status = await this.getStatus(documentId);
                    
                    if (onProgress) {
                        onProgress(status.progress, status.status);
                    }
                    
                    if (status.status === 'completed') {
                        const results = await this.getResults(documentId);
                        resolve(results);
                    } else if (status.status === 'failed') {
                        reject(new Error(`Processing failed: ${status.error_message}`));
                    } else {
                        setTimeout(checkStatus, 5000);
                    }
                } catch (error) {
                    reject(error);
                }
            };
            
            checkStatus();
        });
    }
}

// Usage example with file input
document.getElementById('fileInput').addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    const client = new ContractOCRWebClient('your-api-key');
    const progressBar = document.getElementById('progressBar');
    
    try {
        const results = await client.processDocumentWithProgress(
            file,
            (progress, status) => {
                progressBar.style.width = `${progress}%`;
                progressBar.textContent = `${status}: ${progress}%`;
            }
        );
        
        console.log('Processing complete:', results);
        displayResults(results);
    } catch (error) {
        console.error('Error:', error.message);
        alert(`Error: ${error.message}`);
    }
});
'''
            }
        },
        "csharp": {
            "description": "C# client examples for .NET applications",
            "installation": "Install-Package Newtonsoft.Json",
            "examples": {
                "basic_client": '''
using System;
using System.IO;
using System.Net.Http;
using System.Threading.Tasks;
using Newtonsoft.Json;

public class ContractOCRClient
{
    private readonly HttpClient _httpClient;
    private readonly string _baseUrl;
    
    public ContractOCRClient(string apiKey, string baseUrl = "https://api.contractocr.com/api/v1")
    {
        _httpClient = new HttpClient();
        _httpClient.DefaultRequestHeaders.Add("X-API-Key", apiKey);
        _baseUrl = baseUrl;
    }
    
    public async Task<UploadResponse> UploadDocumentAsync(string filePath)
    {
        using var form = new MultipartFormDataContent();
        using var fileStream = File.OpenRead(filePath);
        using var fileContent = new StreamContent(fileStream);
        
        fileContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("application/pdf");
        form.Add(fileContent, "file", Path.GetFileName(filePath));
        
        var response = await _httpClient.PostAsync($"{_baseUrl}/documents/upload", form);
        var content = await response.Content.ReadAsStringAsync();
        
        if (!response.IsSuccessStatusCode)
        {
            throw new Exception($"Upload failed: {content}");
        }
        
        return JsonConvert.DeserializeObject<UploadResponse>(content);
    }
    
    public async Task<StatusResponse> GetStatusAsync(string documentId)
    {
        var response = await _httpClient.GetAsync($"{_baseUrl}/documents/{documentId}/status");
        var content = await response.Content.ReadAsStringAsync();
        
        if (!response.IsSuccessStatusCode)
        {
            throw new Exception($"Status check failed: {content}");
        }
        
        return JsonConvert.DeserializeObject<StatusResponse>(content);
    }
    
    public async Task<ProcessingResult> ProcessDocumentAsync(string filePath, int timeoutSeconds = 300)
    {
        // Upload
        var uploadResult = await UploadDocumentAsync(filePath);
        var documentId = uploadResult.DocumentId;
        
        // Wait for completion
        var startTime = DateTime.UtcNow;
        while ((DateTime.UtcNow - startTime).TotalSeconds < timeoutSeconds)
        {
            var status = await GetStatusAsync(documentId);
            
            if (status.Status == "completed")
            {
                return await GetResultsAsync(documentId);
            }
            else if (status.Status == "failed")
            {
                throw new Exception($"Processing failed: {status.ErrorMessage}");
            }
            
            await Task.Delay(10000);
        }
        
        throw new TimeoutException("Processing timeout");
    }
}

// Data models
public class UploadResponse
{
    [JsonProperty("document_id")]
    public string DocumentId { get; set; }
    
    [JsonProperty("status")]
    public string Status { get; set; }
    
    [JsonProperty("message")]
    public string Message { get; set; }
}

public class StatusResponse
{
    [JsonProperty("document_id")]
    public string DocumentId { get; set; }
    
    [JsonProperty("status")]
    public string Status { get; set; }
    
    [JsonProperty("progress")]
    public int Progress { get; set; }
    
    [JsonProperty("error_message")]
    public string ErrorMessage { get; set; }
}

// Usage example
class Program
{
    static async Task Main(string[] args)
    {
        var client = new ContractOCRClient("your-api-key");
        
        try
        {
            var results = await client.ProcessDocumentAsync("contract.pdf");
            Console.WriteLine(JsonConvert.SerializeObject(results, Formatting.Indented));
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error: {ex.Message}");
        }
    }
}
'''
            }
        }
    }
    
    return examples


@router.get("/documentation", response_class=HTMLResponse, tags=["integration"])
async def get_complete_documentation():
    """
    Get complete API documentation as interactive HTML page
    
    Returns a comprehensive, styled HTML documentation page with examples,
    integration guides, and interactive elements for the Contract OCR API.
    """
    import os
    from pathlib import Path
    
    # Get the template file path
    template_path = Path(__file__).parent.parent.parent.parent / "templates" / "api_docs.html"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        # Fallback to basic HTML if template not found
        return HTMLResponse(content="""
        <html>
            <head><title>Contract OCR API Documentation</title></head>
            <body>
                <h1>Contract OCR API Documentation</h1>
                <p>Complete documentation is available at <a href="/docs">/docs</a> (Swagger UI) and <a href="/redoc">/redoc</a> (ReDoc).</p>
                <p>For integration examples, visit <a href="/api/v1/integration/copilot-studio/examples">/api/v1/integration/copilot-studio/examples</a></p>
            </body>
        </html>
        """)


@router.get("/integration-guide", response_class=HTMLResponse, tags=["integration"])
async def get_integration_guide():
    """
    Get comprehensive integration guide as HTML
    
    Returns a complete HTML guide for integrating the Contract OCR API
    with various platforms and frameworks.
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Contract OCR API - Integration Guide</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1, h2, h3 { color: #333; }
            h1 { border-bottom: 3px solid #007acc; padding-bottom: 10px; }
            h2 { color: #007acc; margin-top: 30px; }
            .code-block { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px; padding: 15px; margin: 15px 0; overflow-x: auto; }
            .highlight { background: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; margin: 15px 0; }
            .success { background: #d4edda; padding: 10px; border-left: 4px solid #28a745; margin: 15px 0; }
            .error { background: #f8d7da; padding: 10px; border-left: 4px solid #dc3545; margin: 15px 0; }
            .nav { background: #007acc; color: white; padding: 15px; margin: -30px -30px 30px -30px; border-radius: 8px 8px 0 0; }
            .nav a { color: white; text-decoration: none; margin-right: 20px; }
            .nav a:hover { text-decoration: underline; }
            table { width: 100%; border-collapse: collapse; margin: 15px 0; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background: #f8f9fa; font-weight: 600; }
            .endpoint { background: #e3f2fd; padding: 10px; border-radius: 4px; margin: 10px 0; }
            .method { display: inline-block; padding: 4px 8px; border-radius: 4px; font-weight: bold; color: white; margin-right: 10px; }
            .post { background: #28a745; }
            .get { background: #007acc; }
            .put { background: #ffc107; color: #333; }
            .delete { background: #dc3545; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="nav">
                <h1 style="margin: 0; border: none; padding: 0;">Contract OCR API - Integration Guide</h1>
                <p style="margin: 10px 0 0 0;">Complete guide for integrating contract OCR processing into your applications</p>
            </div>

            <h2>🚀 Quick Start</h2>
            <div class="highlight">
                <strong>Get started in 3 steps:</strong>
                <ol>
                    <li>Get your API key from the dashboard</li>
                    <li>Upload a PDF document</li>
                    <li>Retrieve the processed results</li>
                </ol>
            </div>

            <h2>📋 API Endpoints Overview</h2>
            <div class="endpoint">
                <span class="method post">POST</span>
                <strong>/api/v1/documents/upload</strong> - Upload document for processing
            </div>
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/v1/documents/{id}/status</strong> - Check processing status
            </div>
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/v1/documents/{id}/results</strong> - Get processing results
            </div>
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/v1/documents/history</strong> - Get processing history
            </div>

            <h2>🔐 Authentication</h2>
            <p>All API requests require an API key in the header:</p>
            <div class="code-block">
                <strong>Header:</strong> X-API-Key: your-api-key-here
            </div>

            <h2>📤 Document Upload</h2>
            <h3>Requirements</h3>
            <table>
                <tr><th>Property</th><th>Requirement</th></tr>
                <tr><td>File Format</td><td>PDF only</td></tr>
                <tr><td>File Size</td><td>Maximum 50MB</td></tr>
                <tr><td>Page Count</td><td>Up to 100 pages</td></tr>
                <tr><td>Content Type</td><td>multipart/form-data</td></tr>
            </table>

            <h3>Example Request</h3>
            <div class="code-block">
curl -X POST "https://api.contractocr.com/api/v1/documents/upload" \\
     -H "X-API-Key: your-api-key" \\
     -F "file=@contract.pdf"
            </div>

            <h3>Example Response</h3>
            <div class="code-block">
{
  "document_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "queued",
  "message": "Document uploaded successfully and queued for processing"
}
            </div>

            <h2>📊 Status Tracking</h2>
            <p>Processing status can be one of:</p>
            <table>
                <tr><th>Status</th><th>Description</th><th>Progress</th></tr>
                <tr><td>queued</td><td>Document is waiting to be processed</td><td>0%</td></tr>
                <tr><td>processing</td><td>OCR and text extraction in progress</td><td>1-99%</td></tr>
                <tr><td>completed</td><td>Processing finished successfully</td><td>100%</td></tr>
                <tr><td>failed</td><td>Processing failed with error</td><td>N/A</td></tr>
            </table>

            <h2>📄 Results Structure</h2>
            <p>Completed documents return structured data:</p>
            <div class="code-block">
{
  "document_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "progress": 100,
  "pages": [
    {
      "page_number": 1,
      "text_blocks": [
        {
          "text": "CONTRACT AGREEMENT",
          "confidence": 0.98,
          "bounding_box": {"x": 100, "y": 50, "width": 200, "height": 30},
          "is_title": true
        }
      ],
      "raw_text": "Full page text...",
      "normalized_text": "Cleaned and normalized text..."
    }
  ],
  "metadata": {
    "filename": "contract.pdf",
    "file_size": 1048576,
    "page_count": 5,
    "processing_time": 45.2,
    "ocr_confidence": 0.95
  },
  "legal_terms": ["agreement", "contract", "party"]
}
            </div>

            <h2>🔗 Microsoft Copilot Studio Integration</h2>
            <div class="success">
                <strong>Perfect for Copilot Studio!</strong> This API is optimized for Microsoft Copilot Studio integration with Power Automate flows.
            </div>

            <h3>Power Automate Flow Steps</h3>
            <ol>
                <li><strong>Trigger:</strong> Manual trigger or file upload</li>
                <li><strong>Upload Document:</strong> HTTP POST to /documents/upload</li>
                <li><strong>Wait for Processing:</strong> Loop checking status until completed</li>
                <li><strong>Get Results:</strong> HTTP GET to /documents/{id}/results</li>
                <li><strong>Process Results:</strong> Parse and use extracted text</li>
            </ol>

            <h3>Custom Connector Configuration</h3>
            <div class="code-block">
Host: api.contractocr.com
Base Path: /api/v1
Authentication: API Key (Header: X-API-Key)
            </div>

            <h2>⚠️ Error Handling</h2>
            <p>Common error responses:</p>
            <table>
                <tr><th>HTTP Code</th><th>Error Code</th><th>Description</th></tr>
                <tr><td>400</td><td>INVALID_FILE_FORMAT</td><td>File is not a valid PDF</td></tr>
                <tr><td>400</td><td>FILE_TOO_LARGE</td><td>File exceeds 50MB limit</td></tr>
                <tr><td>401</td><td>INVALID_API_KEY</td><td>API key is missing or invalid</td></tr>
                <tr><td>404</td><td>DOCUMENT_NOT_FOUND</td><td>Document ID not found</td></tr>
                <tr><td>429</td><td>RATE_LIMIT_EXCEEDED</td><td>Too many requests</td></tr>
            </table>

            <h2>🎯 Best Practices</h2>
            <div class="highlight">
                <ul>
                    <li><strong>Polling Interval:</strong> Check status every 10-30 seconds</li>
                    <li><strong>Timeout:</strong> Set reasonable timeouts (5-10 minutes for large documents)</li>
                    <li><strong>Error Handling:</strong> Always handle network errors and API errors</li>
                    <li><strong>File Validation:</strong> Validate PDF files before upload</li>
                    <li><strong>Rate Limiting:</strong> Respect rate limits (60 req/min, 1000 req/hour)</li>
                </ul>
            </div>

            <h2>📞 Webhook Notifications</h2>
            <p>Configure webhooks for real-time processing notifications:</p>
            <div class="code-block">
POST /api/v1/documents/{id}/webhook
{
  "url": "https://your-webhook-endpoint.com",
  "events": ["completed", "failed"]
}
            </div>

            <h2>🔧 Testing</h2>
            <p>Use our interactive documentation at <strong>/docs</strong> to test API endpoints directly in your browser.</p>

            <div class="success">
                <strong>Need Help?</strong> Contact our support team at support@contractocr.com or check our FAQ section.
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)