import React, { useState } from 'react';
import axios from 'axios';

function App() {
  const [serverUrl, setServerUrl] = useState('http://localhost:8000');
  const [pdfFile, setPdfFile] = useState(null);
  const [templateFile, setTemplateFile] = useState(null);
  const [extractions, setExtractions] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [statuses, setStatuses] = useState({});
  const [notes, setNotes] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [minConfidence, setMinConfidence] = useState(0);

  // Compute progress
  const total = extractions.length;
  const verifiedCount = Object.values(statuses).filter((s) => s === 'verified').length;
  const progress = total ? Math.round((verifiedCount / total) * 100) : 0;

  // Filter extractions based on search, status and confidence
  const filteredExtractions = extractions.filter((ext, idx) => {
    const matchesSearch =
      ext.field_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(ext.value).toLowerCase().includes(searchTerm.toLowerCase());
    const decision = statuses[idx] || 'pending';
    const matchesStatus = statusFilter === 'all' || decision === statusFilter;
    const matchesConf = ext.confidence >= minConfidence;
    return matchesSearch && matchesStatus && matchesConf;
  });

  // Selected extraction based on filtered list
  const selected = selectedIndex !== null && filteredExtractions[selectedIndex] ? filteredExtractions[selectedIndex] : null;
  const selectedOrigIndex = selected ? extractions.indexOf(selected) : null;

  // Compute context sections
  let context_before = '';
  let context_after = '';
  let highlight_text = '';
  if (selected) {
    const ctx = selected.context || '';
    const quote = selected.exact_text || '';
    const idx = ctx.toLowerCase().indexOf(quote.toLowerCase());
    if (idx !== -1) {
      context_before = ctx.slice(0, idx);
      context_after = ctx.slice(idx + quote.length);
      highlight_text = ctx.slice(idx, idx + quote.length);
    } else {
      context_before = ctx;
      highlight_text = quote;
      context_after = '';
    }
  }

  function handleUpload() {
    if (!pdfFile || !templateFile) {
      alert('Please select a PDF and a JSON template first.');
      return;
    }
    const formData = new FormData();
    formData.append('pdf_file', pdfFile);
    formData.append('template_file', templateFile);
    axios
      .post(`${serverUrl}/api/batch_extract`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((res) => {
        const data = res.data;
        const exts = data.extractions || [];
        setExtractions(exts);
        setStatuses({});
        setNotes({});
        setSelectedIndex(null);
      })
      .catch((err) => {
        console.error(err);
        alert('Error during extraction: ' + (err.response?.data?.detail || err.message));
      });
  }

  function handleDecision(idx, decision) {
    setStatuses((prev) => ({ ...prev, [idx]: decision }));
  }

  function handleNoteChange(idx, value) {
    setNotes((prev) => ({ ...prev, [idx]: value }));
  }

  function handleExport() {
    const records = extractions.map((ext, idx) => ({
      field_name: ext.field_name,
      value: ext.value,
      decision: statuses[idx] || 'pending',
      note: notes[idx] || '',
      confidence: ext.confidence,
      page: ext.page_number,
      verification_hash: ext.verification_hash,
    }));
    const blob = new Blob([JSON.stringify(records, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'decisions.json';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  return (
    <div className="p-4 mx-auto max-w-7xl">
      <h1 className="text-2xl font-bold mb-4">Systematic Review Data Extraction Verifier</h1>
      <div className="mb-4 flex flex-wrap items-center space-x-4">
        <input
          type="file"
          accept=".pdf"
          onChange={(e) => setPdfFile(e.target.files[0] || null)}
          className="border px-2 py-1"
        />
        <input
          type="file"
          accept=".json"
          onChange={(e) => setTemplateFile(e.target.files[0] || null)}
          className="border px-2 py-1"
        />
        <button className="px-4 py-2 bg-blue-600 text-white rounded" onClick={handleUpload}>
          Run Extraction
        </button>
        <input
          className="border ml-4 px-2 py-1"
          type="text"
          value={serverUrl}
          onChange={(e) => setServerUrl(e.target.value)}
          placeholder="Server URL"
        />
      </div>
      <div className="mb-4 flex flex-wrap items-center space-x-4">
        <input
          type="text"
          className="border px-2 py-1 flex-1"
          placeholder="Search..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        <select
          className="border px-2 py-1"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="all">All</option>
          <option value="verified">Verified</option>
          <option value="flagged">Flagged</option>
          <option value="rejected">Rejected</option>
          <option value="pending">Pending</option>
        </select>
        <input
          type="number"
          min="0"
          max="1"
          step="0.05"
          value={minConfidence}
          onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
          className="border px-2 py-1 w-28"
          placeholder="Min conf."
        />
        <button className="px-3 py-2 bg-green-600 text-white rounded" onClick={handleExport}>
          Export Decisions
        </button>
      </div>
      <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden mb-4">
        <div
          className="bg-green-500 h-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        ></div>
      </div>
      <div className="flex gap-4">
        <div className="w-1/3 space-y-2 overflow-y-auto max-h-[70vh] border p-2 rounded">
          {filteredExtractions.map((ext, idx) => {
            const origIdx = extractions.indexOf(ext);
            const decision = statuses[origIdx] || 'pending';
            return (
              <div
                key={idx}
                className={`p-2 border rounded cursor-pointer ${
                  selected && origIdx === selectedOrigIndex ? 'bg-blue-50' : 'bg-white'
                } hover:bg-blue-100`}
                onClick={() => setSelectedIndex(idx)}
              >
                <div className="font-semibold">{ext.field_name}</div>
                <div className="text-sm text-gray-600 truncate">{String(ext.value)}</div>
                <div className="text-xs flex justify-between mt-1">
                  <span>{Math.round(ext.confidence * 100)}%</span>
                  <span>Page {ext.page_number}</span>
                  <span
                    className={`capitalize ${
                      decision === 'verified'
                        ? 'text-green-700'
                        : decision === 'flagged'
                        ? 'text-yellow-700'
                        : decision === 'rejected'
                        ? 'text-red-700'
                        : 'text-gray-500'
                    }`}
                  >
                    {decision}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
        <div className="flex-1 border p-4 rounded overflow-y-auto max-h-[70vh]">
          {selected ? (
            <>
              <h2 className="text-xl font-semibold mb-2">{selected.field_name}</h2>
              <div className="mb-2 text-lg font-bold break-all">{String(selected.value)}</div>
              <div className="mb-2 text-sm">Confidence: {Math.round(selected.confidence * 100)}%</div>
              <div className="mb-2 text-sm">Page: {selected.page_number}</div>
              <div className="mb-2 text-sm">
                Verification Hash:{' '}
                <span className="font-mono break-all">{selected.verification_hash}</span>
              </div>
              <div className="my-4 bg-gray-100 p-4 rounded">
                <p className="text-gray-700">
                  {context_before}
                  <span className="bg-yellow-200 font-bold">{highlight_text}</span>
                  {context_after}
                </p>
              </div>
              {selected.screenshot_path && (
                <div className="my-4">
                  <img
                    src={`${serverUrl}/static/screenshots/${selected.screenshot_path}`}
                    alt="screenshot"
                    className="max-w-full border rounded"
                  />
                </div>
              )}
              <div className="my-2">
                <textarea
                  className="w-full border p-2 rounded"
                  placeholder="Reviewer notes..."
                  value={notes[selectedOrigIndex] || ''}
                  onChange={(e) => handleNoteChange(selectedOrigIndex, e.target.value)}
                  rows={3}
                />
              </div>
              <div className="space-x-2 mt-2">
                <button
                  className={`px-3 py-1 rounded ${
                    statuses[selectedOrigIndex] === 'verified' ? 'bg-green-700 text-white' : 'bg-green-500 text-white'
                  }`}
                  onClick={() => handleDecision(selectedOrigIndex, 'verified')}
                >
                  Verify
                </button>
                <button
                  className={`px-3 py-1 rounded ${
                    statuses[selectedOrigIndex] === 'flagged' ? 'bg-yellow-600 text-white' : 'bg-yellow-400 text-black'
                  }`}
                  onClick={() => handleDecision(selectedOrigIndex, 'flagged')}
                >
                  Flag
                </button>
                <button
                  className={`px-3 py-1 rounded ${
                    statuses[selectedOrigIndex] === 'rejected' ? 'bg-red-700 text-white' : 'bg-red-500 text-white'
                  }`}
                  onClick={() => handleDecision(selectedOrigIndex, 'rejected')}
                >
                  Reject
                </button>
              </div>
            </>
          ) : (
            <p>Select an extraction from the list to view details.</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
