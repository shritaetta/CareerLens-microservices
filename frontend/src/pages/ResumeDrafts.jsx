import React, { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import { ArrowLeft, FileText, Plus, Clock, FileDown, Loader, Trash2, Eye, Edit2, Check, X } from 'lucide-react';
import { Link } from 'react-router-dom';

const ResumeDrafts = () => {
  const [drafts, setDrafts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [fullProfileData, setFullProfileData] = useState(null);
  const [editingDraftId, setEditingDraftId] = useState(null);
  const [editingDraftName, setEditingDraftName] = useState("");

  const fetchDrafts = async () => {
    try {
      const userId = localStorage.getItem('user_id');
      if (!userId) throw new Error("User not logged in");

      const res = await fetch(`http://localhost:8000/profile/${userId}`);
      if (!res.ok) throw new Error('Failed to fetch profile');
      const data = await res.json();
      
      const raw = data.profile_data || {};
      setFullProfileData(raw);
      setDrafts(raw.resume_drafts || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteDraft = async (draftId) => {
    if (!fullProfileData) return;
    
    const currentDrafts = fullProfileData.resume_drafts || [];
    const newDrafts = currentDrafts.filter(d => d.id !== draftId);
    
    const newFullProfile = { ...fullProfileData, resume_drafts: newDrafts };
    setFullProfileData(newFullProfile);
    setDrafts(newDrafts);

    try {
      const userId = localStorage.getItem('user_id');
      await fetch(`http://localhost:8000/profile/${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newFullProfile),
      });
    } catch (err) {
      console.error('Failed to delete draft', err);
    }
  };

  const handleRenameDraft = async (draftId, newName) => {
    if (!fullProfileData || !newName.trim()) return;
    
    const currentDrafts = fullProfileData.resume_drafts || [];
    const newDrafts = currentDrafts.map(d => d.id === draftId ? { ...d, name: newName.trim() } : d);
    
    const newFullProfile = { ...fullProfileData, resume_drafts: newDrafts };
    setFullProfileData(newFullProfile);
    setDrafts(newDrafts);
    setEditingDraftId(null);

    try {
      const userId = localStorage.getItem('user_id');
      await fetch(`http://localhost:8000/profile/${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newFullProfile),
      });
    } catch (err) {
      console.error('Failed to rename draft', err);
    }
  };

  useEffect(() => {
    fetchDrafts();
  }, []);

  return (
    <div className="dashboard-layout animate-fade-in" style={{ minHeight: '100vh', background: 'var(--bg-color)' }}>
      <Navbar />
      <div className="dashboard-container" style={{ padding: '2rem', margin: '0 auto' }}>
        
        <div style={{ marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <Link to="/dashboard" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', textDecoration: 'none', fontWeight: 500 }}>
            <ArrowLeft size={18} /> Back
          </Link>
          <h1 style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0, display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <FileText size={28} style={{ color: '#6366f1' }} /> Resume Drafts
          </h1>
        </div>

        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
             <Loader className="animate-spin" size={48} color="#6366f1" />
          </div>
        ) : error ? (
           <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', color: '#fca5a5', padding: '1.5rem', borderRadius: '12px' }}>
              <p>Error: {error}</p>
           </div>
        ) : drafts.length === 0 ? (
          <div style={{
            background: 'rgba(30, 41, 59, 0.4)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(255, 255, 255, 0.05)',
            borderRadius: '16px',
            padding: '4rem 2rem',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1rem'
          }}>
            <div style={{ width: '80px', height: '80px', borderRadius: '50%', background: 'rgba(99, 102, 241, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1rem' }}>
              <FileText size={40} style={{ color: '#6366f1' }} />
            </div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>No Drafts Available</h2>
            <p style={{ color: 'var(--text-secondary)', maxWidth: '400px', lineHeight: 1.6 }}>
              You haven't saved any drafts yet. Once you build a resume and click Save Draft, it will appear here.
            </p>
            <Link to="/resume-builder" style={{ marginTop: '1.5rem', background: 'var(--primary-color)', border: 'none', padding: '0.75rem 1.5rem', borderRadius: '8px', color: 'white', fontWeight: 600, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
              <Plus size={18} /> Create New Builder
            </Link>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <Link to="/resume-builder" style={{ alignSelf: 'flex-start', background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', padding: '0.75rem 1rem', borderRadius: '8px', color: 'var(--text-primary)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.5rem', fontWeight: 500 }}>
               <Plus size={18} /> Open Interactive Builder
            </Link>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
              {[...drafts].reverse().map((draft, i) => (
                <div key={draft.id || i} style={{
                  background: 'var(--card-bg)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '12px',
                  padding: '1.5rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.75rem',
                  transition: 'transform 0.2s, box-shadow 0.2s'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--primary-color)' }}>
                    <FileDown size={20} />
                    {editingDraftId === draft.id ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', width: '100%' }}>
                        <input 
                          autoFocus
                          type="text" 
                          value={editingDraftName} 
                          onChange={(e) => setEditingDraftName(e.target.value)}
                          onKeyDown={(e) => {
                             if (e.key === 'Enter') handleRenameDraft(draft.id, editingDraftName);
                             if (e.key === 'Escape') setEditingDraftId(null);
                          }}
                          style={{
                            flex: 1,
                            padding: '0.25rem 0.5rem',
                            borderRadius: '4px',
                            border: '1px solid var(--primary-color)',
                            background: 'rgba(0,0,0,0.2)',
                            color: 'var(--text-primary)',
                            outline: 'none',
                            fontSize: '1rem'
                          }}
                        />
                        <button onClick={() => handleRenameDraft(draft.id, editingDraftName)} style={{ background: 'none', border: 'none', color: '#10b981', cursor: 'pointer', padding: '0.25rem', display: 'flex', alignItems: 'center' }}>
                          <Check size={18} />
                        </button>
                        <button onClick={() => setEditingDraftId(null)} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '0.25rem', display: 'flex', alignItems: 'center' }}>
                          <X size={18} />
                        </button>
                      </div>
                    ) : (
                      <>
                        <h3 style={{ margin: 0, fontSize: '1.1rem', color: 'var(--text-primary)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{draft.name || 'Saved Draft'}</h3>
                        <button onClick={() => { setEditingDraftId(draft.id); setEditingDraftName(draft.name || 'Saved Draft'); }} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '0.25rem', display: 'flex', alignItems: 'center', transition: 'color 0.2s' }} onMouseEnter={(e) => e.currentTarget.style.color = 'var(--primary-color)'} onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-secondary)'} title="Rename Draft">
                          <Edit2 size={16} />
                        </button>
                      </>
                    )}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                    <Clock size={14} />
                    <span>{new Date(draft.timestamp).toLocaleString()}</span>
                  </div>
                  <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.9rem', color: 'var(--text-secondary)', flex: 1 }}>
                     Candidate: {draft.data?.basic_info?.first_name} {draft.data?.basic_info?.last_name}
                  </p>
                  
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem', borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
                    <Link to={`/resume-builder?draftId=${draft.id}`} style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', padding: '0.5rem', background: 'rgba(99, 102, 241, 0.1)', color: 'var(--primary-color)', borderRadius: '6px', textDecoration: 'none', fontSize: '0.9rem', fontWeight: 500, transition: 'background 0.2s' }}>
                      <Eye size={16} /> View
                    </Link>
                    <button onClick={() => handleDeleteDraft(draft.id)} style={{ padding: '0.5rem 1rem', background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: 'none', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'background 0.2s' }}>
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResumeDrafts;
