import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  Settings,
  Shield,
  Brain,
  FolderOpen,
  RefreshCw,
  Save,
  CheckCircle2,
  AlertTriangle,
  Cpu,
  Eye,
  Swords,
  Lock,
  Database,
  Repeat,
  Hash,
  Gauge,
  Crosshair,
  Trash2,
  Server,
} from 'lucide-react';

interface ConfigState {
  guard_mode: string;
  max_steps: number;
  enable_ai_eval: boolean;
  enable_shadow_browser: boolean;
  loop_window: number;
  loop_threshold: number;
  max_same_tool: number;
  security_score_threshold: number;
  relevance_score_threshold: number;
  auto_intervene_on_loop: boolean;
  log_retention_days: number;
  _runtime?: {
    api_version: string;
    log_directory: string;
    sessions_directory: string;
    total_session_files: number;
    total_agent_files: number;
    total_step_log_files: number;
    total_issue_files: number;
    config_file: string;
    config_exists: boolean;
  };
}

const GUARD_MODES = [
  { value: 'monitor', label: 'Monitor', icon: Eye, desc: 'Passive observation only' },
  { value: 'intervene', label: 'Intervene', icon: Swords, desc: 'Can cancel stuck/unsafe tool calls' },
  { value: 'enforce', label: 'Enforce', icon: Lock, desc: 'Strict security enforcement' },
];

export const ConfigView: React.FC = () => {
  const [config, setConfig] = useState<ConfigState | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  const loadConfig = async () => {
    try {
      const data = await api.getConfig();
      setConfig(data as ConfigState);
      setError(null);
      setDirty(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load config');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadConfig(); }, []);

  const updateField = (key: string, value: any) => {
    if (!config) return;
    setConfig({ ...config, [key]: value });
    setDirty(true);
    setSaved(false);
  };

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      const { _runtime, ...configData } = config;
      await api.updateConfig(configData);
      setSaved(true);
      setDirty(false);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400 flex items-center gap-2">
          <RefreshCw size={16} className="animate-spin" /> Loading configuration...
        </div>
      </div>
    );
  }

  if (error && !config) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="bg-red-900/20 border border-red-900/30 rounded-xl p-6 text-center">
          <h3 className="text-lg font-medium text-red-400 mb-2">Error</h3>
          <p className="text-sm text-gray-400">{error}</p>
        </div>
      </div>
    );
  }

  if (!config) return null;

  const runtime = config._runtime;

  return (
    <div className="flex flex-col h-full space-y-6 animate-in fade-in duration-700 overflow-y-auto">
      {/* Header */}
      <div className="flex-none flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <Settings size={20} className="text-phantom-400" /> Configuration
          </h1>
          <p className="text-sm text-gray-400">PhantomGuard monitoring and security settings</p>
        </div>
        <div className="flex items-center gap-3">
          {saved && (
            <span className="flex items-center gap-1.5 text-xs text-emerald-400">
              <CheckCircle2 size={14} /> Saved
            </span>
          )}
          <button
            onClick={handleSave}
            disabled={!dirty || saving}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              dirty
                ? 'bg-phantom-600 hover:bg-phantom-500 text-white'
                : 'bg-dark-surface border border-dark-border text-gray-500 cursor-not-allowed'
            }`}
          >
            <Save size={14} />
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* System Info */}
      {runtime && (
        <div className="flex-none bg-dark-surface/50 border border-dark-border rounded-xl p-4">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Server size={14} className="text-phantom-400" /> System Information
          </h3>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            <div>
              <span className="text-gray-500">API Version</span>
              <div className="text-gray-200 font-mono mt-0.5">{runtime.api_version}</div>
            </div>
            <div>
              <span className="text-gray-500">Session Files</span>
              <div className="text-gray-200 font-mono mt-0.5">{runtime.total_session_files}</div>
            </div>
            <div>
              <span className="text-gray-500">Registered Agents</span>
              <div className="text-gray-200 font-mono mt-0.5">{runtime.total_agent_files}</div>
            </div>
            <div>
              <span className="text-gray-500">Config File</span>
              <div className="text-gray-200 font-mono mt-0.5 truncate" title={runtime.config_file}>
                {runtime.config_exists ? 'Active' : 'Using defaults'}
              </div>
            </div>
            <div className="col-span-2">
              <span className="text-gray-500">Log Directory</span>
              <div className="text-gray-200 font-mono mt-0.5 truncate" title={runtime.log_directory}>{runtime.log_directory}</div>
            </div>
            <div className="col-span-2">
              <span className="text-gray-500">Sessions Directory</span>
              <div className="text-gray-200 font-mono mt-0.5 truncate" title={runtime.sessions_directory}>{runtime.sessions_directory}</div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Guard Mode */}
        <div className="bg-dark-surface/50 border border-dark-border rounded-xl p-4">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Shield size={14} className="text-phantom-400" /> Guard Mode
          </h3>
          <div className="space-y-2">
            {GUARD_MODES.map((mode) => {
              const Icon = mode.icon;
              const isActive = config.guard_mode === mode.value;
              return (
                <button
                  key={mode.value}
                  onClick={() => updateField('guard_mode', mode.value)}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg border text-left transition-colors ${
                    isActive
                      ? 'bg-phantom-950/30 border-phantom-900/50 text-phantom-300'
                      : 'bg-dark-bg/30 border-dark-border text-gray-400 hover:text-gray-300 hover:border-gray-600'
                  }`}
                >
                  <Icon size={16} className={isActive ? 'text-phantom-400' : 'text-gray-500'} />
                  <div>
                    <div className="text-sm font-medium">{mode.label}</div>
                    <div className="text-xs text-gray-500">{mode.desc}</div>
                  </div>
                  {isActive && <CheckCircle2 size={14} className="ml-auto text-phantom-400" />}
                </button>
              );
            })}
          </div>
        </div>

        {/* AI Evaluation */}
        <div className="bg-dark-surface/50 border border-dark-border rounded-xl p-4">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Brain size={14} className="text-phantom-400" /> AI Evaluation
          </h3>
          <div className="space-y-4">
            <ToggleField
              label="AI Step Evaluation"
              description="Use Nova Lite to evaluate step relevance and security"
              icon={Cpu}
              value={config.enable_ai_eval}
              onChange={(v) => updateField('enable_ai_eval', v)}
            />
            <ToggleField
              label="Shadow Browser"
              description="Verify browser actions with headless browser"
              icon={Eye}
              value={config.enable_shadow_browser}
              onChange={(v) => updateField('enable_shadow_browser', v)}
            />
            <ToggleField
              label="Auto-Intervene on Loop"
              description="Automatically cancel tool calls when loop detected"
              icon={AlertTriangle}
              value={config.auto_intervene_on_loop}
              onChange={(v) => updateField('auto_intervene_on_loop', v)}
            />
          </div>
        </div>

        {/* Loop Detection */}
        <div className="bg-dark-surface/50 border border-dark-border rounded-xl p-4">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Repeat size={14} className="text-phantom-400" /> Loop Detection
          </h3>
          <div className="space-y-4">
            <NumberField
              label="Loop Window"
              description="Number of recent steps to check for patterns"
              icon={Hash}
              value={config.loop_window}
              min={2}
              max={20}
              onChange={(v) => updateField('loop_window', v)}
            />
            <NumberField
              label="Loop Threshold"
              description="Repetitions in window to trigger loop detection"
              icon={Repeat}
              value={config.loop_threshold}
              min={2}
              max={10}
              onChange={(v) => updateField('loop_threshold', v)}
            />
            <NumberField
              label="Max Same Tool"
              description="Max times a single tool can be called per session"
              icon={Gauge}
              value={config.max_same_tool}
              min={3}
              max={50}
              onChange={(v) => updateField('max_same_tool', v)}
            />
            <NumberField
              label="Max Steps"
              description="Maximum steps before intervention"
              icon={Crosshair}
              value={config.max_steps}
              min={5}
              max={200}
              onChange={(v) => updateField('max_steps', v)}
            />
          </div>
        </div>

        {/* Thresholds */}
        <div className="bg-dark-surface/50 border border-dark-border rounded-xl p-4">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Crosshair size={14} className="text-phantom-400" /> Scoring Thresholds
          </h3>
          <div className="space-y-4">
            <NumberField
              label="Security Threshold"
              description="Score below this triggers security alert (0-100)"
              icon={Shield}
              value={config.security_score_threshold}
              min={0}
              max={100}
              onChange={(v) => updateField('security_score_threshold', v)}
            />
            <NumberField
              label="Relevance Threshold"
              description="Score below this marks step as irrelevant (0-100)"
              icon={Crosshair}
              value={config.relevance_score_threshold}
              min={0}
              max={100}
              onChange={(v) => updateField('relevance_score_threshold', v)}
            />
            <NumberField
              label="Log Retention (days)"
              description="How long to keep session logs"
              icon={Database}
              value={config.log_retention_days}
              min={1}
              max={365}
              onChange={(v) => updateField('log_retention_days', v)}
            />
          </div>
        </div>

      </div>
    </div>
  );
};


