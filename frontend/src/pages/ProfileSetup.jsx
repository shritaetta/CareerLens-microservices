import { useState, useRef, useEffect } from 'react';
import { UploadCloud, X, CheckCircle, File, Briefcase, GraduationCap, MapPin, Plus, Trash2, Eye } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { apiFetch, getFileUrl } from '../api';
import './ProfileSetup.css';

const PREDEFINED_SKILLS = [
  'Python', 'Java', 'C++', 'JavaScript', 'React', 'Node.js',
  'Machine Learning', 'Data Analysis', 'SQL', 'MongoDB',
  'AWS', 'Docker', 'Git', 'Figma', 'UI/UX Design', 'Project Management'
];

const DOMAINS = [
  'Agriculture', 'Automotive', 'Banking & Finance', 'Chemical Industry',
  'Construction & Infrastructure', 'Defence & Security', 'Education',
  'Energy (Oil, Gas & Renewables)', 'Healthcare & Pharma', 'Hospitality & Tourism',
  'IT & Software', 'Logistics & Supply Chain', 'Manufacturing & Production',
  'Media & Entertainment', 'Retail & Consumer Goods', 'Telecom',
  'Transportation & Aviation', 'Human Resources & Administration',
  'Sales & Marketing', 'Data & Analytics', 'Customer Service & BPO'
];

