import React, { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import InternshipCard from '../components/InternshipCard';
import FeedbackModal from '../components/FeedbackModal';
import { ArrowLeft, Loader } from 'lucide-react';
import { Link } from 'react-router-dom';
import { apiFetch } from '../api';

const Recommendations = () => {
  const [internships, setInternships] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [modalInternship, setModalInternship] = useState(null);

  // Dynamic profile loaded from backend
  const [userProfile, setUserProfile] = useState({});
  const [fullProfileData, setFullProfileData] = useState(null);

  const fetchRecommendations = async () => {
    setLoading(true);
    setError(null);
    try {
      const userId = localStorage.getItem('user_id');
      if (!userId) {
        setError("User not logged in");
        setLoading(false);
        return;
      }

      // 1. Fetch user's saved SQLite profile
      const profileRes = await apiFetch(`/api/profile/${userId}`);
      if (!profileRes.ok) throw new Error('Failed to fetch user profile');
      const profileDataRaw = await profileRes.json();
      const raw = profileDataRaw.profile_data || {};
      setFullProfileData(raw);

      const profilePayload = {
        skills: raw.skills || [],
        education: raw.education?.graduation?.institute ? `${raw.education.graduation.board || 'Degree'}, ${raw.education.graduation.institute}` : '',
        achievements: raw.achievements || '',
        resume_text: raw.resumeText || '',
        certificate_text: raw.certificatesText || ''
      };

      setUserProfile(profilePayload);

      // 2. Fetch semantic matches
      const response = await apiFetch('/api/ml/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profilePayload),
      });

      if (!response.ok) throw new Error('Failed to fetch recommendations');

      const data = await response.json();
      setInternships(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, []);

  const handleDislike = (internship) => {
    setModalInternship(internship);
  };

  const handleLike = async (internship, isLiked) => {
    if (!fullProfileData) return;
    
    const currentLiked = fullProfileData.liked_recommendations || [];
    let newLiked = [];
    if (isLiked) {
      if (!currentLiked.find(i => i.id === internship.id)) {
        newLiked = [...currentLiked, internship];
      } else {
        newLiked = currentLiked;
      }
    } else {
      newLiked = currentLiked.filter(i => i.id !== internship.id);
    }
    
    const newFullProfile = { ...fullProfileData, liked_recommendations: newLiked };
    setFullProfileData(newFullProfile);

    try {
      const userId = localStorage.getItem('user_id');
      await apiFetch(`/api/profile/${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newFullProfile),
      });
    } catch (err) {
      console.error('Failed to save liked recommendations:', err);
    }
  };

  const submitFeedback = async (reason, internship) => {
    // Optimistically remove card
    setInternships(prev => prev.filter(i => i.id !== internship.id));
    setModalInternship(null);
    
    try {
      await apiFetch('/api/ml/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          internship_id: String(internship.id),
          reason: reason,
          metadata: {
            location: internship.location || '',
            stipend: internship.stipend || '',
            domain: internship.domain || '',
            duration: internship.duration || ''
          }
        }),
      });
      // Automatically refetch next best constraint-filtered result
      fetchRecommendations();
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    }
  };

  return (
    <div className="dashboard-layout animate-fade-in">
      <Navbar />
      
      <div className="dashboard-container" style={{ paddingTop: '2rem' }}>
        <div style={{ marginBottom: '2rem' }}>
          <Link to="/dashboard" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', textDecoration: 'none', marginBottom: '1rem' }}>
            <ArrowLeft size={16} /> Back to Dashboard
          </Link>
          <h1 style={{ fontSize: '2rem', fontWeight: 700, backgroundImage: 'linear-gradient(to right, #818cf8, #c084fc)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Your Top Recommendations
          </h1>
          <p style={{ color: 'var(--text-secondary)' }}>Based on your skills: {userProfile.skills?.join(', ') || 'No skills listed'}</p>
        </div>

        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '300px' }}>
            <Loader className="animate-spin" size={48} color="var(--primary-color)" />
          </div>
        ) : error ? (
          <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', color: '#fca5a5', padding: '1.5rem', borderRadius: '12px' }}>
            <p><strong>Error:</strong> {error}</p>
            <p style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>Ensure the backend services are running.</p>
          </div>
        ) : internships.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', background: 'var(--card-bg)', borderRadius: '20px' }}>
            <p style={{ color: 'var(--text-secondary)' }}>No internships found matching your profile.</p>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.5rem' }}>
            {internships.map((internship, i) => (
              <InternshipCard 
                 key={internship.id || i} 
                 internship={internship} 
                 onDislike={handleDislike} 
                 onLike={handleLike}
                 isLikedInitial={Boolean(fullProfileData?.liked_recommendations?.find(liked => liked.id === internship.id))}
              />
            ))}
          </div>
        )}
      </div>

      {modalInternship && (
        <FeedbackModal 
          internship={modalInternship} 
          onClose={() => setModalInternship(null)} 
          onSubmit={submitFeedback} 
        />
      )}
    </div>
  );
};

export default Recommendations;
