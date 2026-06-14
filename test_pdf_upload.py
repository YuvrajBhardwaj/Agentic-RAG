#!/usr/bin/env python
"""
Test script for PDF upload functionality
Creates a sample PDF and uploads it to the Agentic RAG API
"""

import requests
import os
import sys

# Try to import reportlab for PDF creation
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

API_URL = "http://localhost:8000"

def create_sample_pdf(filename="sample.pdf", title="Sample Document"):
    """Create a simple PDF for testing"""
    if not HAS_REPORTLAB:
        print("reportlab not installed. Create a PDF manually and test with it.")
        return None
    
    try:
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter
        
        c.setFont("Helvetica-Bold", 24)
        c.drawString(50, height - 50, title)
        
        c.setFont("Helvetica", 12)
        y_pos = height - 100
        
        content = [
            "This is a test PDF document for the Agentic RAG system.",
            "",
            "Key Features:",
            "- Semantic search using embeddings",
            "- Vector indexing with FAISS",
            "- Real-time LLM-powered responses",
            "",
            "This PDF is indexed and searchable via the API."
        ]
        
        for line in content:
            c.drawString(50, y_pos, line)
            y_pos -= 20
        
        c.save()
        print(f"✓ Created sample PDF: {filename}")
        return filename
    
    except Exception as e:
        print(f"✗ Could not create PDF: {e}")
        return None

def test_pdf_upload(pdf_file):
    """Test the PDF upload endpoint"""
    print(f"\n[TEST] PDF Upload to {API_URL}/upload-pdf")
    print("=" * 60)
    
    if not os.path.exists(pdf_file):
        print(f"✗ PDF file not found: {pdf_file}")
        return False
    
    try:
        with open(pdf_file, 'rb') as f:
            files = {'files': (pdf_file, f, 'application/pdf')}
            
            print(f"Uploading: {pdf_file}")
            response = requests.post(f"{API_URL}/upload-pdf", files=files, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✓ Upload Successful!")
                print(f"  Total files: {data['total']}")
                print(f"  Successful: {data['successful']}")
                print(f"  Failed: {data['failed']}")
                
                for result in data['results']:
                    status_icon = "✓" if result['status'] == 'success' else "✗"
                    filename = result['filename']
                    
                    if result['status'] == 'success':
                        pages = result.get('pages', 0)
                        doc_id = result.get('doc_id', 'N/A')
                        print(f"\n  {status_icon} {filename}")
                        print(f"     Pages: {pages}")
                        print(f"     Doc ID: {doc_id}")
                        print(f"     Text Length: {result.get('text_length', 0)} chars")
                    else:
                        error = result.get('error', 'Unknown error')
                        print(f"\n  {status_icon} {filename}")
                        print(f"     Error: {error}")
                
                return data['successful'] > 0
            
            else:
                print(f"✗ Upload failed with status {response.status_code}")
                print(f"  Response: {response.text}")
                return False
    
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to API at {API_URL}")
        print("  Make sure the FastAPI server is running:")
        print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        return False
    
    except Exception as e:
        print(f"✗ Error during upload: {e}")
        return False

def test_query_after_upload():
    """Test querying PDF content after upload"""
    print(f"\n[TEST] Query PDF Content")
    print("=" * 60)
    
    try:
        query_data = {"query": "What is in this document?", "top_k": 2}
        
        print("Querying: 'What is in this document?'")
        response = requests.post(f"{API_URL}/query", json=query_data, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ Query Successful!")
            print(f"  Answer (first 300 chars):\n  {data['answer'][:300]}...")
            print(f"\n  Sources: {len(data['sources'])} documents retrieved")
            for i, source in enumerate(data['sources'], 1):
                meta = source.get('meta', {})
                print(f"    {i}. {source['id']} ({meta.get('filename', 'N/A')})")
            
            return True
        else:
            print(f"✗ Query failed: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"✗ Query error: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("AGENTIC RAG - PDF UPLOAD TEST")
    print("="*60)
    
    # Create sample PDF
    pdf_file = "test_sample.pdf"
    
    if not os.path.exists(pdf_file):
        print("\n[1] Creating Sample PDF...")
        created = create_sample_pdf(pdf_file)
        if not created and not HAS_REPORTLAB:
            print("\nℹ reportlab not available. Install with:")
            print("  pip install reportlab")
            print("\nOr provide your own PDF file and run:")
            print("  python test_pdf.py /path/to/your/file.pdf")
            sys.exit(1)
    else:
        print(f"\n[1] Using existing PDF: {pdf_file}")
    
    # Test upload
    print("\n[2] Testing PDF Upload...")
    upload_success = test_pdf_upload(pdf_file)
    
    if not upload_success:
        print("\n✗ PDF upload test failed")
        sys.exit(1)
    
    # Test query
    print("\n[3] Testing Query on PDF Content...")
    query_success = test_query_after_upload()
    
    print("\n" + "="*60)
    if upload_success and query_success:
        print("✓ ALL TESTS PASSED!")
        print("  PDF upload and query features are working correctly")
    else:
        print("⚠ Some tests failed")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
