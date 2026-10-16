import React, { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import ResumeTemplate from '../components/ResumeTemplate';
import { ArrowLeft, Loader, Download, Edit3, Save, Check } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import './ResumeBuilder.css';

const parseResumeText = (text) => {
  if (!text) return {};
  
  const headers = [
    'PROFILE', 'SUMMARY', 'OBJECTIVE',
    'EDUCATION', 'ACADEMIC BACKGROUND',
    'PROJECTS', 'ACADEMIC PROJECTS',
    'EXPERIENCE', 'WORK EXPERIENCE', 'EMPLOYMENT', 'POSITIONS OF RESPONSIBILITY', 'INTERNSHIPS',
    'SKILLS', 'TECHNICAL SKILLS',
    'CERTIFICATIONS & QUALIFICATIONS', 'CERTIFICATIONS', 'CERTIFICATES', 'QUALIFICATIONS',
    'ACHIEVEMENTS', 'AWARDS', 'HONORS'
  ];
  
  const regexStr = "\\b(" + headers.join('|') + ")\\b(?:\\s|\\n|$)";
  const regex = new RegExp(regexStr, "g");
  
  let matches = [];
  let match;
  while ((match = regex.exec(text)) !== null) {
      if (match[0].toUpperCase() === match[0] || match[0].length > 4) {
          matches.push({
              title: match[1].toUpperCase(),
              index: match.index
          });
      }
  }
  
  if (matches.length === 0) {
      return { RAW: text };
  }
  
  const sections = {};
  for (let i = 0; i < matches.length; i++) {
      const start = matches[i].index + matches[i].title.length;
      const end = (i + 1 < matches.length) ? matches[i + 1].index : text.length;
      const content = text.slice(start, end).trim();
      
      let key = 'EXPERIENCE';
      const t = matches[i].title;
      if (t.includes('PROJECT')) key = 'PROJECTS';
      else if (t.includes('EDUCATION') || t.includes('ACADEMIC B')) key = 'EDUCATION';
      else if (t.includes('SKILL')) key = 'SKILLS';
      else if (t.includes('CERTIF') || t.includes('QUALIF')) key = 'CERTIFICATIONS';
      else if (t.includes('ACHIEVE') || t.includes('AWARD') || t.includes('HONOR')) key = 'ACHIEVEMENTS';
      else if (t.includes('PROFILE') || t.includes('SUMMARY') || t.includes('OBJECTIVE')) key = 'SUMMARY';
      
      if (!sections[key]) sections[key] = content;
      else sections[key] += "\n" + content;
  }
  
  // Restore PyPDF2 smashed bullets by enforcing newlines
  for (let k in sections) {
      sections[k] = sections[k].replace(/([^\\n])([◦•])/g, "$1\n$2");
  }

  return sections;
};

const parseSubSections = (blockText) => {
    const lines = blockText.split('\n');
    const items = [];
    let currentItem = null;

    for (let i = 0; i < lines.length; i++) {
       let line = lines[i].trim();
       if (!line) continue;
       
       if (!line.startsWith('◦') && !line.startsWith('•') && !line.startsWith('-')) {
           if (currentItem && (currentItem.title || currentItem.text)) items.push(currentItem);
           
           const dateMatch = line.match(/(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*,\s*\d{4}/i);
           let title = line;
           let date = '';
           if (dateMatch) {
               date = dateMatch[0];
               title = line.replace(date, '').trim();
           } else {
               const yearMatch = line.match(/\b(19|20)\d{2}\s*(-\s*(19|20)\d{2}|Present)?\b/i);
               if (yearMatch) {
                  date = yearMatch[0];
                  title = line.replace(yearMatch[0], '').trim();
               }
           }
           
           currentItem = { title, date, text: '' };
       } else {
           if (!currentItem) currentItem = { title: '', date: '', text: '' };
           currentItem.text += (currentItem.text ? '\n' : '') + line;
       }
    }
    if (currentItem && (currentItem.title || currentItem.text)) items.push(currentItem);
    return items;
};

const ResumeBuilder = () => {
  const [profileData, setProfileData] = useState(null);
  const [fullProfileData, setFullProfileData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [savingFast, setSavingFast] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [error, setError] = useState(null);
  const [draftNameInput, setDraftNameInput] = useState('');
  
  const [searchParams, setSearchParams] = useSearchParams();
  const draftIdParam = searchParams.get('draftId');
  
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const USER_ID = localStorage.getItem('user_id');
        if (!USER_ID) {
          setError("User not logged in");
          setLoading(false);
          return;
        }
        const response = await fetch(`http://localhost:8000/profile/${USER_ID}`);
        if (!response.ok) throw new Error('Failed to fetch profile data');
        const data = await response.json();
        
        if (!data.profile_data) {
          setError("Profile not found. Please complete your profile first.");
          setLoading(false);
          return;
        }
        
        const raw = data.profile_data || {};
        setFullProfileData(raw);

        // Check if we requested a specific draft wrapper context
        if (draftIdParam && raw.resume_drafts) {
           const specificDraft = raw.resume_drafts.find(d => String(d.id) === draftIdParam);
           if (specificDraft && specificDraft.data) {
               setProfileData(specificDraft.data);
               setDraftNameInput(specificDraft.name || '');
               setLoading(false);
               return; // Skip normal derivation parsing logic!
           }
        }

        let summaryText = raw.professionalSummary || raw.professional_summary || raw.summary || "";
        const parsedResume = raw.resumeText ? parseResumeText(raw.resumeText) : {};
        
        const transformed = {
          basic_info: {
            first_name: raw.personalDetails?.firstName || "First",
            last_name: raw.personalDetails?.lastName || "Last",
            email: USER_ID,
            phone: raw.personalDetails?.phone || "",
            location: (raw.selectedLocations && raw.selectedLocations.length > 0) ? raw.selectedLocations.join(', ') : "Location Setup Needed",
            linkedin: raw.personalDetails?.linkedin || "",
            github: raw.personalDetails?.github || ""
          },
          education: [],
          skills: raw.skills || [],
          achievements: [],
          certificates: [],
          experience: [],
          projects: [],
          professional_summary: summaryText
        };

        // 1. Manual Achievements
        if (raw.achievements) {
            transformed.achievements.push(...raw.achievements.split('\n').filter(a => a.trim() !== ''));
        }

        // 2. Manual Projects
        if (raw.projects && raw.projects.length > 0) {
            raw.projects.forEach(p => {
                transformed.projects.push({
                    title: p.title,
                    duration: p.duration,
                    description: p.description,
                    tech: p.tech
                });
            });
        }

        // 3. Manual Certificates (pass raw data for backend course name extraction)
        if (raw.savedCertificates && raw.savedCertificates.length > 0) {
            raw.savedCertificates.forEach(cert => {
                // Use filename as fallback display name; the backend enhancer
                // will extract the real course name from extracted_text
                const fallbackName = cert.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, ' ');
                transformed.certificates.push({
                    display_name: fallbackName,
                    extracted_text: cert.extracted_text || "",
                    filename: cert.name
                });
            });
        } else if (raw.certificatesText) {
            raw.certificatesText.split('\n').filter(c => c.trim() !== '').forEach(name => {
                transformed.certificates.push({ display_name: name, extracted_text: "", filename: "" });
            });
        }

        const hasManualEdu = !!raw.education?.tenth?.institute || !!raw.education?.graduation?.institute;

        if (parsedResume.EDUCATION && !hasManualEdu) {
            const parsedEdu = parseSubSections(parsedResume.EDUCATION);
            if (parsedEdu.length === 0) {
                transformed.education.push({
                   degree: "",
                   institution: parsedResume.EDUCATION,
                   grad_year: "",
                   score: ""
                });
            } else {
                parsedEdu.forEach(e => {
                   let degreeText = e.title;
                   let instText = e.text;
                   if (!degreeText && e.text) {
                       const parts = e.text.split('\n');
                       degreeText = parts[0];
                       instText = parts.slice(1).join('\n');
                   }
                   transformed.education.push({
                       degree: degreeText || "",
                       institution: instText,
                       grad_year: e.date,
                       score: ""
                   });
                });
            }
        }

        // Merge Parsed Projects if manual list is empty
        if (parsedResume.PROJECTS && transformed.projects.length === 0) {
            const parsedProjs = parseSubSections(parsedResume.PROJECTS);
            parsedProjs.forEach(p => {
               transformed.projects.push({
                   title: p.title,
                   duration: p.date,
                   description: p.text
               });
            });
        }

        // Merge Parsed Experience
        if (parsedResume.EXPERIENCE) {
            const parsedExps = parseSubSections(parsedResume.EXPERIENCE);
            parsedExps.forEach(e => {
               transformed.experience.push({
                   title: e.title,
                   company: "",
                   duration: e.date,
                   description: e.text
               });
            });
        }

        if (parsedResume.CERTIFICATIONS && transformed.certificates.length === 0) {
            const certs = parsedResume.CERTIFICATIONS.split('\n').filter(c => c.trim() !== '');
            transformed.certificates.push(...certs);
        }
        
        if (parsedResume.ACHIEVEMENTS && transformed.achievements.length === 0) {
            const achs = parsedResume.ACHIEVEMENTS.split('\n').filter(a => a.trim() !== '');
            transformed.achievements.push(...achs);
        }

        if (parsedResume.RAW) {
            transformed.professional_summary += (transformed.professional_summary ? "\n" : "") + parsedResume.RAW;
        }

        if (parsedResume.SUMMARY && !transformed.professional_summary) {
            transformed.professional_summary = parsedResume.SUMMARY;
        }

        if (raw.education?.graduation?.institute) {
          transformed.education.push({
            degree: raw.education.graduation.board || "Degree",
            institution: raw.education.graduation.institute,
            grad_year: raw.education.graduation.passoutYear,
            score: raw.education.graduation.percentage
          });
        }
        if (raw.education?.twelfth?.institute) {
          transformed.education.push({
            degree: "12th Grade",
            institution: raw.education.twelfth.institute,
            grad_year: raw.education.twelfth.passoutYear,
            score: raw.education.twelfth.percentage
          });
        }
        if (raw.education?.tenth?.institute) {
          transformed.education.push({
            degree: "10th Grade",
            institution: raw.education.tenth.institute,
            grad_year: raw.education.tenth.passoutYear,
            score: raw.education.tenth.percentage
          });
        }

        // --- OFFLINE ENHANCEMENT PIPELINE ---
        try {
            const enrichResponse = await fetch(`http://localhost:8000/enhance_profile`, {
               method: 'POST',
               headers: { 'Content-Type': 'application/json' },
               body: JSON.stringify({ ...raw, ...transformed, user_id: USER_ID })
            });
            if (enrichResponse.ok) {
                const enrichData = await enrichResponse.json();
                if (enrichData.status === "success") {
                    setProfileData(enrichData.enhanced_profile);
                    return; // Successfully set enhanced profile
                }
            }
        } catch (enrichErr) {
            console.warn("Offline enhancement failed, falling back to raw data", enrichErr);
        }
        
        // Fallback to unenhanced data
        setProfileData(transformed);
        
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, []);

  const handleDownload = () => {
    window.print();
  };

  const handleSaveDraft = async () => {
    if (!profileData || !fullProfileData) return;
    setSavingFast(true);
    
    // Check if we are updating an existing draft
    const existingDraft = draftIdParam ? fullProfileData.resume_drafts?.find(d => String(d.id) === draftIdParam) : null;
    const isUpdating = !!existingDraft;
    
    const draftIdStr = isUpdating ? draftIdParam : Date.now().toString();
    const finalDraftName = draftNameInput.trim() || (isUpdating ? existingDraft.name : `Resume Draft - ${new Date().toLocaleDateString()}`);

    const newDraft = {
       id: draftIdStr,
       name: finalDraftName,
       timestamp: new Date().toISOString(),
       data: profileData
    };
    
    let drafts = fullProfileData.resume_drafts || [];
    if (isUpdating) {
        drafts = drafts.map(d => String(d.id) === draftIdParam ? newDraft : d);
    } else {
        drafts = [...drafts, newDraft];
    }
    
    const updatedFullProfile = {
      ...fullProfileData,
      resume_drafts: drafts
    };

    try {
      const USER_ID = localStorage.getItem('user_id');
      await fetch(`http://localhost:8000/profile/${USER_ID}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedFullProfile),
      });
      setFullProfileData(updatedFullProfile);
      setSavedSuccess(true);
      
      // Update URL to remain in this draft's context if it was new
      if (!isUpdating) {
         setSearchParams({ draftId: draftIdStr });
      }

      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      console.error("Failed to save draft", err);
    } finally {
      setSavingFast(false);
    }
  };

  return (
    <div className="dashboard-layout animate-fade-in">
      <Navbar />
      
      <div className="dashboard-container" style={{ padding: '2rem', display: 'flex', gap: '2rem' }}>
        
        {/* LEFT COLUMN: CONTROLS */}
        <div className="no-print" style={{ flex: '1', maxWidth: '300px', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <Link to={draftIdParam ? "/resume-drafts" : "/dashboard"} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', textDecoration: 'none' }}>
            <ArrowLeft size={16} /> Back
          </Link>
          
          <div>
            <h1 style={{ fontSize: '1.8rem', fontWeight: 700, margin: '0 0 0.5rem 0', color: 'var(--text-primary)' }}>
              Resume Builder
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.4' }}>
              Your profile data has been automatically formatted into an ATS-friendly layout.
            </p>
          </div>

          <div style={{ background: 'var(--card-bg)', padding: '1.25rem', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: 0, color: 'var(--primary-color)' }}>
              <Edit3 size={18} /> Interactive Editor
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0 0 1rem 0' }}>
              Click directly on any text inside the resume preview to the right to modify it before downloading.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <button 
                onClick={handleDownload}
                disabled={loading || error || !profileData}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem',
                  background: 'var(--primary-color)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontWeight: 600,
                  cursor: (loading || error) ? 'not-allowed' : 'pointer',
                  opacity: (loading || error || !profileData) ? 0.6 : 1,
                  transition: 'all 0.2s'
                }}
              >
                <Download size={18} /> Download PDF
              </button>

              <div style={{ width: '100%', height: '1px', background: 'var(--border-color)', margin: '0.5rem 0' }}></div>
              
              <input
                type="text"
                placeholder={draftIdParam ? "Update draft name..." : "Name your draft..."}
                value={draftNameInput}
                onChange={(e) => setDraftNameInput(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  background: 'rgba(0,0,0,0.2)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  color: 'var(--text-primary)',
                  outline: 'none',
                  fontSize: '0.9rem',
                  boxSizing: 'border-box'
                }}
              />
              
              <button 
                onClick={handleSaveDraft}
                disabled={loading || error || !profileData || savingFast}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem',
                  background: savedSuccess ? '#10b981' : 'rgba(255, 255, 255, 0.05)',
                  color: savedSuccess ? 'white' : 'var(--text-primary)',
                  border: '1px solid',
                  borderColor: savedSuccess ? '#10b981' : 'rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  fontWeight: 600,
                  cursor: (loading || error || savingFast) ? 'not-allowed' : 'pointer',
                  opacity: (loading || error || !profileData || savingFast) ? 0.6 : 1,
                  transition: 'all 0.2s'
                }}
              >
                {savingFast ? <Loader className="animate-spin" size={18} /> : 
                 savedSuccess ? <Check size={18} /> : <Save size={18} />}
                {savedSuccess ? 'Draft Saved!' : 'Save Draft'}
              </button>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: RESUME PREVIEW */}
        <div className="print-wrapper" style={{ flex: '3', display: 'flex', justifyContent: 'center', overflowX: 'auto', paddingBottom: '2rem' }}>
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
              <Loader className="animate-spin" size={48} color="var(--primary-color)" />
            </div>
          ) : error ? (
            <div style={{ padding: '2rem', background: 'rgba(239, 68, 68, 0.1)', color: '#fca5a5', borderRadius: '12px', border: '1px solid #ef4444' }}>
              <h3>Error loading profile</h3>
              <p>{error}</p>
            </div>
          ) : profileData ? (
            <div className="print-surface-inner" style={{ filter: 'drop-shadow(0 20px 30px rgba(0,0,0,0.5))', transformOrigin: 'top center', transform: 'scale(0.95)' }}>
              <ResumeTemplate data={profileData} onUpdate={(newData) => setProfileData(newData)} />
            </div>
          ) : null}
        </div>

      </div>
    </div>
  );
};

export default ResumeBuilder;
