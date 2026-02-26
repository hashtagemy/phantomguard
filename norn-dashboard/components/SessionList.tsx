import React from 'react';
import { Session } from '../types';
import { StatusBadge } from './StatusBadge';
import { ChevronRight, Search, Filter, ShieldCheck, ShieldAlert } from 'lucide-react';

interface SessionListProps {
  sessions: Session[];
  onSelectSession: (id: string) => void;
}

export const SessionList: React.FC<SessionListProps> = ({ sessions, onSelectSession }) => {
  return (
    <div className="flex flex-col h-full space-y-4">
      
      {/* Filters */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
          <input 
            type="text" 
            placeholder="Search sessions..." 
            className="w-full bg-dark-surface border border-dark-border rounded-lg pl-10 pr-4 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-phantom-500 transition-colors"
          />
        </div>
        <button className="flex items-center gap-2 px-3 py-2 bg-dark-surface border border-dark-border rounded-lg text-sm text-gray-300 hover:text-white transition-colors">
          <Filter size={14} /> Filter
        </button>
      </div>

      {/* Table Header */}
      <div className="grid grid-cols-12 gap-4 px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider border-b border-dark-border">
        <div className="col-span-4">Agent / Task</div>
        <div className="col-span-2">Status</div>
        <div className="col-span-2">Security</div>
        <div className="col-span-2">Efficiency</div>
        <div className="col-span-2 text-right">Time</div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto space-y-1 pr-1">
        {sessions.map((session) => (
          <div 
            key={session.id}
            onClick={() => onSelectSession(session.id)}
            className="grid grid-cols-12 gap-4 items-center px-4 py-3 bg-dark-surface/30 hover:bg-dark-surface rounded-lg border border-transparent hover:border-dark-border cursor-pointer transition-all group"
          >
            <div className="col-span-4 overflow-hidden">
              <div className="font-medium text-gray-200 truncate group-hover:text-phantom-300 transition-colors">{session.agentName}</div>
              <div className="text-xs text-gray-500 truncate">{session.taskPreview}</div>
            </div>
            
            <div className="col-span-2">
              <StatusBadge status={session.overallQuality} size="sm" />
            </div>

            <div className="col-span-2 flex items-center gap-2">
              {session.securityScore === 100 ? (
                <ShieldCheck size={16} className="text-emerald-500" />
              ) : (
                <ShieldAlert size={16} className={session.securityScore < 70 ? "text-red-500" : "text-yellow-500"} />
              )}
              <span className={`text-sm font-mono ${session.securityScore < 100 ? 'text-gray-300' : 'text-gray-500'}`}>
                {session.securityScore}%
              </span>
            </div>

            <div className="col-span-2">
               <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                 <div 
                    className={`h-full rounded-full ${session.efficiencyScore > 80 ? 'bg-emerald-500' : session.efficiencyScore > 50 ? 'bg-yellow-500' : 'bg-red-500'}`} 
                    style={{ width: `${session.efficiencyScore}%` }}
                  ></div>
               </div>
            </div>

            <div className="col-span-2 text-right flex items-center justify-end gap-2 text-gray-500">
              <span className="text-xs font-mono">{new Date(session.startTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
              <ChevronRight size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
