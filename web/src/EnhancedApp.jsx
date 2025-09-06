import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

function EnhancedApp() {
  // State management
  const [serverUrl, setServerUrl] = useState('http://localhost:8000');
  const [activeTab, setActiveTab] = useState('extract');
  const [pdfFiles, setPdfFiles] = useState([]);
  const [template, setTemplate] = useState(null);
  const [templateLibrary, setTemplateLibrary] = useState({});
  const [extractions, setExtractions] = useState([]);
  const [selectedExtraction, setSelectedExtraction] = useState(null);
  const [statuses, setStatuses] = useState({});
  const [notes, setNotes] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [minConfidence, setMinConfidence] = useState(0);
  const [jobs, setJobs] = useState([]);
  const [currentJob, setCurrentJob] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [similarExtractions, setSimilarExtractions] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [useLLM, setUseLLM] = useState(true);
  const [useOCR, setUseOCR] = useState(false);
  const [useMedicalAgents, setUseMedicalAgents] = useState(true);
  
  // WebSocket for real-time updates
  const ws = useRef(null);
  
  // Initialize WebSocket connection
  useEffect(() => {
    ws.current = new WebSocket(`ws://localhost:8000/ws`);
    
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.job_id && data.status) {
        setJobs(prev => prev.map(job => 
          job.job_id === data.job_id 
            ? { ...job, status: data.status, progress: data.progress || job.progress }
            : job
        ));
        
        if (data.status === 'completed' && currentJob?.job_id === data.job_id) {
          fetchJobResults(data.job_id);
        }
      }
    };
    
    return () => {
      ws.current?.close();
    };
  }, [currentJob]);
  
  // Load template library on mount
  useEffect(() => {
    fetchTemplateLibrary();
    fetchStatistics();
  }, []);
  
  const fetchTemplateLibrary = async () => {
    try {
      const response = await axios.get(`${serverUrl}/api/v2/templates/library`);
      setTemplateLibrary(response.data);
    } catch (error) {
      console.error('Failed to fetch template library:', error);
    }
  };
  
  const fetchStatistics = async () => {
    try {
      const response = await axios.get(`${serverUrl}/api/v2/statistics`);
      setStatistics(response.data);
    } catch (error) {
      console.error('Failed to fetch statistics:', error);
    }
  };
  
  const fetchJobResults = async (jobId) => {
    try {
      const response = await axios.get(`${serverUrl}/api/v2/jobs/${jobId}`);
      if (response.data.status === 'completed' && response.data.results) {
        // Flatten results from all PDFs
        const allExtractions = [];
        Object.entries(response.data.results).forEach(([pdfPath, exts]) => {
          exts.forEach(ext => {
            allExtractions.push({ ...ext, source_pdf: pdfPath });
          });
        });
        setExtractions(allExtractions);
        setIsProcessing(false);
      }
    } catch (error) {
      console.error('Failed to fetch job results:', error);
      setIsProcessing(false);
    }
  };
  
  const handleBatchExtraction = async () => {
    if (pdfFiles.length === 0 || !template) {
      alert('Please select PDFs and a template');
      return;
    }
    
    setIsProcessing(true);
    
    // Upload PDFs first
    const uploadedPaths = [];
    for (const file of pdfFiles) {
      const formData = new FormData();
      formData.append('file', file);
      
      try {
        // This would need an upload endpoint
        uploadedPaths.push(`/uploads/${file.name}`);
      } catch (error) {
        console.error('Upload failed:', error);
      }
    }
    
    // Submit batch job
    try {
      const response = await axios.post(`${serverUrl}/api/v2/extract/batch`, {
        pdf_paths: uploadedPaths,
        template: template,
        use_llm: useLLM,
        use_ocr: useOCR,
        use_medical_agents: useMedicalAgents,
        batch_size: 5
      });
      
      const newJob = {
        job_id: response.data.job_id,
        status: 'pending',
        progress: 0,
        pdf_count: pdfFiles.length
      };
      
      setJobs(prev => [...prev, newJob]);
      setCurrentJob(newJob);
      
    } catch (error) {
      console.error('Batch extraction failed:', error);
      setIsProcessing(false);
    }
  };
  
  const handleSingleExtraction = async () => {
    if (pdfFiles.length !== 1 || !template) {
      alert('Please select one PDF and a template');
      return;
    }
    
    setIsProcessing(true);
    
    const formData = new FormData();
    formData.append('pdf_file', pdfFiles[0]);
    formData.append('template_file', new Blob([JSON.stringify(template)], { type: 'application/json' }));
    
    try {
      const response = await axios.post(
        `${serverUrl}/api/v2/extract/single?use_llm=${useLLM}&use_ocr=${useOCR}`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      
      setExtractions(response.data.extractions);
      setIsProcessing(false);
      
      // Show statistics
      if (response.data.statistics) {
        alert(`Extraction complete! 
          Fields extracted: ${response.data.statistics.extracted_fields}/${response.data.statistics.total_fields}
          LLM validated: ${response.data.statistics.llm_validated}
          Average confidence: ${(response.data.statistics.avg_confidence * 100).toFixed(1)}%`);
      }
      
    } catch (error) {
      console.error('Extraction failed:', error);
      setIsProcessing(false);
    }
  };
  
  const searchSimilar = async (extraction) => {
    try {
      const response = await axios.post(`${serverUrl}/api/v2/search/similar`, {
        field_name: extraction.field_name,
        value: extraction.value,
        limit: 5
      });
      setSimilarExtractions(response.data.similar_extractions);
    } catch (error) {
      console.error('Similar search failed:', error);
    }
  };
  
  const submitFeedback = async (extraction, decision, notes) => {
    try {
      await axios.post(`${serverUrl}/api/v2/feedback`, {
        extraction_id: extraction.embedding_id || extraction.verification_hash,
        field_name: extraction.field_name,
        decision: decision,
        notes: notes
      });
      
      // Update local state
      const idx = extractions.indexOf(extraction);
      setStatuses(prev => ({ ...prev, [idx]: decision }));
      setNotes(prev => ({ ...prev, [idx]: notes }));
      
    } catch (error) {
      console.error('Feedback submission failed:', error);
    }
  };
  
  // Filter extractions
  const filteredExtractions = extractions.filter((ext, idx) => {
    const matchesSearch = 
      ext.field_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(ext.value).toLowerCase().includes(searchTerm.toLowerCase());
    const decision = statuses[idx] || 'pending';
    const matchesStatus = statusFilter === 'all' || decision === statusFilter;
    const matchesConf = ext.confidence >= minConfidence;
    return matchesSearch && matchesStatus && matchesConf;
  });
  
  // Calculate progress
  const total = extractions.length;
  const verifiedCount = Object.values(statuses).filter(s => s === 'verified').length;
  const progress = total ? Math.round((verifiedCount / total) * 100) : 0;
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                AI-Enhanced Systematic Review Extractor
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                Powered by Claude AI, Medical Agents, and Vector Search
              </p>
            </div>
            <div className="flex items-center space-x-4">
              {statistics && (
                <div className="text-sm text-gray-600">
                  <span className="font-semibold">{statistics.total_extractions}</span> extractions
                  {statistics.models_available.llm && (
                    <span className="ml-2 px-2 py-1 bg-green-100 text-green-800 rounded">
                      LLM Active
                    </span>
                  )}
                  {statistics.models_available.medical_agents && (
                    <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 rounded">
                      Medical AI
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </header>
      
      {/* Tab Navigation */}
      <div className="bg-white border-b">
        <div className="px-6">
          <nav className="flex space-x-8">
            {['extract', 'review', 'templates', 'jobs'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-3 px-1 border-b-2 font-medium text-sm capitalize ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab}
              </button>
            ))}
          </nav>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="px-6 py-6">
        {activeTab === 'extract' && (
          <div className="space-y-6">
            {/* File Upload */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Upload Documents</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    PDF Files ({pdfFiles.length} selected)
                  </label>
                  <input
                    type="file"
                    multiple
                    accept=".pdf"
                    onChange={(e) => setPdfFiles(Array.from(e.target.files))}
                    className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Extraction Template
                  </label>
                  <div className="flex space-x-2">
                    <select
                      className="flex-1 rounded-md border-gray-300 shadow-sm"
                      onChange={(e) => {
                        const selectedTemplate = templateLibrary[e.target.value];
                        if (selectedTemplate) {
                          setTemplate(selectedTemplate.template);
                        }
                      }}
                    >
                      <option value="">Select a template...</option>
                      {Object.entries(templateLibrary).map(([key, value]) => (
                        <option key={key} value={key}>
                          {value.name} - {value.description}
                        </option>
                      ))}
                    </select>
                    <button
                      className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
                      onClick={() => setActiveTab('templates')}
                    >
                      Build Custom
                    </button>
                  </div>
                </div>
                
                {/* AI Options */}
                <div className="border-t pt-4">
                  <h3 className="text-sm font-medium text-gray-700 mb-3">AI Enhancement Options</h3>
                  <div className="space-y-2">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={useLLM}
                        onChange={(e) => setUseLLM(e.target.checked)}
                        className="rounded text-blue-600"
                      />
                      <span className="ml-2 text-sm">Use Claude AI for intelligent extraction</span>
                    </label>
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={useOCR}
                        onChange={(e) => setUseOCR(e.target.checked)}
                        className="rounded text-blue-600"
                      />
                      <span className="ml-2 text-sm">Enable OCR for scanned PDFs</span>
                    </label>
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={useMedicalAgents}
                        onChange={(e) => setUseMedicalAgents(e.target.checked)}
                        className="rounded text-blue-600"
                      />
                      <span className="ml-2 text-sm">Use Medical AI Agents (92% accuracy)</span>
                    </label>
                  </div>
                </div>
                
                {/* Action Buttons */}
                <div className="flex space-x-4">
                  <button
                    onClick={handleSingleExtraction}
                    disabled={isProcessing || pdfFiles.length !== 1}
                    className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isProcessing ? 'Processing...' : 'Extract Single PDF'}
                  </button>
                  <button
                    onClick={handleBatchExtraction}
                    disabled={isProcessing || pdfFiles.length === 0}
                    className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isProcessing ? 'Processing...' : `Batch Process ${pdfFiles.length} PDFs`}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {activeTab === 'review' && (
          <div className="grid grid-cols-12 gap-6">
            {/* Left Panel - Extraction List */}
            <div className="col-span-4 bg-white rounded-lg shadow">
              <div className="p-4 border-b">
                <div className="space-y-3">
                  <input
                    type="text"
                    placeholder="Search extractions..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full px-3 py-2 border rounded-md"
                  />
                  <div className="flex space-x-2">
                    <select
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                      className="flex-1 px-3 py-1 border rounded-md text-sm"
                    >
                      <option value="all">All Status</option>
                      <option value="pending">Pending</option>
                      <option value="verified">Verified</option>
                      <option value="flagged">Flagged</option>
                      <option value="rejected">Rejected</option>
                    </select>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={minConfidence * 100}
                      onChange={(e) => setMinConfidence(e.target.value / 100)}
                      className="flex-1"
                    />
                    <span className="text-sm text-gray-600">
                      {Math.round(minConfidence * 100)}%
                    </span>
                  </div>
                </div>
                
                {/* Progress Bar */}
                <div className="mt-4">
                  <div className="flex justify-between text-sm text-gray-600 mb-1">
                    <span>Progress</span>
                    <span>{verifiedCount}/{total}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-green-600 h-2 rounded-full transition-all"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
              </div>
              
              <div className="overflow-y-auto max-h-[600px]">
                {filteredExtractions.map((ext, idx) => {
                  const status = statuses[extractions.indexOf(ext)] || 'pending';
                  return (
                    <div
                      key={idx}
                      onClick={() => {
                        setSelectedExtraction(ext);
                        searchSimilar(ext);
                      }}
                      className={`p-4 border-b cursor-pointer hover:bg-gray-50 ${
                        selectedExtraction === ext ? 'bg-blue-50' : ''
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="font-medium text-sm">{ext.field_name}</div>
                          <div className="text-sm text-gray-900 mt-1 font-semibold">
                            {String(ext.value).substring(0, 50)}
                            {String(ext.value).length > 50 && '...'}
                          </div>
                          <div className="flex items-center mt-2 space-x-2">
                            <span className="text-xs text-gray-500">
                              Page {ext.page_number}
                            </span>
                            <span className={`text-xs px-2 py-0.5 rounded ${
                              ext.confidence >= 0.8
                                ? 'bg-green-100 text-green-800'
                                : ext.confidence >= 0.5
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-red-100 text-red-800'
                            }`}>
                              {Math.round(ext.confidence * 100)}%
                            </span>
                            {ext.llm_validated && (
                              <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-800 rounded">
                                AI
                              </span>
                            )}
                            {ext.extraction_method === 'llm_claude' && (
                              <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-800 rounded">
                                Claude
                              </span>
                            )}
                          </div>
                        </div>
                        <div className={`ml-2 px-2 py-1 text-xs rounded ${
                          status === 'verified'
                            ? 'bg-green-100 text-green-800'
                            : status === 'flagged'
                            ? 'bg-yellow-100 text-yellow-800'
                            : status === 'rejected'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-gray-100 text-gray-600'
                        }`}>
                          {status}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            
            {/* Right Panel - Detail View */}
            <div className="col-span-8 bg-white rounded-lg shadow">
              {selectedExtraction ? (
                <div className="p-6">
                  <div className="mb-6">
                    <h2 className="text-xl font-semibold mb-2">
                      {selectedExtraction.field_name}
                    </h2>
                    <div className="text-2xl font-bold text-gray-900 mb-4">
                      {String(selectedExtraction.value)}
                    </div>
                    
                    {/* Metadata */}
                    <div className="grid grid-cols-2 gap-4 mb-6">
                      <div>
                        <span className="text-sm text-gray-500">Confidence</span>
                        <div className="flex items-center mt-1">
                          <div className="flex-1 bg-gray-200 rounded-full h-2 mr-2">
                            <div
                              className={`h-2 rounded-full ${
                                selectedExtraction.confidence >= 0.8
                                  ? 'bg-green-500'
                                  : selectedExtraction.confidence >= 0.5
                                  ? 'bg-yellow-500'
                                  : 'bg-red-500'
                              }`}
                              style={{ width: `${selectedExtraction.confidence * 100}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium">
                            {Math.round(selectedExtraction.confidence * 100)}%
                          </span>
                        </div>
                      </div>
                      <div>
                        <span className="text-sm text-gray-500">Page</span>
                        <div className="text-sm font-medium mt-1">
                          {selectedExtraction.page_number}
                        </div>
                      </div>
                      <div>
                        <span className="text-sm text-gray-500">Method</span>
                        <div className="text-sm font-medium mt-1">
                          {selectedExtraction.extraction_method}
                        </div>
                      </div>
                      <div>
                        <span className="text-sm text-gray-500">Source PDF</span>
                        <div className="text-sm font-medium mt-1 truncate">
                          {selectedExtraction.source_pdf || 'Unknown'}
                        </div>
                      </div>
                    </div>
                    
                    {/* AI Validation */}
                    {selectedExtraction.llm_validated && (
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                        <div className="flex items-start">
                          <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                          </svg>
                          <div className="ml-3">
                            <h3 className="text-sm font-medium text-blue-900">
                              AI Validation
                            </h3>
                            <p className="text-sm text-blue-700 mt-1">
                              {selectedExtraction.llm_explanation}
                            </p>
                            <div className="mt-2">
                              <span className="text-xs font-medium text-blue-600">
                                LLM Confidence: {Math.round(selectedExtraction.llm_confidence * 100)}%
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {/* Context */}
                    <div className="mb-6">
                      <h3 className="text-sm font-medium text-gray-700 mb-2">Context</h3>
                      <div className="bg-gray-50 p-4 rounded-lg text-sm">
                        <p className="text-gray-700 whitespace-pre-wrap">
                          {selectedExtraction.context}
                        </p>
                      </div>
                    </div>
                    
                    {/* Screenshot */}
                    {selectedExtraction.screenshot_path && (
                      <div className="mb-6">
                        <h3 className="text-sm font-medium text-gray-700 mb-2">Evidence Screenshot</h3>
                        <img
                          src={`${serverUrl}/static/screenshots/${selectedExtraction.screenshot_path}`}
                          alt="Evidence"
                          className="max-w-full border rounded-lg"
                        />
                      </div>
                    )}
                    
                    {/* Similar Extractions */}
                    {similarExtractions.length > 0 && (
                      <div className="mb-6">
                        <h3 className="text-sm font-medium text-gray-700 mb-2">
                          Similar Extractions in Database
                        </h3>
                        <div className="space-y-2">
                          {similarExtractions.slice(0, 3).map((similar, idx) => (
                            <div key={idx} className="bg-gray-50 p-3 rounded text-sm">
                              <div className="font-medium">{similar.field_name}</div>
                              <div className="text-gray-600">{similar.value}</div>
                              <div className="text-xs text-gray-500 mt-1">
                                Confidence: {Math.round(similar.confidence * 100)}%
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Review Actions */}
                    <div className="border-t pt-6">
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Reviewer Notes
                        </label>
                        <textarea
                          className="w-full px-3 py-2 border rounded-md"
                          rows={3}
                          placeholder="Add notes about this extraction..."
                          value={notes[extractions.indexOf(selectedExtraction)] || ''}
                          onChange={(e) => {
                            const idx = extractions.indexOf(selectedExtraction);
                            setNotes(prev => ({ ...prev, [idx]: e.target.value }));
                          }}
                        />
                      </div>
                      
                      <div className="flex space-x-3">
                        <button
                          onClick={() => submitFeedback(selectedExtraction, 'verified', notes[extractions.indexOf(selectedExtraction)])}
                          className="flex-1 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                        >
                          Verify
                        </button>
                        <button
                          onClick={() => submitFeedback(selectedExtraction, 'flagged', notes[extractions.indexOf(selectedExtraction)])}
                          className="flex-1 px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600"
                        >
                          Flag for Review
                        </button>
                        <button
                          onClick={() => submitFeedback(selectedExtraction, 'rejected', notes[extractions.indexOf(selectedExtraction)])}
                          className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-6 text-center text-gray-500">
                  Select an extraction to view details
                </div>
              )}
            </div>
          </div>
        )}
        
        {activeTab === 'templates' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Template Builder</h2>
            <div className="text-gray-600">
              <p>Visual template builder coming soon...</p>
              <p className="mt-2">Features will include:</p>
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li>Drag-and-drop field creation</li>
                <li>Visual regex pattern builder</li>
                <li>Test patterns on sample text</li>
                <li>Import/export templates</li>
                <li>Template versioning</li>
              </ul>
            </div>
          </div>
        )}
        
        {activeTab === 'jobs' && (
          <div className="bg-white rounded-lg shadow">
            <div className="p-6">
              <h2 className="text-lg font-semibold mb-4">Extraction Jobs</h2>
              <div className="space-y-4">
                {jobs.map(job => (
                  <div key={job.job_id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <span className="font-medium">Job {job.job_id.slice(0, 8)}</span>
                        <span className="ml-2 text-sm text-gray-500">
                          ({job.pdf_count} PDFs)
                        </span>
                      </div>
                      <span className={`px-2 py-1 text-xs rounded ${
                        job.status === 'completed'
                          ? 'bg-green-100 text-green-800'
                          : job.status === 'processing'
                          ? 'bg-blue-100 text-blue-800'
                          : job.status === 'failed'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        {job.status}
                      </span>
                    </div>
                    {job.status === 'processing' && (
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all"
                          style={{ width: `${job.progress}%` }}
                        />
                      </div>
                    )}
                    {job.status === 'completed' && (
                      <button
                        onClick={() => fetchJobResults(job.job_id)}
                        className="mt-2 text-sm text-blue-600 hover:text-blue-800"
                      >
                        Load Results
                      </button>
                    )}
                  </div>
                ))}
                {jobs.length === 0 && (
                  <p className="text-gray-500 text-center py-8">
                    No extraction jobs yet
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default EnhancedApp;