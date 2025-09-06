#!/usr/bin/env python3
"""
Instant-run version of the systematic review extractor.
Works with zero dependencies beyond standard library.
"""

import http.server
import socketserver
import json
import re
import os
from datetime import datetime
from pathlib import Path
import webbrowser
import threading
import time

# Create output directory
output_dir = Path("verified_extractions")
output_dir.mkdir(exist_ok=True)
(output_dir / "uploads").mkdir(exist_ok=True)

class ExtractionHandler(http.server.SimpleHTTPRequestHandler):
    """Simple HTTP handler for extraction API."""
    
    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/api/health':
            self.send_json({
                "status": "healthy",
                "mode": "minimal",
                "timestamp": datetime.now().isoformat()
            })
        elif self.path == '/api/templates':
            self.send_json({
                "medical_basic": {
                    "name": "Medical Basic",
                    "template": {
                        "sample_size": {
                            "patterns": [
                                r"n\s*=\s*(\d+)",
                                r"(\d+)\s*participants?",
                                r"(\d+)\s*subjects?",
                                r"enrolled\s+(\d+)"
                            ],
                            "hint": "Total number of participants",
                            "type": "integer"
                        },
                        "mean_age": {
                            "patterns": [
                                r"mean\s+age.*?(\d+\.?\d*)",
                                r"age.*?(\d+\.?\d*)\s*±",
                                r"(\d+\.?\d*)\s*years?\s*old"
                            ],
                            "hint": "Mean age of participants",
                            "type": "float"
                        },
                        "p_value": {
                            "patterns": [
                                r"p\s*[<=]\s*(0?\.\d+)",
                                r"P\s*value.*?(0?\.\d+)",
                                r"significance.*?(0?\.\d+)"
                            ],
                            "hint": "P-value for primary outcome",
                            "type": "float"
                        },
                        "effect_size": {
                            "patterns": [
                                r"Cohen's\s*d\s*=\s*(\d+\.?\d*)",
                                r"effect\s+size.*?(\d+\.?\d*)",
                                r"SMD\s*=\s*(\d+\.?\d*)"
                            ],
                            "hint": "Effect size",
                            "type": "float"
                        },
                        "confidence_interval": {
                            "patterns": [
                                r"95%?\s*CI\s*\[?([\d.-]+)[,\s]+([\d.-]+)\]?",
                                r"CI\s*\(([\d.-]+)[,\s]+([\d.-]+)\)",
                                r"\(([\d.-]+)\s+to\s+([\d.-]+)\)"
                            ],
                            "hint": "95% Confidence Interval",
                            "type": "string"
                        }
                    }
                }
            })
        elif self.path == '/':
            self.send_html()
        else:
            super().do_GET()
    
    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/api/extract':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data)
                text = data.get('text', '')
                template = data.get('template', {})
                
                # Simple extraction
                results = self.extract_simple(text, template)
                
                self.send_json({
                    "extractions": results,
                    "mode": "minimal",
                    "fields_found": len(results),
                    "fields_requested": len(template)
                })
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
        else:
            self.send_error(404)
    
    def extract_simple(self, text, template):
        """Simple regex extraction."""
        results = []
        
        for field_name, config in template.items():
            patterns = config.get("patterns", [])
            found = False
            
            for pattern in patterns:
                if found:
                    break
                try:
                    matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                    if matches:
                        # Get the first match
                        value = matches[0] if isinstance(matches[0], str) else matches[0][0]
                        
                        # Find context
                        match_obj = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                        if match_obj:
                            start = max(0, match_obj.start() - 100)
                            end = min(len(text), match_obj.end() + 100)
                            context = text[start:end]
                        else:
                            context = ""
                        
                        results.append({
                            "field_name": field_name,
                            "value": value,
                            "confidence": 0.7,  # Fixed confidence for simple mode
                            "page_number": 1,
                            "context": context,
                            "extraction_method": "regex",
                            "timestamp": datetime.now().isoformat(),
                            "pattern_used": pattern
                        })
                        found = True
                except Exception as e:
                    print(f"Pattern error: {e}")
                    continue
        
        return results
    
    def send_json(self, data, status=200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def send_html(self):
        """Send the main HTML interface."""
        html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Systematic Review Extractor - Instant Version</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <div class="container mx-auto px-4 py-8">
        <h1 class="text-3xl font-bold mb-2">Systematic Review Extractor</h1>
        <p class="text-gray-600 mb-8">Instant-run version (no dependencies required)</p>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Input Section -->
            <div class="bg-white rounded-lg shadow p-6">
                <h2 class="text-xl font-semibold mb-4">Input Text</h2>
                <textarea id="inputText" class="w-full h-64 p-3 border rounded-md" placeholder="Paste your PDF text here...

Example:
This randomized controlled trial enrolled n = 150 participants with a mean age of 45.2 ± 12.3 years. The primary outcome showed significant improvement with p < 0.001. The effect size was Cohen's d = 0.85."></textarea>
                
                <div class="mt-4">
                    <label class="block text-sm font-medium mb-2">Template</label>
                    <select id="template" class="w-full p-2 border rounded-md">
                        <option value="medical_basic">Medical Basic</option>
                    </select>
                </div>
                
                <button onclick="extract()" class="mt-4 w-full bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700">
                    Extract Data
                </button>
            </div>
            
            <!-- Results Section -->
            <div class="bg-white rounded-lg shadow p-6">
                <h2 class="text-xl font-semibold mb-4">Extracted Data</h2>
                <div id="results" class="space-y-3">
                    <p class="text-gray-500">No extractions yet. Click "Extract Data" to begin.</p>
                </div>
            </div>
        </div>
        
        <!-- Details Section -->
        <div id="details" class="mt-6 bg-white rounded-lg shadow p-6 hidden">
            <h3 class="text-lg font-semibold mb-3">Extraction Details</h3>
            <div id="detailsContent"></div>
        </div>
    </div>
    
    <script>
        let templates = {};
        let currentExtractions = [];
        
        // Load templates on startup
        async function loadTemplates() {
            try {
                const response = await fetch('/api/templates');
                templates = await response.json();
                console.log('Templates loaded:', templates);
            } catch (error) {
                console.error('Failed to load templates:', error);
            }
        }
        
        async function extract() {
            const text = document.getElementById('inputText').value;
            const templateName = document.getElementById('template').value;
            
            if (!text) {
                alert('Please enter some text to extract from');
                return;
            }
            
            const template = templates[templateName]?.template || templates[templateName];
            
            try {
                const response = await fetch('/api/extract', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        text: text,
                        template: template
                    })
                });
                
                const data = await response.json();
                currentExtractions = data.extractions;
                displayResults(data.extractions);
                
                if (data.extractions.length === 0) {
                    alert('No data could be extracted. Try adjusting the text or template.');
                }
            } catch (error) {
                console.error('Extraction failed:', error);
                alert('Extraction failed: ' + error.message);
            }
        }
        
        function displayResults(extractions) {
            const resultsDiv = document.getElementById('results');
            
            if (extractions.length === 0) {
                resultsDiv.innerHTML = '<p class="text-gray-500">No data extracted</p>';
                return;
            }
            
            resultsDiv.innerHTML = extractions.map((ext, idx) => `
                <div class="border rounded p-3 cursor-pointer hover:bg-gray-50" onclick="showDetails(${idx})">
                    <div class="flex justify-between items-start">
                        <div>
                            <div class="font-semibold">${ext.field_name}</div>
                            <div class="text-lg text-blue-600">${ext.value}</div>
                        </div>
                        <div class="text-sm text-gray-500">
                            ${Math.round(ext.confidence * 100)}%
                        </div>
                    </div>
                </div>
            `).join('');
            
            // Show summary
            const summary = document.createElement('div');
            summary.className = 'mt-4 p-3 bg-green-50 border border-green-200 rounded';
            summary.innerHTML = `
                <div class="text-green-800">
                    ✓ Extracted ${extractions.length} fields successfully
                </div>
            `;
            resultsDiv.appendChild(summary);
        }
        
        function showDetails(idx) {
            const ext = currentExtractions[idx];
            const detailsDiv = document.getElementById('details');
            const detailsContent = document.getElementById('detailsContent');
            
            detailsContent.innerHTML = `
                <div class="space-y-3">
                    <div>
                        <span class="font-semibold">Field:</span> ${ext.field_name}
                    </div>
                    <div>
                        <span class="font-semibold">Value:</span> ${ext.value}
                    </div>
                    <div>
                        <span class="font-semibold">Confidence:</span> ${Math.round(ext.confidence * 100)}%
                    </div>
                    <div>
                        <span class="font-semibold">Pattern Used:</span> 
                        <code class="text-sm bg-gray-100 p-1 rounded">${ext.pattern_used || 'N/A'}</code>
                    </div>
                    <div>
                        <span class="font-semibold">Context:</span>
                        <div class="mt-1 p-2 bg-gray-50 rounded text-sm">
                            ${ext.context || 'No context available'}
                        </div>
                    </div>
                </div>
            `;
            
            detailsDiv.classList.remove('hidden');
        }
        
        // Load templates when page loads
        loadTemplates();
        
        // Check API health
        fetch('/api/health')
            .then(r => r.json())
            .then(data => console.log('API Status:', data))
            .catch(e => console.error('API Error:', e));
    </script>
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

def start_server(port=8000):
    """Start the HTTP server."""
    with socketserver.TCPServer(("", port), ExtractionHandler) as httpd:
        print(f"Server running at http://localhost:{port}")
        print(f"Open your browser to: http://localhost:{port}")
        httpd.serve_forever()

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Systematic Review Extractor - Instant Run")
    print("=" * 60)
    print("\nNo dependencies required! Running with Python standard library only.")
    print("\nFeatures available:")
    print("  ✓ Web interface")
    print("  ✓ Regex extraction")
    print("  ✓ Medical templates")
    print("  ✓ REST API")
    print("\nStarting server...")
    print("-" * 60)
    
    # Start server in a thread
    server_thread = threading.Thread(target=lambda: start_server(8000))
    server_thread.daemon = True
    server_thread.start()
    
    # Wait a moment for server to start
    time.sleep(1)
    
    # Try to open browser
    try:
        webbrowser.open('http://localhost:8000')
        print("\n✅ Browser opened automatically")
    except:
        print("\n⚠️  Please open your browser to: http://localhost:8000")
    
    print("\nPress Ctrl+C to stop the server\n")
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nServer stopped. Goodbye!")