/* ── Reusable field components ─────────────────────── */

const ToggleField: React.FC<{
  label: string;
  description: string;
  icon: React.ElementType;
  value: boolean;
  onChange: (v: boolean) => void;
}> = ({ label, description, icon: Icon, value, onChange }) => (
  <div className="flex items-center justify-between gap-3">
    <div className="flex items-center gap-3">
      <Icon size={14} className="text-gray-500 shrink-0" />
      <div>
        <div className="text-sm text-gray-300">{label}</div>
        <div className="text-xs text-gray-500">{description}</div>
      </div>
    </div>
    <button
      onClick={() => onChange(!value)}
      className={`relative w-10 h-5 rounded-full transition-colors shrink-0 ${
        value ? 'bg-phantom-600' : 'bg-gray-700'
      }`}
    >
      <span
        className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
          value ? 'left-[22px]' : 'left-0.5'
        }`}
      />
    </button>
  </div>
);


const NumberField: React.FC<{
  label: string;
  description: string;
  icon: React.ElementType;
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
}> = ({ label, description, icon: Icon, value, min, max, onChange }) => (
  <div className="flex items-center justify-between gap-3">
    <div className="flex items-center gap-3 flex-1 min-w-0">
      <Icon size={14} className="text-gray-500 shrink-0" />
      <div className="min-w-0">
        <div className="text-sm text-gray-300">{label}</div>
        <div className="text-xs text-gray-500">{description}</div>
      </div>
    </div>
    <input
      type="number"
      value={value}
      min={min}
      max={max}
      onChange={(e) => {
        const n = parseInt(e.target.value, 10);
        if (!isNaN(n) && n >= min && n <= max) onChange(n);
      }}
      className="w-20 px-2 py-1 text-sm font-mono text-right bg-dark-bg border border-dark-border rounded-lg text-gray-200 focus:border-phantom-600 focus:outline-none shrink-0"
    />
  </div>
);
