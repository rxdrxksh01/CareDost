import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  // Broadcast state
  const [bcastDate, setBcastDate] = useState('');
  const [bcastMsg, setBcastMsg] = useState('');
  const [bcastCancel, setBcastCancel] = useState(false);
  const [bcastLoading, setBcastLoading] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    api.dashboard().then(setData).catch(console.error).finally(() => setLoading(false));
  }, []);

  const showToast = (msg, isError = false) => {
    setToast({ msg, isError });
    setTimeout(() => setToast(null), 3000);
  };

  const handleBroadcast = async (e) => {
    e.preventDefault();
    if (!bcastMsg.trim() || !bcastDate) return;
    setBcastLoading(true);
    try {
      const res = await api.broadcast({
        message: bcastMsg,
        target_date: bcastDate,
        is_cancellation: bcastCancel,
      });
      showToast(`✅ Broadcast sent to ${res.affected} patients`);
      setBcastMsg('');
      setBcastDate('');
      setBcastCancel(false);
      // Refresh dashboard data
      api.dashboard().then(setData);
    } catch (err) {
      showToast(err.message, true);
    } finally {
      setBcastLoading(false);
    }
  };

  if (loading) return <div className="loading-container"><div className="spinner" /></div>;
  if (!data) return <div className="empty-state">Failed to load dashboard</div>;

  const { stats, today, upcoming, recent_completed } = data;

  return (
    <>
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Welcome back, {data.doctor_name}. Here's your clinic overview.</p>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card cyan">
          <div className="stat-icon">📅</div>
          <div className="stat-value">{stats.today_count}</div>
          <div className="stat-label">Today's Appointments</div>
        </div>
        <div className="stat-card accent">
          <div className="stat-icon">👥</div>
          <div className="stat-value">{stats.total_patients}</div>
          <div className="stat-label">Total Patients</div>
        </div>
        <div className="stat-card blue">
          <div className="stat-icon">🗓</div>
          <div className="stat-value">{stats.total_appointments}</div>
          <div className="stat-label">Total Appointments</div>
        </div>
        <div className="stat-card green">
          <div className="stat-icon">✅</div>
          <div className="stat-value">{stats.completed}</div>
          <div className="stat-label">Completed Visits</div>
        </div>
        <div className="stat-card pink">
          <div className="stat-icon">💊</div>
          <div className="stat-value">{stats.active_reminders}</div>
          <div className="stat-label">Active Reminders</div>
        </div>
        <div className="stat-card amber">
          <div className="stat-icon">❌</div>
          <div className="stat-value">{stats.cancelled}</div>
          <div className="stat-label">Cancelled</div>
        </div>
      </div>

      <div className="two-col">
        {/* Left column */}
        <div>
          {/* Today's Appointments */}
          <div className="section">
            <div className="section-header">
              <h3>📅 Today's Appointments</h3>
              {today.length > 0 && <span className="count">{today.length}</span>}
            </div>
            {today.length > 0 ? (
              today.map(apt => (
                <div
                  key={apt.id}
                  className="apt-row"
                  onClick={() => navigate(`/appointment/${apt.id}`)}
                >
                  <div className="apt-left">
                    <div className="apt-avatar">
                      {apt.patient_name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)}
                    </div>
                    <div className="apt-info">
                      <div className="apt-name">{apt.patient_name}</div>
                      <div className="apt-time">{apt.time} · {apt.patient_phone}</div>
                    </div>
                  </div>
                  <div className="apt-right">
                    <span className="badge badge-scheduled">Scheduled</span>
                    <button
                      className="btn btn-primary"
                      onClick={(e) => { e.stopPropagation(); navigate(`/appointment/${apt.id}`); }}
                    >
                      📝 Notes
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <div className="empty-icon">📭</div>
                <div>No appointments scheduled for today</div>
              </div>
            )}
          </div>

          {/* Recent completed */}
          {recent_completed.length > 0 && (
            <div className="section">
              <div className="section-header">
                <h3>✅ Recently Completed</h3>
              </div>
              {recent_completed.map(apt => (
                <div
                  key={apt.id}
                  className="apt-row"
                  onClick={() => navigate(`/appointment/${apt.id}`)}
                >
                  <div className="apt-left">
                    <div className="apt-avatar" style={{ background: 'linear-gradient(135deg, var(--green), #16a34a)' }}>
                      {apt.patient_name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)}
                    </div>
                    <div className="apt-info">
                      <div className="apt-name">{apt.patient_name}</div>
                      <div className="apt-time">{apt.time}</div>
                    </div>
                  </div>
                  <span className="badge badge-completed">Completed</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right column */}
        <div>
          {/* Upcoming */}
          <div className="section">
            <div className="section-header">
              <h3>🗓 Upcoming</h3>
              {upcoming.length > 0 && <span className="count">{upcoming.length}</span>}
            </div>
            {upcoming.length > 0 ? (
              upcoming.map(apt => (
                <div
                  key={apt.id}
                  className="apt-row"
                  onClick={() => navigate(`/appointment/${apt.id}`)}
                >
                  <div className="apt-left">
                    <div className="apt-avatar" style={{ background: 'linear-gradient(135deg, var(--amber), #d97706)' }}>
                      {apt.patient_name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)}
                    </div>
                    <div className="apt-info">
                      <div className="apt-name">{apt.patient_name}</div>
                      <div className="apt-time">{apt.time}</div>
                    </div>
                  </div>
                  <span className="badge badge-upcoming">Upcoming</span>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <div className="empty-icon">🗓</div>
                <div>No upcoming appointments</div>
              </div>
            )}
          </div>

          {/* Broadcast */}
          <div className="section broadcast-section" style={{ borderRadius: 'var(--radius)' }}>
            <div className="broadcast-header">📢 Broadcast Announcement</div>
            <form onSubmit={handleBroadcast} style={{ padding: 20 }}>
              <div className="form-group">
                <label className="form-label">Target Date</label>
                <input
                  id="broadcast-date"
                  type="date"
                  className="form-input"
                  value={bcastDate}
                  onChange={(e) => setBcastDate(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Message</label>
                <textarea
                  id="broadcast-message"
                  className="form-textarea"
                  rows={3}
                  placeholder="Type your announcement..."
                  value={bcastMsg}
                  onChange={(e) => setBcastMsg(e.target.value)}
                  required
                />
              </div>
              <div className="checkbox-wrapper">
                <input
                  type="checkbox"
                  id="broadcast-cancel"
                  checked={bcastCancel}
                  onChange={(e) => setBcastCancel(e.target.checked)}
                />
                <label htmlFor="broadcast-cancel">
                  🚨 Mass Cancellation — Cancel all slots & remove from calendar
                </label>
              </div>
              <button
                id="broadcast-submit"
                type="submit"
                className="btn btn-primary btn-block"
                disabled={bcastLoading}
                style={{ marginTop: 8 }}
              >
                {bcastLoading ? 'Sending...' : '📢 Send Broadcast'}
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div className={`toast ${toast.isError ? 'error' : ''}`}>
          {toast.msg}
        </div>
      )}
    </>
  );
}
