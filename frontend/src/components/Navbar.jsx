import React, { useState, useRef, useEffect } from 'react';
import { User, LogOut, Edit3, Heart, FileText } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import './Navbar.css';

const Navbar = () => {
  const navigate = useNavigate();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('user_id');
    localStorage.removeItem('access_token');
    navigate('/login');
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/dashboard" className="brand-logo">
          CareerLens
        </Link>
        
        <div className="navbar-actions">
          <div className="profile-dropdown-container" ref={dropdownRef}>
            <button 
              className={`nav-icon-link ${dropdownOpen ? 'active' : ''}`}
              title="Profile Menu"
              onClick={() => setDropdownOpen(!dropdownOpen)}
              style={{ border: 'none', background: 'transparent', cursor: 'pointer' }}
            >
              <User size={22} className="nav-icon" />
            </button>

            {dropdownOpen && (
              <div className="profile-dropdown-menu animate-fade-in">
                <Link to="/profile-setup" className="dropdown-item" onClick={() => setDropdownOpen(false)}>
                  <Edit3 size={16} />
                  <span>Edit Profile</span>
                </Link>
                <Link to="/liked-recommendations" className="dropdown-item" onClick={() => setDropdownOpen(false)}>
                  <Heart size={16} />
                  <span>Liked Recommendations</span>
                </Link>
                <Link to="/resume-drafts" className="dropdown-item" onClick={() => setDropdownOpen(false)}>
                  <FileText size={16} />
                  <span>Resume Drafts</span>
                </Link>
                <div className="dropdown-divider"></div>
                <button onClick={handleLogout} className="dropdown-item logout-item">
                  <LogOut size={16} />
                  <span>Logout</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
