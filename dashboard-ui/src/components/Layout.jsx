import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../auth';

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const location = useLocation();

  const initials = user?.name
    ? user.name.replace(/^Dr\.?\s*/i, '').split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
    : 'DR';

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>
            <span className="icon">🏥</span>
            CareDost
          </h1>
          <p>Clinic Management</p>
        </div>

        <nav className="sidebar-nav">
          <NavLink
            to="/"
            end
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="nav-icon">📊</span>
            Dashboard
          </NavLink>

          <NavLink
            to="/patients"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="nav-icon">👥</span>
            Patients
          </NavLink>

          {location.pathname.startsWith('/appointment') && (
            <div className="nav-item active">
              <span className="nav-icon">📋</span>
              Visit Notes
            </div>
          )}
        </nav>

        <div className="sidebar-footer">
          <div className="doctor-chip">
            <div className="doctor-avatar">{initials}</div>
            <div className="info">
              <div className="name">{user?.name || 'Doctor'}</div>
              <div className="role">Physician</div>
            </div>
          </div>
          <button
            className="nav-item"
            onClick={logout}
            style={{ marginTop: 8, color: 'var(--red)' }}
          >
            <span className="nav-icon">🚪</span>
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="main-content">
        {children}
      </main>
    </div>
  );
}
