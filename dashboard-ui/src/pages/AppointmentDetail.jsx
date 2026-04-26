import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api';

export default function AppointmentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const chatRef = useRef(null);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState(null);

  // Form state
  const [notes, setNotes] = useState('');
  const [medicines, setMedicines] = useState('');
  const [followUp, setFollowUp] = useState('');
  const [directMsg, setDirectMsg] = useState('');
  const [sendingMsg, setSendingMsg] = useState(false);
  const [expandingNotes, setExpandingNotes] = useState(false);
  const [expandingMeds, setExpandingMeds] = useState(false);

  useEffect(() => {
    api.appointment(id)
      .then(res => {
        setData(res);
        if (res.summary) {
          setNotes(res.summary.notes || '');
          setMedicines(res.summary.medicines || '');
          setFollowUp(res.summary.follow_up_date || '');
        }
      })
      .catch(() => navigate('/'))
      .finally(() => setLoading(false));
  }, [id, navigate]);

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [data?.messages]);

  const showToast = (msg, isError = false) => {
    setToast({ msg, isError });
    setTimeout(() => setToast(null), 3000);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await api.saveNotes(id, { notes, medicines, follow_up: followUp });
      showToast(
        res.revisit_scheduled
          ? 'Saved and revisit auto-scheduled.'
          : 'Visit completed and patient notified.'
      );
      // Refresh
      const fresh = await api.appointment(id);
      setData(fresh);
    } catch (err) {
      showToast(err.message, true);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = async () => {
    if (!confirm('Cancel this appointment? The patient will be notified.')) return;
    try {
      await api.cancelAppointment(id);
      showToast('Appointment cancelled.');
      const fresh = await api.appointment(id);
      setData(fresh);
    } catch (err) {
      showToast(err.message, true);
    }
  };

  const handleSendMsg = async (e) => {
    e.preventDefault();
    if (!directMsg.trim()) return;
    setSendingMsg(true);
    try {
      await api.sendMessage(id, directMsg);
      showToast('Message sent to patient.');
      setDirectMsg('');
    } catch (err) {
      showToast(err.message, true);
    } finally {
      setSendingMsg(false);
    }
  };

  const handleExpand = async (field) => {
    const text = field === 'notes' ? notes : medicines;
    if (!text.trim()) return;
    field === 'notes' ? setExpandingNotes(true) : setExpandingMeds(true);
    try {
      const res = await api.expandNotes(text);
      if (res.expanded) {
        field === 'notes' ? setNotes(res.expanded) : setMedicines(res.expanded);
      }
    } catch {
      showToast('AI expansion failed', true);
    } finally {
      field === 'notes' ? setExpandingNotes(false) : setExpandingMeds(false);
    }
  };

  const getSeverityClass = (severity) => {
    if (!severity) return '';
    const s = severity.toLowerCase();
    if (s.includes('mild')) return 'severity-mild';
    if (s.includes('moderate')) return 'severity-moderate';
    if (s.includes('severe')) return 'severity-severe';
    return '';
  };

  if (loading) return <div className="loading-container"><div className="spinner" /></div>;
  if (!data) return <div className="empty-state">Appointment not found</div>;

  const { appointment, patient, pre_visit, messages } = data;

  return (
    <>
      <button className="back-link" onClick={() => navigate('/')}>
        Back to Dashboard
      </button>

      <div className="page-header">
        <h2>Visit Notes - {patient.name}</h2>
        <p>Appointment #{appointment.id} - {appointment.time}</p>
      </div>

      <div className="two-col">
        {/* Left column */}
        <div>
          {/* Patient Info */}
          <div className="detail-card">
            <h3>Patient Information</h3>
            <div className="info-grid">
              <div className="info-item">
                <div className="info-label">Name</div>
                <div className="info-value">{patient.name}</div>
              </div>
              <div className="info-item">
                <div className="info-label">Phone</div>
                <div className="info-value">{patient.phone}</div>
              </div>
              <div className="info-item">
                <div className="info-label">Appointment</div>
                <div className="info-value">{appointment.time}</div>
              </div>
              <div className="info-item">
                <div className="info-label">Status</div>
                <div className="info-value">
                  <span className={`badge badge-${appointment.status}`}>
                    {appointment.status}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Pre-Visit Info */}
          <div className="detail-card previsit-card">
            <h3>Pre-Visit Questionnaire</h3>
            {pre_visit ? (
              <div className="previsit-grid">
                <div className="previsit-item">
                  <div className="pv-label">Main Problem</div>
                  <div className="pv-value">{pre_visit.main_problem || '—'}</div>
                </div>
                <div className="previsit-item">
                  <div className="pv-label">Duration</div>
                  <div className="pv-value">{pre_visit.duration || '—'}</div>
                </div>
                <div className="previsit-item">
                  <div className="pv-label">Severity</div>
                  <div className={`pv-value ${getSeverityClass(pre_visit.severity)}`}>
                    {pre_visit.severity || '—'}
                  </div>
                </div>
                <div className="previsit-item">
                  <div className="pv-label">Taking Medicine</div>
                  <div className="pv-value">{pre_visit.taking_medicine || '—'}</div>
                </div>
                {pre_visit.extra_notes && (
                  <div className="previsit-item" style={{ gridColumn: '1 / -1' }}>
                    <div className="pv-label">Additional Notes</div>
                    <div className="pv-value">{pre_visit.extra_notes}</div>
                  </div>
                )}
              </div>
            ) : (
              <div className="empty-state" style={{ padding: '20px 0' }}>
                <div className="empty-icon">--</div>
                <div>Patient hasn't filled the questionnaire yet</div>
              </div>
            )}
          </div>

          {/* Visit Notes Form */}
          <div className="detail-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ marginBottom: 0 }}>Clinical Notes</h3>
              <button
                className="btn btn-ai"
                onClick={() => handleExpand('notes')}
                disabled={expandingNotes || !notes.trim()}
              >
                {expandingNotes ? 'Expanding...' : 'AI Expand'}
              </button>
            </div>

            <form onSubmit={handleSave}>
              <div className="form-group">
                <label className="form-label">Diagnosis / Notes</label>
                <textarea
                  id="notes-field"
                  className="form-textarea"
                  rows={4}
                  placeholder="Patient complaints, diagnosis, observations..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <label className="form-label" style={{ margin: 0 }}>Medicines Prescribed</label>
                <button
                  type="button"
                  className="btn btn-ai"
                  onClick={() => handleExpand('medicines')}
                  disabled={expandingMeds || !medicines.trim()}
                >
                  {expandingMeds ? 'Expanding...' : 'AI Expand'}
                </button>
              </div>
              <div className="form-group">
                <textarea
                  id="medicines-field"
                  className="form-textarea"
                  rows={3}
                  placeholder="e.g. Paracetamol 500mg — twice daily for 5 days"
                  value={medicines}
                  onChange={(e) => setMedicines(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Follow-up Date</label>
                <input
                  id="followup-field"
                  type="date"
                  className="form-input"
                  value={followUp}
                  onChange={(e) => setFollowUp(e.target.value)}
                />
              </div>

              <div className="action-row">
                <button type="button" className="btn btn-ghost" onClick={() => navigate('/')}>
                  Go Back
                </button>
                {appointment.status === 'scheduled' && (
                  <button
                    id="save-notes-btn"
                    type="submit"
                    className="btn btn-success"
                    disabled={saving}
                  >
                    {saving ? 'Saving...' : 'Save and Mark Complete'}
                  </button>
                )}
                <a
                  href={`/appointment/${id}/prescription`}
                  className="btn btn-ghost"
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => {
                    e.preventDefault();
                    window.open(`/appointment/${id}/prescription`, '_blank');
                  }}
                >
                  Prescription PDF
                </a>
              </div>

              {appointment.status === 'scheduled' && (
                <button
                  id="cancel-apt-btn"
                  type="button"
                  className="btn btn-danger btn-block"
                  style={{ marginTop: 12 }}
                  onClick={handleCancel}
                >
                  Cancel Booking and Remove from Calendar
                </button>
              )}
            </form>
          </div>
        </div>

        {/* Right column — Chat */}
        <div>
          <div className="detail-card" style={{ borderTop: '3px solid var(--green)' }}>
            <h3>Conversation History</h3>

            <div className="chat-container" ref={chatRef}>
              {messages.length > 0 ? (
                messages.map(msg => (
                  <div
                    key={msg.id}
                    className={`msg-bubble ${msg.direction === 'to_patient' ? 'msg-to-patient' : 'msg-from-patient'}`}
                  >
                    <div className="msg-time">{msg.time}</div>
                    {msg.message && <div style={{ whiteSpace: 'pre-wrap' }}>{msg.message}</div>}
                    {msg.file_path && msg.is_image && (
                      <a href={msg.file_path} target="_blank" rel="noopener noreferrer">
                        <img src={msg.file_path} alt="Attachment" />
                      </a>
                    )}
                    {msg.file_path && !msg.is_image && (
                      <a
                        href={msg.file_path}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          display: 'inline-block',
                          marginTop: 6,
                          color: 'var(--accent-light)',
                          fontSize: 13,
                          textDecoration: 'none',
                          background: 'var(--bg-card)',
                          padding: '4px 10px',
                          borderRadius: 6,
                          border: '1px solid var(--border)'
                        }}
                      >
                        View Document
                      </a>
                    )}
                  </div>
                ))
              ) : (
                <div className="empty-state" style={{ padding: '20px 0' }}>
                  <div style={{ fontSize: 24, opacity: 0.3, marginBottom: 8 }}>--</div>
                  <div>No message history yet</div>
                </div>
              )}
            </div>

            <form onSubmit={handleSendMsg}>
              <div className="form-group" style={{ marginBottom: 8 }}>
                <label className="form-label">Send Message to Patient's Telegram</label>
                <textarea
                  id="direct-message"
                  className="form-textarea"
                  rows={3}
                  placeholder="Type a direct message..."
                  value={directMsg}
                  onChange={(e) => setDirectMsg(e.target.value)}
                  required
                />
              </div>
              <button
                id="send-msg-btn"
                type="submit"
                className="btn btn-success btn-block"
                disabled={sendingMsg || !directMsg.trim()}
              >
                {sendingMsg ? 'Sending...' : 'Send Message'}
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
