import { useState, useEffect } from 'react';
import { api } from '../api';

export default function Patients() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    api.patients()
      .then(res => setPatients(res.patients || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const filtered = patients.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.phone?.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) return <div className="loading-container"><div className="spinner" /></div>;

  return (
    <>
      <div className="page-header">
        <h2>Patients</h2>
        <p>All registered patients from Telegram bot</p>
      </div>

      <div style={{ marginBottom: 20 }}>
        <input
          id="patient-search"
          type="text"
          className="form-input"
          placeholder="Search by name or phone..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ maxWidth: 360 }}
        />
      </div>

      <div className="section">
        <div className="section-header">
          <h3>👥 Patient Records</h3>
          <span className="count">{filtered.length}</span>
        </div>

        {filtered.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-strong)' }}>
                  {['Name', 'Phone', 'Appointments', 'Last Visit'].map(h => (
                    <th
                      key={h}
                      style={{
                        textAlign: 'left',
                        padding: '12px 20px',
                        fontSize: 11,
                        fontWeight: 600,
                        color: 'var(--text-muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map(p => (
                  <tr
                    key={p.id}
                    style={{
                      borderBottom: '1px solid var(--border)',
                      transition: 'var(--transition)',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-card-hover)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={{ padding: '14px 20px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <div className="apt-avatar">
                          {p.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)}
                        </div>
                        <span style={{ fontWeight: 600, fontSize: 14 }}>{p.name}</span>
                      </div>
                    </td>
                    <td style={{ padding: '14px 20px', color: 'var(--text-secondary)', fontSize: 14 }}>
                      {p.phone || '—'}
                    </td>
                    <td style={{ padding: '14px 20px' }}>
                      <span className="badge badge-scheduled">{p.total_appointments}</span>
                    </td>
                    <td style={{ padding: '14px 20px', color: 'var(--text-muted)', fontSize: 13 }}>
                      {p.last_visit}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-icon">👥</div>
            <div>No patients found</div>
          </div>
        )}
      </div>
    </>
  );
}
