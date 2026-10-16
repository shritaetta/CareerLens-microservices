import React, { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import InternshipCard from '../components/InternshipCard';
import { ArrowLeft, Heart, Loader } from 'lucide-react';
import { Link } from 'react-router-dom';
import { apiFetch } from '../api';

const LikedRecommendations = () => {
  const [likedInternships, setLikedInternships] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [fullProfileData, setFullProfileData] = useState(null);

  const fetchLiked = async () => {
    try {
      const userId = localStorage.getItem('user_id');
      if (!userId) throw new Error("User not logged in");

      const res = await apiFetch(`/api/profile/${userId}`);
      if (!res.ok) throw new Error('Failed to fetch profile');
      const data = await res.json();
      
      const raw = data.profile_data || {};
      setFullProfileData(raw);
      setLikedInternships(raw.liked_recommendations || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLiked();
  }, []);

  const handleLike = async (internship, isLiked) => {
    if (!fullProfileData) return;
    
    // We mainly handle 'unliking' here
    const currentLiked = fullProfileData.liked_recommendations || [];
    let newLiked = [];
    if (isLiked) {
      if (!currentLiked.find(i => i.id === internship.id)) newLiked = [...currentLiked, internship];
      else newLiked = currentLiked;
    } else {
      newLiked = currentLiked.filter(i => i.id !== internship.id);
    }
    
    const newFullProfile = { ...fullProfileData, liked_recommendations: newLiked };
    
    // Optimistic UI update
    setFullProfileData(newFullProfile);
    setLikedInternships(newLiked);

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

  return (
    <div className="dashboard-layout animate-fade-in" style={{ minHeight: '100vh', background: 'var(--bg-color)' }}>
      <Navbar />
      <div className="dashboard-container" style={{ padding: '2rem', margin: '0 auto' }}>
        
        <div style={{ marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <Link to="/dashboard" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', textDecoration: 'none', fontWeight: 500 }}>
            <ArrowLeft size={18} /> Back
          </Link>
          <h1 style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0, display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Heart size={28} style={{ color: '#ec4899' }} /> Liked Recommendations
          </h1>
        </div>

        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
             <Loader className="animate-spin" size={48} color="#ec4899" />
          </div>
        ) : error ? (
           <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', color: '#fca5a5', padding: '1.5rem', borderRadius: '12px' }}>
              <p>Error: {error}</p>
           </div>
        ) : likedInternships.length === 0 ? (
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
            <div style={{ width: '80px', height: '80px', borderRadius: '50%', background: 'rgba(236, 72, 153, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1rem' }}>
              <Heart size={40} style={{ color: '#ec4899' }} />
            </div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>No Liked Recommendations Yet</h2>
            <p style={{ color: 'var(--text-secondary)', maxWidth: '400px', lineHeight: 1.6 }}>
              When you find a recommendation that matches your career goals, click the heart icon. They will be stored here for easy access.
            </p>
            <Link to="/recommendations" style={{ marginTop: '1.5rem', background: 'linear-gradient(to right, #8b5cf6, #ec4899)', border: 'none', padding: '0.75rem 1.5rem', borderRadius: '8px', color: 'white', fontWeight: 600, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
              Browse Recommendations
            </Link>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.5rem' }}>
            {likedInternships.map((internship, i) => (
              <InternshipCard 
                 key={internship.id || i} 
                 internship={internship} 
                 onLike={handleLike}
                 isLikedInitial={true}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default LikedRecommendations;
