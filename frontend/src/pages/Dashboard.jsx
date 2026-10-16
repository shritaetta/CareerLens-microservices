import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { apiFetch } from '../api';
import { 
  Sparkles, 
  FileText, 
  CheckSquare,
  Edit3,
  ChevronRight,
  GraduationCap,
  Briefcase,
  Globe,
  FolderOpen,
  Info
} from 'lucide-react';
import './Dashboard.css';

const Dashboard = () => {
  const [toasts, setToasts] = useState([]);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchProfile = async () => {
      const userId = localStorage.getItem('user_id') || 'default_user';
      try {
        const response = await apiFetch(`/api/profile/${userId}`);
        const data = await response.json();
        if (data.profile_data) {
          setProfile(data.profile_data);
        }
      } catch (err) {
        console.error("Failed to fetch profile", err);
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, []);

  const addToast = (message) => {
    const id = Date.now();
    setToasts([...toasts, { id, message }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 3000);
  };

  const handleAction = (featureName) => {
    if (featureName === 'Get Recommendations') {
      navigate('/recommendations');
    } else if (featureName === 'Generate Resume') {
      navigate('/resume-builder');
    } else if (featureName === 'Check ATS Score') {
      navigate('/ats-evaluation');
    } else {
      addToast(`${featureName} feature is coming soon!`);
    }
  };

  const highestEdu = profile?.education?.graduation?.institute 
    ? `${profile.education.graduation.board || 'Degree'}, ${profile.education.graduation.institute}`
    : profile?.education?.twelfth?.institute 
    ? `12th Grade, ${profile.education.twelfth.institute}`
    : profile?.education?.tenth?.institute 
    ? `10th Grade, ${profile.education.tenth.institute}`
    : 'Not set';

  return (
    <div className="dashboard-layout animate-fade-in">
      <Navbar />
      
      <div className="dashboard-container">
        <div className="dashboard-grid">
          
          {/* Left Column: Profile Summary Card */}
          <div className="profile-summary-section">
            <div className="summary-card">
              <div className="summary-header">
                <h2>Your Profile Summary</h2>
                <Link to="/profile-setup" className="edit-button">
                  <Edit3 size={16} /> Edit
                </Link>
              </div>

              {loading ? (
                <p>Loading profile...</p>
              ) : profile ? (
                <>
                  <div className="summary-group">
                    <h3><GraduationCap size={16} style={{display: 'inline', verticalAlign: 'text-bottom', marginRight:'4px'}}/> Highest Education</h3>
                    <p className="summary-text">{highestEdu}</p>
                  </div>

                  <div className="summary-group">
                    <h3><Briefcase size={16} style={{display: 'inline', verticalAlign: 'text-bottom', marginRight:'4px'}}/> Top Skills</h3>
                    <div className="summary-content">
                      {profile.skills && profile.skills.length > 0 ? (
                        profile.skills.map((skill, index) => (
                          <span key={index} className="pill selected">{skill}</span>
                        ))
                      ) : (
                        <p className="summary-text">No skills added yet</p>
                      )}
                    </div>
                  </div>

                  <div className="summary-group">
                    <h3><Globe size={16} style={{display: 'inline', verticalAlign: 'text-bottom', marginRight:'4px'}}/> Preferred Domains</h3>
                    <p className="summary-text">
                      {profile.selectedDomains && profile.selectedDomains.length > 0
                        ? profile.selectedDomains.join(', ')
                        : 'Not set'}
                    </p>
                  </div>

                  <div className="summary-group">
                    <h3><FolderOpen size={16} style={{display: 'inline', verticalAlign: 'text-bottom', marginRight:'4px'}}/> Total Projects</h3>
                    <p className="summary-text">
                      {profile.projects && profile.projects.length > 0
                        ? `${profile.projects.length} project(s) added`
                        : 'Not set'}
                    </p>
                  </div>
                </>
              ) : (
                <div style={{textAlign: 'center', padding: '2rem 0'}}>
                  <p style={{color: 'var(--text-secondary)', marginBottom: '1rem'}}>Profile not set up yet.</p>
                  <Link to="/profile-setup" className="primary-button" style={{display: 'inline-block', width: 'auto'}}>Complete Profile</Link>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Action Buttons */}
          <div className="actions-section">
            
            <div className="action-card" onClick={() => handleAction('Get Recommendations')}>
              <div className="action-icon-wrapper">
                <Sparkles size={32} />
              </div>
              <div className="action-details">
                <h3>Get Recommendations</h3>
                <p>Use AI to find your best-fit internships</p>
              </div>
              <ChevronRight className="action-arrow" size={24} />
            </div>

            <div className="action-card" onClick={() => handleAction('Generate Resume')}>
              <div className="action-icon-wrapper" style={{color: '#34d399', background: 'rgba(52, 211, 153, 0.15)'}}>
                <FileText size={32} />
              </div>
              <div className="action-details">
                <h3>Generate Resume</h3>
                <p>Create a professional ATS-friendly resume</p>
              </div>
              <ChevronRight className="action-arrow" size={24} />
            </div>

            <div className="action-card" onClick={() => handleAction('Check ATS Score')}>
              <div className="action-icon-wrapper" style={{color: '#f472b6', background: 'rgba(244, 114, 182, 0.15)'}}>
                <CheckSquare size={32} />
              </div>
              <div className="action-details">
                <h3>Check ATS Score</h3>
                <p>Evaluate your resume against job postings</p>
              </div>
              <ChevronRight className="action-arrow" size={24} />
            </div>

          </div>

        </div>
      </div>

      {/* Floating Toasts */}
      <div className="toast-container">
        {toasts.map(toast => (
          <div key={toast.id} className="toast">
            <Info size={20} style={{ color: 'var(--primary-color)' }} />
            {toast.message}
          </div>
        ))}
      </div>
    </div>
  );
};

export default Dashboard;
