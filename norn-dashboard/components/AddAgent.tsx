import React, { useState } from 'react';
import { Github, Upload, FileCode, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../services/api';

interface AddAgentProps {
  onAgentAdded?: () => void;
}

export const AddAgent: React.FC<AddAgentProps> = ({ onAgentAdded }) => {
  const [activeTab, setActiveTab] = useState<'github' | 'upload'>('github');
  const [url, setUrl] = useState('');
  const [agentName, setAgentName] = useState('');
  const [mainFile, setMainFile] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [importedAgents, setImportedAgents] = useState<any[]>([]);
  const [registeredAgents, setRegisteredAgents] = useState<any[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(false);

  // Load registered agents on mount
  React.useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    setLoadingAgents(true);
    try {
      const agents = await api.getAgents();
      setRegisteredAgents(agents);
    } catch (err) {
      console.error('Failed to load agents:', err);
    } finally {
      setLoadingAgents(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleGithubImport = async () => {
    if (!url) {
      setError('Please provide a repository URL');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(false);
    setImportedAgents([]);

    try {
      const results = await api.importGithubAgent({
        repo_url: url,
        ...(agentName && { agent_name: agentName }),
        ...(mainFile && { main_file: mainFile }),
      });

      setSuccess(true);
      setImportedAgents(results);
      setUrl('');
      setAgentName('');
      setMainFile('');

      // Reload agents list
      await loadAgents();

      // Notify parent to refresh
      if (onAgentAdded) {
        onAgentAdded();
      }

      // Reset success message after 8 seconds
      setTimeout(() => {
        setSuccess(false);
        setImportedAgents([]);
      }, 8000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import agent');
    } finally {
      setLoading(false);
    }
  };

  const handleZipUpload = async () => {
    if (!file || !agentName) {
      setError('Please provide both file and agent name');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(false);
    setImportedAgents([]);

    try {
      // Use FormData directly
      const formData = new FormData();
      formData.append('file', file);
      formData.append('agent_name', agentName);

      // Direct fetch since we need FormData
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/agents/import/zip`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(errorData.detail || 'Upload failed');
      }

      const result = await response.json();

      setSuccess(true);
      setImportedAgents(Array.isArray(result) ? result : [result]);
      setFile(null);
      setAgentName('');

      // Reload agents list
      await loadAgents();

      // Notify parent to refresh
      if (onAgentAdded) {
        onAgentAdded();
      }

      // Reset success message after 5 seconds
      setTimeout(() => {
        setSuccess(false);
        setImportedAgents([]);
      }, 5000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload agent');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAgent = async (agentId: string) => {
    if (!confirm('Are you sure you want to delete this agent?')) {
      return;
    }

    try {
      await api.deleteAgent(agentId);
      await loadAgents();
      
      if (onAgentAdded) {
        onAgentAdded();
      }
    } catch (err) {
      console.error('Failed to delete agent:', err);
      alert('Failed to delete agent');
    }
  };

  return (
    <div className="max-w-3xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white tracking-tight mb-2">Import New Agent</h1>
        <p className="text-gray-400">Connect a repository or upload your agent's code package for analysis.</p>
      </div>

      <div className="bg-dark-surface border border-dark-border rounded-xl overflow-hidden">
        {/* Tabs */}
        <div className="flex border-b border-dark-border">
          <button
            onClick={() => setActiveTab('github')}
            className={`flex-1 py-4 text-sm font-medium transition-colors flex items-center justify-center gap-2
              ${activeTab === 'github' ? 'bg-dark-surface text-phantom-400 border-b-2 border-phantom-500' : 'bg-dark-bg/50 text-gray-500 hover:text-gray-300'}`}
          >
            <Github size={18} />
            GitHub Repository
          </button>
          <button
            onClick={() => setActiveTab('upload')}
            className={`flex-1 py-4 text-sm font-medium transition-colors flex items-center justify-center gap-2
              ${activeTab === 'upload' ? 'bg-dark-surface text-phantom-400 border-b-2 border-phantom-500' : 'bg-dark-bg/50 text-gray-500 hover:text-gray-300'}`}
          >
            <Upload size={18} />
            Upload ZIP
          </button>
        </div>

        <div className="p-8">
          {activeTab === 'github' ? (
            <div className="space-y-6">
              {error && (
                <div className="bg-red-900/20 border border-red-900/30 rounded-lg p-4 flex gap-3">
                  <AlertCircle className="text-red-400 shrink-0" size={20} />
                  <div className="text-sm text-red-200">{error}</div>
                </div>
              )}

              {success && (
                <div className="bg-emerald-900/20 border border-emerald-900/30 rounded-lg p-4 flex gap-3">
                  <CheckCircle2 className="text-emerald-400 shrink-0" size={20} />
                  <div className="text-sm text-emerald-200">
                    {importedAgents.length} agent{importedAgents.length !== 1 ? 's' : ''} discovered and imported successfully!
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Agent Name <span className="text-gray-500 font-normal">(optional - used as name prefix)</span>
                </label>
                <input
                  type="text"
                  value={agentName}
                  onChange={(e) => setAgentName(e.target.value)}
                  placeholder="e.g. My Suite (optional)"
                  className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-phantom-500 transition-colors mb-4"
                  disabled={loading}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Repository URL</label>
                <div className="relative">
                  <Github className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
                  <input
                    type="text"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://github.com/username/agent-repo"
                    className="w-full bg-dark-bg border border-dark-border rounded-lg pl-10 pr-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-phantom-500 transition-colors"
                    disabled={loading}
                  />
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  Norn will automatically scan the repository for agent definitions and configuration files.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Main File <span className="text-gray-500 font-normal">(optional)</span>
                </label>
                <div className="relative">
                  <FileCode className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
                  <input
                    type="text"
                    value={mainFile}
                    onChange={(e) => setMainFile(e.target.value)}
                    placeholder="e.g. personal_assistant.py"
                    className="w-full bg-dark-bg border border-dark-border rounded-lg pl-10 pr-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-phantom-500 transition-colors"
                    disabled={loading}
                  />
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  Leave empty to auto-discover all agents. Specify a file to import only that agent.
                </p>
              </div>

              <div className="bg-phantom-950/20 border border-phantom-900/30 rounded-lg p-4 flex gap-3">
                <AlertCircle className="text-phantom-400 shrink-0" size={20} />
                <div className="text-sm text-phantom-200">
                  Ensure the repository is public or you have granted Norn access to your private repositories.
                </div>
              </div>

              <div className="pt-4 flex justify-end">
                <button 
                  onClick={handleGithubImport}
                  disabled={loading || !url}
                  className={`px-6 py-2 font-medium rounded-lg transition-colors flex items-center gap-2
                    ${loading || !url
                      ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                      : 'bg-phantom-600 hover:bg-phantom-500 text-white'}`}
                >
                  {loading && <Loader2 size={16} className="animate-spin" />}
                  {loading ? 'Importing...' : 'Import Repository'}
                </button>
              </div>

              {/* Discovered Agents */}
              {importedAgents.length > 0 && (
                <div className="mt-6 space-y-3">
                  <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    <CheckCircle2 className="text-emerald-400" size={20} />
                    {importedAgents.length} Agent{importedAgents.length !== 1 ? 's' : ''} Imported
                  </h3>
                  {importedAgents.map((agent, idx) => (
                    <div key={idx} className="bg-dark-bg/50 border border-dark-border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-white font-medium">{agent.name}</span>
                        <span className="text-xs text-gray-500 font-mono bg-dark-surface px-2 py-1 rounded">{agent.main_file}</span>
                      </div>
                      {agent.discovery && (
                        <div className="grid grid-cols-4 gap-2">
                          <div className="text-center">
                            <div className="text-xl font-bold text-phantom-400">
                              {agent.discovery.tools?.length || 0}
                            </div>
                            <div className="text-xs text-gray-500">Tools</div>
                          </div>
                          <div className="text-center">
                            <div className="text-xl font-bold text-blue-400">
                              {agent.discovery.functions?.length || 0}
                            </div>
                            <div className="text-xs text-gray-500">Functions</div>
                          </div>
                          <div className="text-center">
                            <div className="text-xl font-bold text-red-400">
                              {agent.discovery.potential_issues?.length || 0}
                            </div>
                            <div className="text-xs text-gray-500">Issues</div>
                          </div>
                          <div className="text-center">
                            <div className="text-sm font-bold text-emerald-400">
                              {agent.discovery.agent_type || 'Unknown'}
                            </div>
                            <div className="text-xs text-gray-500">Type</div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-6">
              {error && (
                <div className="bg-red-900/20 border border-red-900/30 rounded-lg p-4 flex gap-3">
                  <AlertCircle className="text-red-400 shrink-0" size={20} />
                  <div className="text-sm text-red-200">{error}</div>
                </div>
              )}

              {success && (
                <div className="bg-emerald-900/20 border border-emerald-900/30 rounded-lg p-4 flex gap-3">
                  <CheckCircle2 className="text-emerald-400 shrink-0" size={20} />
                  <div className="text-sm text-emerald-200">Agent uploaded successfully! Analysis in progress...</div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Agent Name</label>
                <input
                  type="text"
                  value={agentName}
                  onChange={(e) => setAgentName(e.target.value)}
                  placeholder="My Trading Bot"
                  className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-phantom-500 transition-colors mb-4"
                  disabled={loading}
                />
              </div>

              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-xl p-10 text-center transition-all cursor-pointer
                  ${isDragging 
                    ? 'border-phantom-500 bg-phantom-950/10' 
                    : 'border-dark-border hover:border-gray-600 bg-dark-bg/50'}`}
              >
                <input
                  type="file"
                  id="file-upload"
                  className="hidden"
                  accept=".zip,.tar,.gz"
                  onChange={handleFileChange}
                />
                
                {file ? (
                  <div className="flex flex-col items-center">
                    <div className="w-16 h-16 bg-phantom-900/30 text-phantom-400 rounded-full flex items-center justify-center mb-4">
                      <FileCode size={32} />
                    </div>
                    <div className="text-lg font-medium text-white mb-1">{file.name}</div>
                    <div className="text-sm text-gray-500 mb-4">{(file.size / 1024 / 1024).toFixed(2)} MB</div>
                    <button 
                      onClick={(e) => { e.stopPropagation(); setFile(null); }}
                      className="text-xs text-red-400 hover:text-red-300 underline"
                    >
                      Remove file
                    </button>
                  </div>
                ) : (
                  <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center">
                    <div className="w-16 h-16 bg-gray-800/50 text-gray-400 rounded-full flex items-center justify-center mb-4 group-hover:text-white transition-colors">
                      <Upload size={32} />
                    </div>
                    <div className="text-lg font-medium text-gray-300 mb-1">
                      Drop your ZIP file here
                    </div>
                    <div className="text-sm text-gray-500">
                      or <span className="text-phantom-400 hover:underline">browse files</span>
                    </div>
                  </label>
                )}
              </div>

              <div className="text-xs text-gray-500 flex items-center justify-center gap-4">
                <span className="flex items-center gap-1"><CheckCircle2 size={12} /> .zip format</span>
                <span className="flex items-center gap-1"><CheckCircle2 size={12} /> secure scan</span>
              </div>

              <div className="pt-4 flex justify-end">
                <button 
                  onClick={handleZipUpload}
                  disabled={!file || !agentName || loading}
                  className={`px-6 py-2 font-medium rounded-lg transition-colors flex items-center gap-2
                    ${file && agentName && !loading
                      ? 'bg-phantom-600 hover:bg-phantom-500 text-white' 
                      : 'bg-gray-800 text-gray-500 cursor-not-allowed'}`}
                >
                  {loading && <Loader2 size={16} className="animate-spin" />}
                  {loading ? 'Uploading...' : 'Upload & Analyze'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Registered Agents List */}
      <div className="mt-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white">Registered Agents</h2>
          <button 
            onClick={loadAgents}
            disabled={loadingAgents}
            className="text-sm text-phantom-400 hover:text-phantom-300 flex items-center gap-2"
          >
            {loadingAgents ? <Loader2 size={14} className="animate-spin" /> : null}
            Refresh
          </button>
        </div>

        {loadingAgents && registeredAgents.length === 0 ? (
          <div className="text-center py-8 text-gray-500">Loading agents...</div>
        ) : registeredAgents.length === 0 ? (
          <div className="bg-dark-surface border border-dark-border rounded-xl p-8 text-center">
            <div className="text-gray-500 mb-2">No agents registered yet</div>
            <div className="text-sm text-gray-600">Import your first agent using the form above</div>
          </div>
        ) : (
          <div className="space-y-3">
            {registeredAgents.map((agent) => (
              <div key={agent.id} className="bg-dark-surface border border-dark-border rounded-xl p-4 hover:border-phantom-900/50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-white">{agent.name}</h3>
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        agent.status === 'analyzed' ? 'bg-emerald-900/30 text-emerald-400' :
                        agent.status === 'analyzing' ? 'bg-yellow-900/30 text-yellow-400' :
                        agent.status === 'error' ? 'bg-red-900/30 text-red-400' :
                        'bg-gray-800 text-gray-400'
                      }`}>
                        {agent.status}
                      </span>
                    </div>
                    
                    <p className="text-sm text-gray-400 mb-3">{agent.task_description}</p>
                    
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span className="flex items-center gap-1">
                        <Github size={12} />
                        {agent.source === 'git' ? 'GitHub' : 'ZIP'}
                      </span>
                      <span>{agent.main_file}</span>
                      <span>{new Date(agent.added_at).toLocaleDateString()}</span>
                    </div>

                    {/* Discovery Metrics */}
                    {agent.discovery && (
                      <div className="flex items-center gap-3 mt-3 pt-3 border-t border-dark-border">
                        <div className="text-xs">
                          <span className="text-gray-500">Tools: </span>
                          <span className="text-phantom-400 font-medium">{agent.discovery.tools?.length || 0}</span>
                        </div>
                        <div className="text-xs">
                          <span className="text-gray-500">Functions: </span>
                          <span className="text-blue-400 font-medium">{agent.discovery.functions?.length || 0}</span>
                        </div>
                        <div className="text-xs">
                          <span className="text-gray-500">Issues: </span>
                          <span className={`font-medium ${
                            (agent.discovery.potential_issues?.length || 0) > 0 ? 'text-red-400' : 'text-emerald-400'
                          }`}>
                            {agent.discovery.potential_issues?.length || 0}
                          </span>
                        </div>
                        <div className="text-xs">
                          <span className="text-gray-500">Type: </span>
                          <span className="text-gray-300 font-medium">{agent.discovery.agent_type || 'Unknown'}</span>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2 ml-4">
                    <button
                      onClick={() => handleDeleteAgent(agent.id)}
                      className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-900/10 rounded-lg transition-colors"
                      title="Delete agent"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