const ProfileSetup = () => {
  const navigate = useNavigate();

  // State
  const [personalDetails, setPersonalDetails] = useState({ firstName: '', lastName: '', phone: '' });

  const [education, setEducation] = useState({
    tenth: { institute: '', board: '', percentage: '', passoutYear: '' },
    twelfth: { institute: '', board: '', percentage: '', passoutYear: '' },
    graduation: { institute: '', board: '', percentage: '', passoutYear: '' }
  });

  const [skills, setSkills] = useState([]);
  const [skillInput, setSkillInput] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);

  const [achievements, setAchievements] = useState('');
  
  const [projects, setProjects] = useState([]);

  const [selectedDomains, setSelectedDomains] = useState([]);

  // Ephemeral states for file objects before uploading
  const [resume, setResume] = useState(null);
  const [certificates, setCertificates] = useState([]);

  // Persistent stored files
  const [savedResume, setSavedResume] = useState(null);
  const [savedCertificates, setSavedCertificates] = useState([]);

  const [isSaved, setIsSaved] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Preserve fields from the existing profile that ProfileSetup doesn't manage
  const [preservedFields, setPreservedFields] = useState({});

  // References for click outside pattern
  const suggestionsRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    const fetchProfile = async () => {
      const userId = localStorage.getItem('user_id');
      if (!userId) return; 
      try {
        const response = await apiFetch(`/api/profile/${userId}`);
        const data = await response.json();
        if (data.profile_data) {
          const pd = data.profile_data;
          if (pd.personalDetails) setPersonalDetails(pd.personalDetails);
          if (pd.education) setEducation(pd.education);
          if (pd.skills) setSkills(pd.skills);
          if (pd.achievements) setAchievements(pd.achievements);
          if (pd.projects) setProjects(pd.projects);
          if (pd.selectedDomains) setSelectedDomains(pd.selectedDomains);
          
          if (pd.savedResume) setSavedResume(pd.savedResume);
          if (pd.savedCertificates) setSavedCertificates(pd.savedCertificates);

          // Preserve fields that this form doesn't manage
          setPreservedFields({
            resume_drafts: pd.resume_drafts || [],
            liked_recommendations: pd.liked_recommendations || [],
            resumeText: pd.resumeText || "",
            professionalSummary: pd.professionalSummary || "",
            selectedLocations: pd.selectedLocations || [],
          });
        }
      } catch (err) {
        console.error("Failed to fetch profile", err);
      }
    };
    fetchProfile();
  }, []);

  // Handlers
  const handlePersonalChange = (e) => {
    setPersonalDetails({ ...personalDetails, [e.target.name]: e.target.value });
  };

  const handleEducationChange = (level, field, value) => {
    setEducation((prev) => ({
      ...prev,
      [level]: { ...prev[level], [field]: value }
    }));
  };

  const addSkill = (skill) => {
    if (skill && !skills.includes(skill)) {
      setSkills([...skills, skill]);
    }
    setSkillInput('');
    setShowSuggestions(false);
  };

  const removeSkill = (skillToRemove) => {
    setSkills(skills.filter(s => s !== skillToRemove));
  };

  const handleSkillKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addSkill(skillInput.trim());
    }
  };
  
  const addProject = () => {
    setProjects([...projects, { title: '', description: '', tech: '', duration: '' }]);
  };

  const updateProject = (index, field, value) => {
    const newProjects = [...projects];
    newProjects[index][field] = value;
    setProjects(newProjects);
  };

  const removeProject = (index) => {
    const newProjects = projects.filter((_, i) => i !== index);
    setProjects(newProjects);
  };

  const toggleMultiSelect = (item, selectedList, setFn, maxLimit = null) => {
    if (selectedList.includes(item)) {
      setFn(selectedList.filter(i => i !== item));
    } else {
      if (maxLimit && selectedList.length >= maxLimit) return;
      setFn([...selectedList, item]);
    }
  };

  const handleResumeUpload = (e) => {
    if (e.target.files && e.target.files[0]) {
      setResume(e.target.files[0]);
    }
  };

  const handleCertificatesUpload = (e) => {
    if (e.target.files) {
      setCertificates([...certificates, ...Array.from(e.target.files)]);
    }
  };

  const removeFile = (type, index = null) => {
    if (type === 'resume') setResume(null);
    if (type === 'cert') {
      const newCerts = [...certificates];
      newCerts.splice(index, 1);
      setCertificates(newCerts);
    }
  };

  const removeSavedFile = (type, index = null) => {
    if (type === 'resume') setSavedResume(null);
    if (type === 'cert') {
      const newCerts = [...savedCertificates];
      newCerts.splice(index, 1);
      setSavedCertificates(newCerts);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    const userId = localStorage.getItem('user_id') || 'default_user';

    let currentSavedResume = savedResume;
    let currentSavedCertificates = [...savedCertificates];

    try {
      // 1. Upload new physical files if present
      if (resume) {
        const formData = new FormData();
        formData.append('file', resume);
        const res = await apiFetch('/api/files/upload', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.url) {
           currentSavedResume = { name: data.filename, url: data.url };
        }
      }
      
      for (let i = 0; i < certificates.length; i++) {
        const formData = new FormData();
        formData.append('file', certificates[i]);
        const res = await apiFetch('/api/files/upload', { method: 'POST', body: formData });
        const data = await res.json();
        
        let extracted_text = "";
        if (certificates[i].name.toLowerCase().endsWith('.pdf')) {
            try {
               const extractForm = new FormData();
               extractForm.append('file', certificates[i]);
               const extRes = await apiFetch('/api/files/extract_pdf', { method: 'POST', body: extractForm });
               const extData = await extRes.json();
               if (extData.extracted_text) extracted_text = extData.extracted_text;
            } catch (e) { console.error("Extraction error", e); }
        }

        if (data.url) {
           currentSavedCertificates.push({ 
               name: data.filename, 
               url: data.url,
               extracted_text: extracted_text
           });
        }
      }
    } catch (err) {
        console.error("File upload failed", err);
    }

    const profileData = {
      ...preservedFields,
      personalDetails,
      education,
      skills,
      achievements,
      projects,
      selectedDomains,
      savedResume: currentSavedResume,
      savedCertificates: currentSavedCertificates
    };

    try {
      await apiFetch(`/api/profile/${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profileData)
      });
      // Synchronize state
      setResume(null);
      setCertificates([]);
      setSavedResume(currentSavedResume);
      setSavedCertificates(currentSavedCertificates);

      setIsSaving(false);
      setIsSaved(true);
      setTimeout(() => {
        setIsSaved(false);
        navigate('/dashboard');
      }, 2000);
    } catch (err) {
      console.error("Failed to save profile", err);
      setIsSaving(false);
    }
  };

  const filteredSkills = PREDEFINED_SKILLS.filter(s =>
    s.toLowerCase().includes(skillInput.toLowerCase()) && !skills.includes(s)
  );

  return (
    <div className="profile-container animate-fade-in">
      <div className="profile-card">
        <div className="profile-header">
          <h1>Build Your Profile</h1>
          <p>Help us find the perfect internship for you</p>
        </div>

        <form onSubmit={handleSubmit}>

          <h2 className="section-title">Personal Details</h2>
          <div className="grid-2">
            <div className="form-group">
              <label>First Name <span className="required-badge">Required</span></label>
              <input type="text" className="input-field" name="firstName" value={personalDetails.firstName} onChange={handlePersonalChange} required placeholder="Jane" />
            </div>
            <div className="form-group">
              <label>Last Name <span className="required-badge">Required</span></label>
              <input type="text" className="input-field" name="lastName" value={personalDetails.lastName} onChange={handlePersonalChange} required placeholder="Doe" />
            </div>
            <div className="form-group" style={{ gridColumn: '1 / -1' }}>
              <label>Phone Number <span className="required-badge">Required</span></label>
              <input type="tel" className="input-field" name="phone" value={personalDetails.phone} onChange={handlePersonalChange} required placeholder="+1 234 567 8900" />
            </div>
          </div>

          <h2 className="section-title"><GraduationCap size={20} /> Education History</h2>

          {/* 10th Grade (Required) */}
          <div className="education-block">
            <div className="education-title">
              10th Standard / Equivalent <span className="required-badge">Required</span>
            </div>
            <div className="grid-2">
              <input type="text" className="input-field" placeholder="Institute Name" required
                value={education.tenth.institute} onChange={(e) => handleEducationChange('tenth', 'institute', e.target.value)} />
              <input type="text" className="input-field" placeholder="Board (e.g. CBSE)" required
                value={education.tenth.board} onChange={(e) => handleEducationChange('tenth', 'board', e.target.value)} />
              <input type="text" className="input-field" placeholder="Percentage/CGPA" required
                value={education.tenth.percentage} onChange={(e) => handleEducationChange('tenth', 'percentage', e.target.value)} />
              <input type="number" className="input-field" placeholder="Passout Year" required
                value={education.tenth.passoutYear} onChange={(e) => handleEducationChange('tenth', 'passoutYear', e.target.value)} />
            </div>
          </div>

          {/* 12th Grade */}
          <div className="education-block">
            <div className="education-title">12th Standard / Diploma</div>
            <div className="grid-2">
              <input type="text" className="input-field" placeholder="Institute Name"
                value={education.twelfth.institute} onChange={(e) => handleEducationChange('twelfth', 'institute', e.target.value)} />
              <input type="text" className="input-field" placeholder="Board / Program"
                value={education.twelfth.board} onChange={(e) => handleEducationChange('twelfth', 'board', e.target.value)} />
              <input type="text" className="input-field" placeholder="Percentage/CGPA"
                value={education.twelfth.percentage} onChange={(e) => handleEducationChange('twelfth', 'percentage', e.target.value)} />
              <input type="number" className="input-field" placeholder="Passout Year"
                value={education.twelfth.passoutYear} onChange={(e) => handleEducationChange('twelfth', 'passoutYear', e.target.value)} />
            </div>
          </div>

          {/* Graduation */}
          <div className="education-block">
            <div className="education-title">Graduation (Degree)</div>
            <div className="grid-2">
              <input type="text" className="input-field" placeholder="Institute Name"
                value={education.graduation.institute} onChange={(e) => handleEducationChange('graduation', 'institute', e.target.value)} />
              <input type="text" className="input-field" placeholder="University / Program"
                value={education.graduation.board} onChange={(e) => handleEducationChange('graduation', 'board', e.target.value)} />
              <input type="text" className="input-field" placeholder="Percentage/CGPA"
                value={education.graduation.percentage} onChange={(e) => handleEducationChange('graduation', 'percentage', e.target.value)} />
              <input type="number" className="input-field" placeholder="Passout Year"
                value={education.graduation.passoutYear} onChange={(e) => handleEducationChange('graduation', 'passoutYear', e.target.value)} />
            </div>
          </div>

          <h2 className="section-title"><Briefcase size={20} /> Professional Summary</h2>

          <div className="form-group">
            <label>Skills <span className="required-badge">Required</span></label>
            <div className="skills-wrapper" ref={suggestionsRef}>
              <div className="skills-input-area" onClick={() => setShowSuggestions(true)}>
                {skills.map(skill => (
                  <span key={skill} className="skill-tag">
                    {skill}
                    <button type="button" className="skill-remove" onClick={(e) => { e.stopPropagation(); removeSkill(skill); }}>
                      <X size={14} />
                    </button>
                  </span>
                ))}
                <input
                  type="text"
                  className="skills-input"
                  placeholder={skills.length === 0 ? "Type a skill and hit Enter..." : "Add more..."}
                  value={skillInput}
                  onChange={(e) => { setSkillInput(e.target.value); setShowSuggestions(true); }}
                  onKeyDown={handleSkillKeyDown}
                />
              </div>

              {showSuggestions && (skillInput.length > 0 || filteredSkills.length > 0) && (
                <div className="suggestions-dropdown">
                  {filteredSkills.length > 0 ? (
                    filteredSkills.map(s => (
                      <div key={s} className="suggestion-item" onClick={() => addSkill(s)}>
                        {s}
                      </div>
                    ))
                  ) : (
                    skillInput.length > 0 && (
                      <div className="suggestion-item" onClick={() => addSkill(skillInput.trim())}>
                        Add "{skillInput}" as custom skill
                      </div>
                    )
                  )}
                </div>
              )}
            </div>
          </div>
          
          <h2 className="section-title">Projects / Experience</h2>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginBottom: '1.5rem' }}>
             {projects.map((proj, idx) => (
               <div key={idx} style={{ background: 'rgba(15, 23, 42, 0.4)', padding: '1.5rem', borderRadius: '16px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                     <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#e0e7ff' }}>Project/Experience #{idx + 1}</h3>
                     <button type="button" onClick={() => removeProject(idx)} style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: 'none', padding: '0.4rem 0.8rem', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Trash2 size={14} /> Remove
                     </button>
                  </div>
                  <div className="grid-2">
                     <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                        <label>Title</label>
                        <input type="text" className="input-field" placeholder="e.g. AI Internship Recommender" value={proj.title} onChange={(e) => updateProject(idx, 'title', e.target.value)} required />
                     </div>
                     <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                        <label>Description</label>
                        <textarea className="input-field" style={{ minHeight: '80px', resize: 'vertical' }} placeholder="Briefly describe your role or what you built..." value={proj.description} onChange={(e) => updateProject(idx, 'description', e.target.value)} required />
                     </div>
                     <div className="form-group">
                        <label>Technologies Used</label>
                        <input type="text" className="input-field" placeholder="e.g. React, Node.js, AWS" value={proj.tech} onChange={(e) => updateProject(idx, 'tech', e.target.value)} />
                     </div>
                     <div className="form-group">
                        <label>Duration / Dates</label>
                        <input type="text" className="input-field" placeholder="e.g. June 2023 - Present" value={proj.duration} onChange={(e) => updateProject(idx, 'duration', e.target.value)} />
                     </div>
                  </div>
               </div>
             ))}

             <button type="button" onClick={addProject} style={{ alignSelf: 'flex-start', background: 'rgba(99, 102, 241, 0.1)', color: '#818cf8', display: 'flex', alignItems: 'center', gap: '0.5rem', border: '1px dashed #818cf8', padding: '0.75rem 1.5rem', borderRadius: '8px', cursor: 'pointer', fontWeight: 600 }}>
                <Plus size={18} /> Add Project or Experience
             </button>
          </div>

          <h2 className="section-title">Achievements</h2>
          <div className="form-group">
            <label>Hackathons, Awards, and Certifications</label>
            <textarea
              className="input-field"
              style={{ minHeight: '100px', resize: 'vertical' }}
              placeholder="Highlight any of your key achievements, hackathons, open source contributions, or certifications here..."
              value={achievements}
              onChange={(e) => setAchievements(e.target.value)}
            />
          </div>

          <h2 className="section-title">Preferred Domains</h2>

          <div className="form-group">
            <label>Select domains of interest</label>
            <div className="tags-container">
              {DOMAINS.map(dom => (
                <div
                  key={dom}
                  className={`pill ${selectedDomains.includes(dom) ? 'selected' : ''}`}
                  onClick={() => toggleMultiSelect(dom, selectedDomains, setSelectedDomains)}
                >
                  {dom}
                </div>
              ))}
            </div>
          </div>

          <h2 className="section-title"><File size={20} /> Documents</h2>

          <div className="grid-2">
            <div>
              <label>Resume (Optional)</label>
              
              {savedResume && !resume && (
                <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.2)', padding: '1rem', borderRadius: '12px', marginBottom: '1rem' }}>
                   <p style={{ margin: '0 0 0.5rem 0', color: '#10b981', fontSize: '0.9rem', fontWeight: 600 }}>Currently Saved Resume:</p>
                   <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem' }}><File size={16} /> {savedResume.name}</span>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                         <a href={getFileUrl(savedResume.url)} target="_blank" rel="noreferrer" style={{ background: 'rgba(99, 102, 241, 0.1)', color: '#818cf8', padding: '0.4rem', borderRadius: '6px', display: 'flex' }}><Eye size={16} /></a>
                         <button type="button" onClick={() => removeSavedFile('resume')} style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: 'none', padding: '0.4rem', borderRadius: '6px', cursor: 'pointer', display: 'flex' }}><Trash2 size={16} /></button>
                      </div>
                   </div>
                </div>
              )}

              <div className="file-dropzone" onClick={() => document.getElementById('resume-upload').click()}>
                <UploadCloud className="file-icon" size={32} />
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{savedResume ? 'Upload a new resume to replace' : 'Click to upload Resume'}</p>
                <input id="resume-upload" type="file" hidden accept=".pdf,.doc,.docx" onChange={handleResumeUpload} />
              </div>
              {resume && (
                <div className="file-list">
                  <div className="file-item">
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}><File size={16} /> {resume.name} <span style={{ color: '#818cf8', fontSize: '0.75rem' }}>(New)</span></span>
                    <button type="button" className="skill-remove" onClick={() => removeFile('resume')}><X size={16} /></button>
                  </div>
                </div>
              )}
            </div>

            <div>
              <label>Certificates (Supports Multiple)</label>
              
              {savedCertificates.length > 0 && (
                <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.2)', padding: '1rem', borderRadius: '12px', marginBottom: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                   <p style={{ margin: 0, color: '#10b981', fontSize: '0.9rem', fontWeight: 600 }}>Saved Certificates:</p>
                   {savedCertificates.map((cert, idx) => (
                      <div key={`saved-cert-${idx}`} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(0,0,0,0.2)', padding: '0.5rem', borderRadius: '8px' }}>
                          <span style={{ color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}><File size={14} /> {cert.name}</span>
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                             <a href={getFileUrl(cert.url)} target="_blank" rel="noreferrer" style={{ background: 'rgba(99, 102, 241, 0.1)', color: '#818cf8', padding: '0.3rem', borderRadius: '6px', display: 'flex' }}><Eye size={14} /></a>
                             <button type="button" onClick={() => removeSavedFile('cert', idx)} style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: 'none', padding: '0.3rem', borderRadius: '6px', cursor: 'pointer', display: 'flex' }}><Trash2 size={14} /></button>
                          </div>
                      </div>
                   ))}
                </div>
              )}

              <div className="file-dropzone" onClick={() => document.getElementById('cert-upload').click()}>
                <UploadCloud className="file-icon" size={32} />
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Click to upload Certificates</p>
                <input id="cert-upload" type="file" hidden multiple accept=".pdf,.png,.jpg,.jpeg" onChange={handleCertificatesUpload} />
              </div>
              {certificates.length > 0 && (
                <div className="file-list">
                  {certificates.map((cert, idx) => (
                    <div key={idx} className="file-item">
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        <File size={16} style={{ flexShrink: 0 }} /> {cert.name} <span style={{ color: '#818cf8', fontSize: '0.75rem' }}>(New)</span>
                      </span>
                      <button type="button" className="skill-remove" onClick={() => removeFile('cert', idx)}><X size={16} /></button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {isSaved && (
            <div className="success-message">
              <CheckCircle size={20} /> Profile successfully saved!
            </div>
          )}

          <button type="submit" disabled={isSaving} className="primary-button" style={{ marginTop: '3rem' }}>
            {isSaving ? 'Processing & Saving...' : 'Save Profile'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ProfileSetup;
