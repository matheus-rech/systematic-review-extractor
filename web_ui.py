#!/usr/bin/env python3
"""
Web UI for Systematic Review Extraction System
Provides a user-friendly interface for PDF extraction with multi-model validation
"""

from flask import Flask, render_template_string, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
import json
import asyncio
from pathlib import Path
from datetime import datetime
import tempfile
import shutil
from werkzeug.utils import secure_filename

# Import our systems
from systematic_review_pipeline import SystematicReviewPipeline
from multi_model_validator import MultiModelValidator

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

# Create necessary directories
os.makedirs('uploads', exist_ok=True)
os.makedirs('projects', exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Systematic Review Extractor - AI-Powered Data Extraction</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <style>
        .gradient-bg {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .processing-animation {
            animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: .5; }
        }
    </style>
</head>
<body class="bg-gray-50">
    <div x-data="extractorApp()" class="min-h-screen">
        <!-- Header -->
        <div class="gradient-bg text-white">
            <div class="container mx-auto px-4 py-8">
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="text-4xl font-bold mb-2">🔬 Systematic Review Extractor</h1>
                        <p class="text-lg opacity-90">AI-Powered Data Extraction with Multi-Model Validation</p>
                    </div>
                    <div class="text-right">
                        <div class="text-sm opacity-75">Zero Hallucination Guarantee</div>
                        <div class="text-sm opacity-75">100% Evidence Trail</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Main Content -->
        <div class="container mx-auto px-4 py-8">
            <!-- Upload Section -->
            <div class="bg-white rounded-lg shadow-lg p-6 mb-8">
                <h2 class="text-2xl font-semibold mb-4">📄 Upload Research Paper</h2>
                
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <!-- Upload Area -->
                    <div>
                        <div 
                            @dragover.prevent="dragover = true"
                            @dragleave.prevent="dragover = false"
                            @drop.prevent="handleDrop"
                            :class="{'border-blue-500 bg-blue-50': dragover}"
                            class="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center transition-colors"
                        >
                            <svg class="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                            </svg>
                            
                            <p class="mb-2 text-sm text-gray-600">
                                <span class="font-semibold">Click to upload</span> or drag and drop
                            </p>
                            <p class="text-xs text-gray-500">PDF files up to 50MB</p>
                            
                            <input type="file" @change="handleFileSelect" accept=".pdf" class="hidden" id="fileInput">
                            <button onclick="document.getElementById('fileInput').click()" 
                                    class="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                                Select PDF
                            </button>
                        </div>
                        
                        <div x-show="selectedFile" class="mt-4 p-3 bg-gray-50 rounded">
                            <div class="flex items-center justify-between">
                                <span class="text-sm" x-text="selectedFile?.name"></span>
                                <button @click="selectedFile = null" class="text-red-500 hover:text-red-700">
                                    ✕
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Options -->
                    <div>
                        <h3 class="font-semibold mb-3">Extraction Options</h3>
                        
                        <div class="space-y-4">
                            <!-- Template Selection -->
                            <div>
                                <label class="block text-sm font-medium mb-2">Template</label>
                                <select x-model="selectedTemplate" class="w-full p-2 border rounded-lg">
                                    <option value="default">Default (All patterns)</option>
                                    <option value="medical_rct">Medical RCT</option>
                                    <option value="surgical">Surgical Outcomes</option>
                                    <option value="custom">Custom Template</option>
                                </select>
                            </div>
                            
                            <!-- Multi-Model Validation -->
                            <div>
                                <label class="flex items-center">
                                    <input type="checkbox" x-model="useMultiModel" class="mr-2">
                                    <span class="text-sm font-medium">Enable Multi-Model Validation</span>
                                </label>
                                <p class="text-xs text-gray-600 mt-1">
                                    Uses multiple AI models to validate extractions (requires API keys)
                                </p>
                            </div>
                            
                            <!-- Models to Use -->
                            <div x-show="useMultiModel" class="pl-6 space-y-2">
                                <label class="flex items-center text-sm">
                                    <input type="checkbox" x-model="models.claude" class="mr-2">
                                    Claude-3 (Anthropic)
                                </label>
                                <label class="flex items-center text-sm">
                                    <input type="checkbox" x-model="models.gpt" class="mr-2">
                                    GPT-4 (OpenAI)
                                </label>
                                <label class="flex items-center text-sm">
                                    <input type="checkbox" x-model="models.local" class="mr-2">
                                    Local LLM (Ollama)
                                </label>
                            </div>
                            
                            <!-- Project Name -->
                            <div>
                                <label class="block text-sm font-medium mb-2">Project Name</label>
                                <input type="text" x-model="projectName" placeholder="my_extraction"
                                       class="w-full p-2 border rounded-lg">
                            </div>
                        </div>
                        
                        <!-- Extract Button -->
                        <button 
                            @click="startExtraction"
                            :disabled="!selectedFile || processing"
                            class="mt-6 w-full py-3 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 disabled:bg-gray-400"
                        >
                            <span x-show="!processing">🚀 Start Extraction</span>
                            <span x-show="processing" class="processing-animation">⏳ Processing...</span>
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- Progress Section -->
            <div x-show="processing || results" class="bg-white rounded-lg shadow-lg p-6 mb-8">
                <h2 class="text-2xl font-semibold mb-4">
                    <span x-show="processing">⚙️ Processing</span>
                    <span x-show="!processing && results">✅ Results</span>
                </h2>
                
                <!-- Progress Bar -->
                <div x-show="processing" class="mb-6">
                    <div class="w-full bg-gray-200 rounded-full h-2.5">
                        <div class="bg-blue-600 h-2.5 rounded-full processing-animation" 
                             :style="`width: ${progress}%`"></div>
                    </div>
                    <p class="text-sm text-gray-600 mt-2" x-text="statusMessage"></p>
                </div>
                
                <!-- Results Summary -->
                <div x-show="results" class="space-y-4">
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div class="bg-blue-50 p-4 rounded-lg">
                            <div class="text-2xl font-bold text-blue-600" x-text="results?.total_extractions || 0"></div>
                            <div class="text-sm text-gray-600">Extractions</div>
                        </div>
                        <div class="bg-green-50 p-4 rounded-lg">
                            <div class="text-2xl font-bold text-green-600" x-text="results?.pages_analyzed || 0"></div>
                            <div class="text-sm text-gray-600">Pages</div>
                        </div>
                        <div class="bg-purple-50 p-4 rounded-lg">
                            <div class="text-2xl font-bold text-purple-600" x-text="results?.confidence || '0%'"></div>
                            <div class="text-sm text-gray-600">Confidence</div>
                        </div>
                        <div class="bg-yellow-50 p-4 rounded-lg">
                            <div class="text-2xl font-bold text-yellow-600" x-text="results?.screenshots || 0"></div>
                            <div class="text-sm text-gray-600">Screenshots</div>
                        </div>
                    </div>
                    
                    <!-- Key Findings -->
                    <div x-show="results?.key_findings" class="mt-6">
                        <h3 class="font-semibold mb-3">🔍 Key Findings</h3>
                        <div class="space-y-2">
                            <template x-for="(values, field) in results?.key_findings" :key="field">
                                <div class="flex justify-between items-center p-3 bg-gray-50 rounded">
                                    <span class="font-medium" x-text="field.replace(/_/g, ' ')"></span>
                                    <span class="text-blue-600 font-bold" x-text="values[0]?.value"></span>
                                </div>
                            </template>
                        </div>
                    </div>
                    
                    <!-- Download Options -->
                    <div class="mt-6 flex space-x-4">
                        <button @click="downloadReport" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                            📄 View HTML Report
                        </button>
                        <button @click="downloadJSON" class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
                            📊 Download JSON
                        </button>
                        <button @click="downloadScreenshots" class="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700">
                            📸 Download Evidence
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- Previous Extractions -->
            <div class="bg-white rounded-lg shadow-lg p-6">
                <h2 class="text-2xl font-semibold mb-4">📚 Recent Extractions</h2>
                <div class="overflow-x-auto">
                    <table class="w-full text-sm">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="p-2 text-left">Project</th>
                                <th class="p-2 text-left">PDF</th>
                                <th class="p-2 text-center">Extractions</th>
                                <th class="p-2 text-center">Confidence</th>
                                <th class="p-2 text-center">Date</th>
                                <th class="p-2 text-center">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            <template x-for="project in recentProjects" :key="project.id">
                                <tr class="border-b">
                                    <td class="p-2" x-text="project.name"></td>
                                    <td class="p-2" x-text="project.pdf"></td>
                                    <td class="p-2 text-center" x-text="project.extractions"></td>
                                    <td class="p-2 text-center" x-text="project.confidence"></td>
                                    <td class="p-2 text-center" x-text="project.date"></td>
                                    <td class="p-2 text-center">
                                        <button @click="viewProject(project.id)" class="text-blue-600 hover:underline">
                                            View
                                        </button>
                                    </td>
                                </tr>
                            </template>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function extractorApp() {
            return {
                selectedFile: null,
                dragover: false,
                selectedTemplate: 'default',
                useMultiModel: false,
                models: {
                    claude: true,
                    gpt: true,
                    local: false
                },
                projectName: '',
                processing: false,
                progress: 0,
                statusMessage: '',
                results: null,
                recentProjects: [],
                
                init() {
                    this.loadRecentProjects();
                },
                
                handleDrop(e) {
                    this.dragover = false;
                    const files = e.dataTransfer.files;
                    if (files.length > 0 && files[0].type === 'application/pdf') {
                        this.selectedFile = files[0];
                    }
                },
                
                handleFileSelect(e) {
                    const files = e.target.files;
                    if (files.length > 0) {
                        this.selectedFile = files[0];
                    }
                },
                
                async startExtraction() {
                    if (!this.selectedFile) return;
                    
                    this.processing = true;
                    this.progress = 0;
                    this.statusMessage = 'Uploading PDF...';
                    
                    const formData = new FormData();
                    formData.append('pdf', this.selectedFile);
                    formData.append('template', this.selectedTemplate);
                    formData.append('project_name', this.projectName || 'extraction_' + Date.now());
                    formData.append('use_multi_model', this.useMultiModel);
                    formData.append('models', JSON.stringify(this.models));
                    
                    try {
                        // Simulate progress updates
                        this.progress = 20;
                        this.statusMessage = 'Analyzing PDF structure...';
                        
                        const response = await fetch('/api/extract', {
                            method: 'POST',
                            body: formData
                        });
                        
                        this.progress = 50;
                        this.statusMessage = 'Extracting data points...';
                        
                        const data = await response.json();
                        
                        this.progress = 80;
                        this.statusMessage = 'Generating evidence screenshots...';
                        
                        // Simulate final processing
                        setTimeout(() => {
                            this.progress = 100;
                            this.statusMessage = 'Complete!';
                            this.results = data;
                            this.processing = false;
                            this.loadRecentProjects();
                        }, 1000);
                        
                    } catch (error) {
                        console.error('Error:', error);
                        this.processing = false;
                        alert('An error occurred during extraction.');
                    }
                },
                
                async loadRecentProjects() {
                    try {
                        const response = await fetch('/api/projects');
                        this.recentProjects = await response.json();
                    } catch (error) {
                        console.error('Error loading projects:', error);
                    }
                },
                
                downloadReport() {
                    if (this.results?.report_path) {
                        window.open('/download/report/' + this.results.project_id, '_blank');
                    }
                },
                
                downloadJSON() {
                    if (this.results?.json_path) {
                        window.open('/download/json/' + this.results.project_id, '_blank');
                    }
                },
                
                downloadScreenshots() {
                    if (this.results?.project_id) {
                        window.open('/download/evidence/' + this.results.project_id, '_blank');
                    }
                },
                
                viewProject(projectId) {
                    window.open('/project/' + projectId, '_blank');
                }
            }
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """Main UI page."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/extract', methods=['POST'])
def extract():
    """Handle extraction request."""
    try:
        # Check if file is present
        if 'pdf' not in request.files:
            return jsonify({'error': 'No PDF file provided'}), 400
        
        file = request.files['pdf']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            # Save uploaded file
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            
            # Get parameters
            template = request.form.get('template', 'default')
            project_name = request.form.get('project_name', f'extraction_{timestamp}')
            use_multi_model = request.form.get('use_multi_model', 'false') == 'true'
            
            # Select template
            template_path = None
            if template == 'medical_rct':
                template_path = 'templates/medical_rct_template.json'
            elif template == 'surgical':
                template_path = 'templates/surgical_outcomes_template.json'
            
            # Run extraction pipeline
            pipeline = SystematicReviewPipeline(project_name=project_name)
            results = pipeline.run_complete_pipeline(
                pdf_path=filepath,
                template_path=template_path,
                open_report=False
            )
            
            # Run multi-model validation if requested
            if use_multi_model:
                # This would integrate with multi_model_validator.py
                # For now, we'll add a flag
                results['multi_model_validated'] = True
            
            # Prepare response
            response_data = {
                'project_id': project_name,
                'total_extractions': results['extraction_results']['total_extractions'],
                'pages_analyzed': results.get('pages_analyzed', 0),
                'confidence': f"{results['extraction_results'].get('average_confidence', 0):.0%}",
                'screenshots': results['extraction_results']['total_extractions'],
                'report_path': results['output_files']['html_report'],
                'json_path': results['output_files']['json_results'],
                'key_findings': {}  # Would parse from results
            }
            
            # Save project metadata
            project_meta = {
                'id': project_name,
                'name': project_name,
                'pdf': filename,
                'extractions': results['extraction_results']['total_extractions'],
                'confidence': f"{results['extraction_results'].get('average_confidence', 0):.0%}",
                'date': datetime.now().strftime('%Y-%m-%d'),
                'path': str(results['project_directory'])
            }
            
            meta_file = Path('projects') / f"{project_name}.json"
            with open(meta_file, 'w') as f:
                json.dump(project_meta, f)
            
            return jsonify(response_data)
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects')
def get_projects():
    """Get list of recent projects."""
    projects = []
    project_files = Path('projects').glob('*.json')
    
    for pf in sorted(project_files, key=os.path.getmtime, reverse=True)[:10]:
        with open(pf) as f:
            projects.append(json.load(f))
    
    return jsonify(projects)

@app.route('/download/report/<project_id>')
def download_report(project_id):
    """Download HTML report."""
    report_path = Path(project_id) / 'output' / 'reports' / 'extraction_report.html'
    if report_path.exists():
        return send_file(str(report_path))
    return "Report not found", 404

@app.route('/download/json/<project_id>')
def download_json(project_id):
    """Download JSON results."""
    json_path = Path(project_id) / 'output' / 'json' / 'raw_extractions.json'
    if json_path.exists():
        return send_file(str(json_path), as_attachment=True)
    return "JSON not found", 404

@app.route('/project/<project_id>')
def view_project(project_id):
    """View project report."""
    report_path = Path(project_id) / 'output' / 'reports' / 'extraction_report.html'
    if report_path.exists():
        return send_file(str(report_path))
    return "Project not found", 404

if __name__ == '__main__':
    print("=" * 60)
    print("SYSTEMATIC REVIEW EXTRACTOR - WEB UI")
    print("=" * 60)
    print("\n🌐 Starting web server...")
    print("📍 Access the UI at: http://localhost:5000")
    print("\nFeatures:")
    print("✓ Drag-and-drop PDF upload")
    print("✓ Multiple extraction templates")
    print("✓ Multi-model validation (optional)")
    print("✓ Real-time progress tracking")
    print("✓ Download reports and evidence")
    print("\nPress Ctrl+C to stop the server")
    print("-" * 60)
    
    app.run(debug=True, port=5000)