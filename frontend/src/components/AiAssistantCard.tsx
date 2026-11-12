import React, { useState } from 'react';
import {
  Sparkles,
  AlertTriangle,
  HelpCircle,
  CheckSquare,
  Square,
  ShieldAlert,
  Info,
  Cpu
} from 'lucide-react';
import { BedrockAISummary } from '../types/case';

interface AiAssistantCardProps {
  summary?: BedrockAISummary | null;
  onActionCheck?: (action: string, checked: boolean) => void;
}

export const AiAssistantCard: React.FC<AiAssistantCardProps> = ({ summary, onActionCheck }) => {
  const [completedActions, setCompletedActions] = useState<Record<string, boolean>>({});
  const [showDisclaimer, setShowDisclaimer] = useState(false);

  if (!summary) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 text-center text-slate-400">
        <Sparkles className="w-8 h-8 text-sky-400 mx-auto mb-2 opacity-50 animate-pulse" />
        <p className="text-sm">Amazon Bedrock analysis pending or not triggered for this case.</p>
      </div>
    );
  }

  const toggleAction = (action: string) => {
    const updated = !completedActions[action];
    setCompletedActions((prev) => ({ ...prev, [action]: updated }));
    if (onActionCheck) {
      onActionCheck(action, updated);
    }
  };

  const confidencePct = Math.round((summary.confidence_score ?? 0.88) * 100);
  const riskIndicators = summary.risk_indicators || summary.key_evidence || [];

  return (
    <div className="bg-gradient-to-b from-slate-900 to-slate-900/90 border border-sky-900/50 rounded-xl shadow-xl overflow-hidden">
      {/* Header */}
      <div className="bg-sky-950/40 border-b border-sky-900/40 px-5 py-3.5 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="text-sm font-semibold text-white flex items-center gap-2">
              Amazon Bedrock GenAI Assistant
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-300 font-normal">
                {summary.model_id ? summary.model_id.split(':').pop() : 'claude-3-5-sonnet'}
              </span>
            </div>
            <div className="text-[11px] text-slate-400 font-mono">
              Prompt Grounding: Strict Evidence Retrieval &bull; No Speculative Hallucinations
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="text-right">
            <div className="text-[10px] text-slate-400 uppercase font-mono">Synthesis Confidence</div>
            <div className="text-xs font-bold text-sky-400 font-mono">{confidencePct}%</div>
          </div>
          <button
            onClick={() => setShowDisclaimer(!showDisclaimer)}
            className="text-slate-400 hover:text-slate-200 text-xs p-1 rounded hover:bg-slate-800 transition-colors"
            title="Advisory AI Boundary"
          >
            <Info className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Advisory Guardrail Banner */}
      {showDisclaimer && (
        <div className="bg-amber-950/40 border-b border-amber-900/40 px-5 py-2.5 text-xs text-amber-200/90 flex items-start space-x-2">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-amber-300">Human-in-the-Loop Governance:</span> This GenAI synthesis is advisory only. In accordance with enterprise fraud compliance, Bedrock does not declare legal guilt, block accounts, or void settlements without human analyst authorization.
          </div>
        </div>
      )}

      <div className="p-5 space-y-5 text-sm">
        {/* Executive Summary */}
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 font-mono flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-sky-400" />
            Executive Synthesis
          </h4>
          <div className="p-3.5 bg-slate-950/70 rounded-lg border border-slate-800/80 text-slate-200 leading-relaxed text-xs md:text-sm font-sans">
            {summary.executive_summary}
          </div>
        </div>

        {/* Risk Indicators */}
        {riskIndicators.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-rose-400 mb-2 font-mono flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
              Observed Risk Indicators ({riskIndicators.length})
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {riskIndicators.map((ind: string, idx: number) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-lg bg-rose-950/20 border border-rose-900/30 text-rose-200/90 text-xs flex items-start space-x-2"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-rose-400 mt-1.5 shrink-0" />
                  <span>{ind}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Alternative Explanations */}
        {summary.alternative_explanations && summary.alternative_explanations.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 font-mono flex items-center gap-1.5">
              <HelpCircle className="w-3.5 h-3.5 text-indigo-400" />
              Plausible Legitimate Hypotheses
            </h4>
            <ul className="space-y-1.5">
              {summary.alternative_explanations.map((alt: string, idx: number) => (
                <li
                  key={idx}
                  className="p-2.5 rounded-lg bg-slate-950/50 border border-slate-800/60 text-slate-300 text-xs flex items-start space-x-2"
                >
                  <span className="text-indigo-400 font-mono font-bold text-xs shrink-0">&bull;</span>
                  <span>{alt}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recommended Actions */}
        {summary.recommended_actions && summary.recommended_actions.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-2 font-mono flex items-center gap-1.5">
              <CheckSquare className="w-3.5 h-3.5 text-emerald-400" />
              SOP Action Plan for Human Investigator
            </h4>
            <div className="space-y-1.5">
              {summary.recommended_actions.map((act: string, idx: number) => {
                const isChecked = !!completedActions[act];
                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => toggleAction(act)}
                    className={`w-full text-left p-2.5 rounded-lg border transition-all text-xs flex items-center justify-between ${
                      isChecked
                        ? 'bg-emerald-950/20 border-emerald-800/40 text-emerald-300 line-through'
                        : 'bg-slate-950/80 border-slate-800 hover:border-slate-700 text-slate-200'
                    }`}
                  >
                    <div className="flex items-center space-x-2.5">
                      {isChecked ? (
                        <CheckSquare className="w-4 h-4 text-emerald-400 shrink-0" />
                      ) : (
                        <Square className="w-4 h-4 text-slate-500 shrink-0" />
                      )}
                      <span>{act}</span>
                    </div>
                    <span className="text-[10px] font-mono text-slate-500 uppercase">
                      {isChecked ? 'Completed' : 'Pending'}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
