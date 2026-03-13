import React, { useState, useEffect } from 'react';
import {
  ShieldAlert, ShieldCheck, Activity, Database,
  CheckCircle2, AlertTriangle, Blocks, TrendingUp, Bug, X,
  Users, Target, BarChart3
} from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend
} from 'recharts';

// Backend API endpoint
const API_BASE = 'http://localhost:8000/api';

const DEFAULT_INPUT = {
  credit_score: 700,
  income: 60000,
  loan_amount: 20000,
  existing_debt: 5000,
  employment_status: 'employed',
  loan_term: 36,
};

const Dashboard = () => {
  const [records, setRecords] = useState([]);
  const [stats, setStats] = useState({
    total_applicants: 0,
    average_credit_score: 0,
    loan_approval_rate: 0,
    credit_score_distribution: []
  });
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab ] = useState('overview'); // overview | engine | audit
  const [systemStatus, setSystemStatus] = useState('SAFE');
  
  const [formData, setFormData] = useState(DEFAULT_INPUT);
  const [tamperingRecord, setTamperingRecord] = useState(null);
  const [tamperForm, setTamperForm] = useState({ 
    decision: '', 
    confidence: 0,
    income: 0,
    loan_amount: 0,
    existing_debt: 0,
    employment_status: 'employed',
    loan_term: 36
  });
  const [verifyResult, setVerifyResult] = useState(null);
  const [verifying, setVerifying] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [lastResult, setLastResult] = useState(null);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000); 
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [auditRes, statusRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/audits`),
        fetch(`${API_BASE}/system/status`),
        fetch(`${API_BASE}/stats`),
      ]);
      if (auditRes.ok) setRecords(await auditRes.json());
      if (statusRes.ok) setSystemStatus((await statusRes.json()).status);
      if (statsRes.ok) setStats(await statsRes.json());
    } catch (err) {
      console.error('Fetch error:', err);
    }
  };

  const verifyRecord = async (decisionId) => {
    setVerifying(decisionId);
    setVerifyResult(null);
    try {
      const res = await fetch(`${API_BASE}/verify/${decisionId}`, { method: 'POST' });
      const data = await res.json();
      setVerifyResult({ id: decisionId, ...data });
      setTimeout(() => setVerifyResult(null), 8000);
    } catch (err) {
      console.error('Verify error:', err);
    } finally {
      setVerifying(null);
    }
  };

  const runDecision = async () => {
    setSubmitting(true);
    setLastResult(null);
    try {
      const payload = {
        ...formData,
        credit_score: parseInt(formData.credit_score),
        income: parseFloat(formData.income),
        loan_amount: parseFloat(formData.loan_amount),
        existing_debt: parseFloat(formData.existing_debt),
        loan_term: parseInt(formData.loan_term),
      };
      const res = await fetch(`${API_BASE}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        alert(`Error: ${data.detail}`);
      } else {
        setLastResult(data);
        await fetchData();
        // Commented out automatic tab switch as requested
        // setActiveTab('audit');
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  const openTamperModal = (record) => {
    setTamperingRecord(record);
    setTamperForm({
      decision: record.decision === 'Loan Approved' ? 'Loan Rejected' : 'Loan Approved',
      confidence: parseFloat((1.0 - record.confidence).toFixed(2)),
      income: record.income || 0,
      loan_amount: record.loan_amount || 0,
      existing_debt: record.existing_debt || 0,
      employment_status: record.employment_status || 'employed',
      loan_term: record.loan_term || 36
    });
  };

  const handleTamper = async () => {
    if (!tamperingRecord) return;
    try {
      const res = await fetch(`${API_BASE}/tamper/${tamperingRecord.decision_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tamperForm),
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || 'Tamper failed');
        return;
      }
      await fetchData();
      setTamperingRecord(null);
    } catch (err) {
      console.error('Tamper error:', err);
    }
  };

  const tabs = [
    { id: 'overview', label: 'Analytics', icon: <TrendingUp className="w-4 h-4" /> },
    { id: 'engine', label: 'Decision Engine', icon: <Activity className="w-4 h-4" /> },
    { id: 'audit', label: 'Audit Log', icon: <Blocks className="w-4 h-4" /> }
  ];

  const downloadCSV = () => {
    if (records.length === 0) return;
    const headers = ["Decision ID", "Timestamp", "Model Version", "Credit Score", "Income", "Loan Amount", "Debt", "Employment", "Term", "Decision", "Confidence", "Status", "Input Hash", "Execution Hash", "Blockchain TX"];
    const csvRows = [
      headers.join(","),
      ...records.map(rec => [
        `"${rec.decision_id}"`, `"${new Date(rec.timestamp).toLocaleString()}"`, `"${rec.model_version}"`, `"${rec.credit_score}"`, `"${rec.income}"`, `"${rec.loan_amount}"`, `"${rec.existing_debt}"`, `"${rec.employment_status}"`, `"${rec.loan_term}"`, `"${rec.decision}"`, `"${(rec.confidence * 100).toFixed(2)}%"`, `"${rec.status}"`, `"${rec.input_hash}"`, `"${rec.execution_hash}"`, `"${rec.blockchain_tx_id}"`
      ].join(","))
    ];
    const blob = new Blob([csvRows.join("\n")], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a'); a.style.display = 'none'; a.href = url; a.download = `AI_Audit_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a); a.click(); window.URL.revokeObjectURL(url);
  };

  const getStatusBadge = (status) => {
    const base = "px-3 py-1.5 rounded-xl text-xs font-black uppercase tracking-tight flex items-center gap-1.5 border";
    switch (status) {
      case 'Verified': return <span className={`${base} bg-emerald-50 text-emerald-700 border-emerald-100`}><ShieldCheck className="w-3.5 h-3.5"/> Verified</span>;
      case 'Anchored': return <span className={`${base} bg-indigo-50 text-indigo-700 border-indigo-100`}><Blocks className="w-3.5 h-3.5"/> Anchored</span>;
      case 'Anchoring': return <span className={`${base} bg-amber-50 text-amber-700 border-amber-100`}><Activity className="w-3.5 h-3.5 animate-pulse"/> Anchoring</span>;
      case 'Tampering Detected': return <span className={`${base} bg-rose-50 text-rose-700 border-rose-400 animate-bounce`}><AlertTriangle className="w-3.5 h-3.5"/> Breach Detected</span>;
      default: return <span className={`${base} bg-slate-50 text-slate-500 border-slate-100`}>{status}</span>;
    }
  };

  const labelClass = 'block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2';
  const fieldClass = 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl focus:ring-4 focus:ring-indigo-50 outline-none text-sm font-bold text-slate-700 transition-all';

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 p-8 font-sans selection:bg-indigo-100">
      {/* Header */}
      <header className="max-w-7xl mx-auto mb-10 flex justify-between items-end">
        <div>
          <div className="flex items-center gap-4 mb-2">
             <div className="bg-indigo-600 p-3 rounded-2xl shadow-xl shadow-indigo-100">
                <ShieldCheck className="w-8 h-8 text-white" />
             </div>
             <h1 className="text-4xl font-black text-slate-900 tracking-tighter">AI Audit <span className="text-indigo-600">PRO</span></h1>
          </div>
          <p className="text-slate-400 font-bold uppercase tracking-widest text-[10px]">Immutable Accountability Protocol v2.4</p>
        </div>
        
        <div className="flex items-center gap-4">
          <button 
            onClick={downloadCSV}
            className="group bg-white hover:bg-slate-900 hover:text-white text-slate-700 font-black py-4 px-8 rounded-3xl border border-slate-200 shadow-xl shadow-slate-200/50 transition-all duration-300 flex items-center gap-3 text-xs uppercase tracking-widest"
          >
            <Database className="w-4 h-4 group-hover:scale-110 transition-transform" />
            Export Audit Trial
          </button>
          
          <div className={`px-8 py-4 rounded-3xl font-black flex items-center gap-3 shadow-xl border transition-all ${
              systemStatus === 'SAFE' ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-rose-50 text-rose-700 border-rose-100 animate-pulse'
            }`}>
            <div className={`w-3 h-3 rounded-full ${systemStatus === 'SAFE' ? 'bg-emerald-500' : 'bg-rose-500'}`}></div>
            <span className="uppercase tracking-[0.2em] text-[10px]">{systemStatus} OPERATIONAL</span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto space-y-10">
        {/* Suspicious Behavior Alert */}
        {stats.behavior_analysis?.is_suspicious && (
          <div className="bg-rose-600 p-8 rounded-[40px] shadow-2xl shadow-rose-200 text-white flex items-center justify-between border-4 border-white animate-pulse">
            <div className="flex items-center gap-6">
              <div className="bg-white/20 p-4 rounded-3xl backdrop-blur-md">
                <AlertTriangle className="w-10 h-10" />
              </div>
              <div>
                <h3 className="text-2xl font-black uppercase tracking-tighter text-white">Suspicious AI Behavior Detected</h3>
                <p className="text-rose-100 font-bold text-xs uppercase tracking-widest">{stats.behavior_analysis.reason}</p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="bg-white/10 px-6 py-3 rounded-2xl backdrop-blur-sm border border-white/20">
                <p className="text-[10px] font-black uppercase text-rose-200 mb-1">Recent Rejection Rate</p>
                <p className="text-xl font-black text-white">{stats.behavior_analysis.rejection_rate}%</p>
              </div>
              <div className="bg-white/10 px-6 py-3 rounded-2xl backdrop-blur-sm border border-white/20">
                <p className="text-[10px] font-black uppercase text-rose-200 mb-1">Consecutive Count</p>
                <p className="text-xl font-black text-white">{stats.behavior_analysis.consecutive_rejections}</p>
              </div>
            </div>
          </div>
        )}

        {/* Tab Switcher */}
        <nav className="flex p-2 bg-slate-200/50 backdrop-blur-xl rounded-[32px] w-fit border border-slate-200/50 shadow-inner">
           {tabs.map(tab => (
             <button
               key={tab.id}
               onClick={() => setActiveTab(tab.id)}
               className={`px-10 py-4 rounded-[24px] font-black text-[10px] uppercase tracking-[0.2em] transition-all duration-500 flex items-center gap-3 ${
                 activeTab === tab.id 
                   ? 'bg-white text-indigo-600 shadow-2xl shadow-indigo-100 scale-105' 
                   : 'text-slate-500 hover:text-slate-800'
               }`}
             >
               {tab.icon}
               {tab.label}
             </button>
           ))}
        </nav>

        {/* --- Overview Tab --- */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-10 animate-in fade-in slide-in-from-bottom-8 duration-700">
            <div className="xl:col-span-4 space-y-6">
               {[
                 { label: 'Total Executions', val: stats.total_applicants, icon: <Users/>, col: 'indigo' },
                 { label: 'Integrity Score', val: '99.9%', icon: <ShieldCheck/>, col: 'emerald' },
                 { label: 'Approval Index', val: `${stats.loan_approval_rate}%`, icon: <Activity/>, col: 'blue' },
                 { label: 'Recent Rejection Rate', val: `${stats.behavior_analysis?.rejection_rate || 0}%`, icon: <Bug/>, col: stats.behavior_analysis?.is_suspicious ? 'rose' : 'slate' },
                 { label: 'Consecutive Rejections', val: stats.behavior_analysis?.consecutive_rejections || 0, icon: <AlertTriangle/>, col: stats.behavior_analysis?.is_suspicious ? 'rose' : 'slate' }
               ].map((s, i) => (
                 <div key={i} className={`bg-white p-8 rounded-[40px] shadow-sm border border-slate-100 flex items-center gap-6 transition-all ${s.col === 'rose' ? 'border-rose-200 bg-rose-50/20' : ''}`}>
                   <div className={`p-4 rounded-3xl bg-${s.col === 'slate' ? 'slate' : s.col}-50 text-${s.col === 'slate' ? 'slate' : s.col}-600 shadow-inner`}>{s.icon}</div>
                   <div>
                     <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">{s.label}</p>
                     <h3 className="text-3xl font-black text-slate-900 tracking-tight">{s.val}</h3>
                   </div>
                 </div>
               ))}
            </div>
            
            <div className="xl:col-span-8 bg-white p-10 rounded-[48px] shadow-2xl shadow-slate-200/40 border border-slate-100">
               <div className="flex justify-between items-start mb-12">
                  <div className="flex items-center gap-3">
                     <BarChart3 className="w-6 h-6 text-indigo-600" />
                     <h2 className="font-black text-sm uppercase tracking-[0.2em] text-slate-800">Decision Landscape</h2>
                  </div>
               </div>
               <div className="h-80 w-full">
                 <ResponsiveContainer width="100%" height="100%">
                   <BarChart data={stats.credit_score_distribution}>
                     <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                     <XAxis dataKey="range" axisLine={false} tickLine={false} tick={{fontSize: 10, fontWeight: 'bold', fill: '#94a3b8'}} />
                     <YAxis axisLine={false} tickLine={false} tick={{fontSize: 10, fontWeight: 'bold', fill: '#94a3b8'}} unit="%" />
                     <Tooltip contentStyle={{borderRadius: '24px', border: 'none', boxShadow: '0 25px 50px -12px rgb(0 0 0 / 0.15)'}} cursor={{fill: '#f8fafc'}} />
                     <Bar dataKey="approval_rate" fill="#6366f1" radius={[12, 12, 0, 0]} barSize={50} />
                   </BarChart>
                 </ResponsiveContainer>
               </div>
            </div>
          </div>
        )}

        {/* --- Engine Tab --- */}
        {activeTab === 'engine' && (
          <div className="max-w-4xl mx-auto animate-in fade-in slide-in-from-bottom-8 duration-700">
            <div className="bg-white p-16 rounded-[64px] shadow-2xl shadow-indigo-100 border border-indigo-50 relative overflow-hidden">
               <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-50 rounded-full blur-[120px] -mr-48 -mt-48 opacity-40"></div>
               <div className="relative">
                  <div className="flex items-center gap-5 mb-12">
                    <div className="bg-indigo-600 p-4 rounded-3xl shadow-xl shadow-indigo-200 text-white"><Activity className="w-8 h-8"/></div>
                    <div>
                      <h2 className="text-3xl font-black text-slate-900 tracking-tight">AI Decision Engine</h2>
                      <p className="text-slate-400 text-xs font-bold uppercase tracking-[0.2em] mt-1">Algorithmic Risk Assessment</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                    {['credit_score', 'income', 'loan_amount', 'existing_debt'].map(f => (
                      <div key={f}>
                        <label className={labelClass}>{f.replace('_', ' ')}</label>
                        <input type="number" value={formData[f]} onChange={(e) => setFormData({...formData, [f]: e.target.value})} className={fieldClass} />
                      </div>
                    ))}
                    <div>
                      <label className={labelClass}>Employment</label>
                      <select className={fieldClass} value={formData.employment_status} onChange={(e) => setFormData({...formData, employment_status: e.target.value})}>
                        <option value="employed">Employed</option>
                        <option value="self_employed">Self Employed</option>
                        <option value="unemployed">Unemployed</option>
                      </select>
                    </div>
                    <div>
                      <label className={labelClass}>Loan Term</label>
                      <input type="number" value={formData.loan_term} onChange={(e) => setFormData({...formData, loan_term: e.target.value})} className={fieldClass} />
                    </div>
                  </div>

                  <button onClick={runDecision} disabled={submitting} className="w-full mt-16 bg-slate-900 hover:bg-indigo-600 text-white font-black py-7 rounded-[32px] transition-all duration-500 shadow-2xl shadow-indigo-100 flex items-center justify-center gap-4 uppercase tracking-[0.3em] text-sm group">
                    {submitting ? 'Executing Protocol...' : 'Generate Verified Decision'}
                    <Database className="w-6 h-6 group-hover:rotate-12 transition-transform" />
                  </button>
               </div>

               {/* Result Card Integration */}
               {lastResult && (
                 <div className={`mt-12 p-10 rounded-[48px] border-2 animate-in zoom-in-95 slide-in-from-bottom-5 duration-700 ${
                   lastResult.decision === 'Loan Approved' ? 'bg-emerald-50/50 border-emerald-100' : 'bg-rose-50/50 border-rose-100'
                 }`}>
                   <div className="flex justify-between items-start mb-8">
                     <div>
                        <p className="text-[10px] font-black uppercase text-slate-400 tracking-[0.2em] mb-2">AI Protocol Verdict</p>
                        <h3 className={`text-4xl font-black tracking-tighter ${lastResult.decision === 'Loan Approved' ? 'text-emerald-700' : 'text-rose-700'}`}>
                          {lastResult.decision}
                        </h3>
                     </div>
                     <div className="bg-white px-4 py-2 rounded-2xl text-[10px] font-black uppercase tracking-[0.1em] border border-slate-100 shadow-sm">
                        Status: <span className={lastResult.status === 'Verified' ? 'text-emerald-600' : 'text-amber-600'}>{lastResult.status}</span>
                     </div>
                   </div>
                   
                   <div className="space-y-4">
                     <div className="flex justify-between items-end">
                       <div>
                          <p className="text-[10px] font-black uppercase text-slate-400 tracking-[0.2em] mb-1">Confidence Score</p>
                          <p className="text-xl font-black text-slate-800">{(lastResult.confidence * 100).toFixed(1)}% Trust Accuracy</p>
                       </div>
                       <button onClick={() => setActiveTab('audit')} className="text-[10px] font-black text-indigo-600 uppercase tracking-widest hover:underline">View in Audit Ledger →</button>
                     </div>
                     <div className="h-4 bg-slate-200/50 rounded-full overflow-hidden p-1 border border-white">
                        <div 
                          className={`h-full rounded-full transition-all duration-[1500ms] ${lastResult.decision === 'Loan Approved' ? 'bg-emerald-500 shadow-lg shadow-emerald-200' : 'bg-rose-500 shadow-lg shadow-rose-200'}`} 
                          style={{ width: `${(lastResult.confidence * 100).toFixed(0)}%` }}
                        ></div>
                     </div>
                   </div>
                 </div>
               )}
            </div>
          </div>
        )}

        {/* --- Audit Tab --- */}
        {activeTab === 'audit' && (
          <div className="animate-in fade-in slide-in-from-bottom-8 duration-700">
            <div className="bg-white rounded-[56px] shadow-2xl shadow-slate-200/40 border border-slate-100 overflow-hidden">
              <div className="p-12 border-b border-slate-50 flex justify-between items-end bg-slate-50/30">
                  <div>
                    <h2 className="text-3xl font-black text-slate-900 tracking-tight">Audit Trail Ledger</h2>
                    <p className="text-slate-400 text-xs font-bold uppercase tracking-[0.2em] mt-1">Immutable Execution Evidence</p>
                  </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="bg-slate-50/50">
                      <th className="px-12 py-8 text-left text-[10px] font-black text-slate-400 uppercase tracking-widest">Execution Identity</th>
                      <th className="px-8 py-8 text-left text-[10px] font-black text-slate-400 uppercase tracking-widest">AI Verdict</th>
                      <th className="px-8 py-8 text-left text-[10px] font-black text-slate-400 uppercase tracking-widest">Integrity Hash</th>
                      <th className="px-8 py-8 text-left text-[10px] font-black text-slate-400 uppercase tracking-widest">Status</th>
                      <th className="px-12 py-8 text-right text-[10px] font-black text-slate-400 uppercase tracking-widest">Transparency Control</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {records.map((rec) => (
                      <tr key={rec.decision_id} className="hover:bg-slate-50/50 transition-colors group">
                        <td className="px-12 py-8">
                           <div className="flex flex-col gap-1">
                             <span className="font-mono text-xs font-black text-indigo-600">{rec.decision_id}</span>
                             <span className="text-[10px] text-slate-400 font-bold uppercase">{new Date(rec.timestamp).toLocaleDateString()}</span>
                           </div>
                        </td>
                        <td className="px-8 py-8">
                           <span className={`text-sm font-black ${rec.decision === 'Loan Approved' ? 'text-emerald-600' : 'text-rose-600'}`}>{rec.decision}</span>
                        </td>
                        <td className="px-8 py-8">
                           <div className="flex items-center gap-3">
                              <div className="w-20 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                 <div className="h-full bg-indigo-500" style={{width: `${rec.confidence * 100}%`}}></div>
                              </div>
                              <span className="font-mono text-[9px] text-slate-400 uppercase">{rec.execution_hash.substring(0,8)}...</span>
                           </div>
                        </td>
                        <td className="px-8 py-8">{getStatusBadge(rec.status)}</td>
                        <td className="px-12 py-8 text-right space-x-3">
                            <button onClick={() => verifyRecord(rec.decision_id)} disabled={verifying === rec.decision_id} 
                                    className="bg-white border border-slate-200 hover:border-indigo-600 text-indigo-600 px-6 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all shadow-sm hover:shadow-indigo-100 italic">
                              {verifying === rec.decision_id ? 'Verifying...' : 'Validate Ledger'}
                            </button>
                            <button onClick={() => openTamperModal(rec)} className="bg-slate-50 hover:bg-rose-50 text-slate-300 hover:text-rose-600 p-3 rounded-2xl transition-all"><Bug className="w-5 h-5" /></button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Modal & Toast remain unchanged logic-wise */}
      {tamperingRecord && (
        <div className="fixed inset-0 bg-slate-900/80 backdrop-blur-md z-[500] flex items-center justify-center p-6 animate-in fade-in duration-300">
          <div className="bg-white rounded-[56px] shadow-2xl w-full max-w-2xl overflow-hidden animate-in zoom-in-95 duration-300">
            <div className="bg-rose-600 p-10 text-white flex justify-between items-center">
              <div className="flex items-center gap-4"><Bug className="w-8 h-8" /><h3 className="text-2xl font-black uppercase tracking-tight">System Breach Simulation</h3></div>
              <button onClick={() => setTamperingRecord(null)} className="hover:bg-white/20 p-2 rounded-full"><X className="w-8 h-8" /></button>
            </div>
            <div className="p-12 space-y-10">
              <div className="grid grid-cols-2 gap-8">
                <div className="col-span-2"><label className={labelClass}>Decision</label><select value={tamperForm.decision} onChange={e=>setTamperForm({...tamperForm, decision:e.target.value})} className={fieldClass}><option value="Loan Approved">Loan Approved</option><option value="Loan Rejected">Loan Rejected</option></select></div>
                {['confidence', 'income', 'loan_amount', 'existing_debt'].map(f=>(<div key={f}><label className={labelClass}>{f}</label><input type="number" step="0.01" value={tamperForm[f]} onChange={e=>setTamperForm({...tamperForm, [f]:f==='loan_term'?parseInt(e.target.value):parseFloat(e.target.value)})} className={fieldClass}/></div>))}
              </div>
              <button onClick={handleTamper} className="w-full bg-rose-600 hover:bg-rose-700 text-white font-black py-6 rounded-[32px] shadow-2xl shadow-rose-200 uppercase tracking-widest">Execute Manual Tamper</button>
            </div>
          </div>
        </div>
      )}

      {verifyResult && (
        <div className={`fixed bottom-10 right-10 p-10 rounded-[48px] shadow-2xl border-2 z-[600] animate-in slide-in-from-right-10 duration-700 ${verifyResult.result ? 'bg-white border-emerald-500' : 'bg-white border-rose-500'}`}>
           <div className="flex gap-6">
              <div className={`p-4 rounded-3xl ${verifyResult.result ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'}`}>{verifyResult.result ? <ShieldCheck className="w-10 h-10"/> : <ShieldAlert className="w-10 h-10"/>}</div>
              <div>
                <h4 className="font-black uppercase tracking-widest text-lg mb-2">{verifyResult.result ? 'Ledger Verified' : 'Breach Detected'}</h4>
                <p className="max-w-xs text-xs text-slate-500 font-bold mb-6">{verifyResult.message}</p>
                <div className="bg-slate-50 p-4 rounded-2xl border border-slate-100 font-mono text-[9px] text-slate-400 break-all">{verifyResult.recomputed_hash}</div>
              </div>
           </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
