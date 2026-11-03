/**
 * Job Application Tracker - React Frontend
 * ========================================
 * Purpose:
 *   Single Page Application (SPA) providing an interactive dashboard to manage
 *   job applications across ephemeral PR preview environments.
 *
 * Key Features for DevOps Portfolio / Interview:
 *   1. Dynamic Preview Banner: Fetches `/api/version` to display PR number & commit SHA.
 *   2. Relative API Endpoints: Uses `/api/...` so the app functions transparently
 *      behind any Ingress controller, NGINX reverse proxy, or local port forward.
 *   3. Full CRUD & Filters: Add, update status, delete, and filter applications.
 */

import React, { useState, useEffect, useMemo } from 'react';
import './App.css';

const STATUS_OPTIONS = ['applied', 'interview', 'offer', 'rejected'];

export default function App() {
  // --- State Management ---
  const [applications, setApplications] = useState([]);
  const [versionInfo, setVersionInfo] = useState(null);
  const [selectedFilter, setSelectedFilter] = useState('all');
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);

  // New Application Form State
  const [newCompany, setNewCompany] = useState('');
  const [newRole, setNewRole] = useState('');
  const [newStatus, setNewStatus] = useState('applied');
  const [newNotes, setNewNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // --- 1. Fetch PR & Version Metadata ---
  useEffect(() => {
    // Why relative URL? In Kubernetes and Ingress, the app is accessed on dynamic
    // subdomains (e.g. pr-42.127.0.0.1.nip.io). Relative paths avoid hardcoded domains.
    fetch('/api/version')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => setVersionInfo(data))
      .catch((err) => {
        console.warn('Could not load version info (running without backend?):', err);
      });
  }, []);

  // --- 2. Fetch Job Applications ---
  const fetchApplications = async () => {
    setIsLoading(true);
    setErrorMessage('');
    try {
      const res = await fetch('/api/applications');
      if (!res.ok) throw new Error(`Failed to load applications (HTTP ${res.status})`);
      const data = await res.json();
      setApplications(data);
    } catch (err) {
      console.error(err);
      setErrorMessage(err.message || 'Error connecting to backend API.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, []);

  // --- 3. Create Application Handler ---
  const handleCreateApplication = async (e) => {
    e.preventDefault();
    if (!newCompany.trim() || !newRole.trim()) return;

    setIsSubmitting(true);
    try {
      const res = await fetch('/api/applications', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company: newCompany.trim(),
          role: newRole.trim(),
          status: newStatus,
          notes: newNotes.trim() || null,
        }),
      });

      if (!res.ok) throw new Error(`Failed to create application (HTTP ${res.status})`);

      const created = await res.json();
      setApplications((prev) => [created, ...prev]);

      // Reset form
      setNewCompany('');
      setNewRole('');
      setNewStatus('applied');
      setNewNotes('');
      setShowAddForm(false);
    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  // --- 4. Update Application Status Handler ---
  const handleStatusChange = async (id, updatedStatus) => {
    try {
      const res = await fetch(`/api/applications/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: updatedStatus }),
      });

      if (!res.ok) throw new Error(`Failed to update status (HTTP ${res.status})`);

      const updated = await res.json();
      setApplications((prev) =>
        prev.map((app) => (app.id === id ? updated : app))
      );
    } catch (err) {
      alert(`Error updating status: ${err.message}`);
    }
  };

  // --- 5. Delete Application Handler ---
  const handleDeleteApplication = async (id) => {
    if (!window.confirm('Are you sure you want to delete this application?')) return;

    try {
      const res = await fetch(`/api/applications/${id}`, { method: 'DELETE' });
      if (!res.ok && res.status !== 204) throw new Error(`HTTP ${res.status}`);

      setApplications((prev) => prev.filter((app) => app.id !== id));
    } catch (err) {
      alert(`Error deleting application: ${err.message}`);
    }
  };

  // --- Filtered Applications & Summary Stats ---
  const filteredApplications = useMemo(() => {
    if (selectedFilter === 'all') return applications;
    return applications.filter((app) => app.status === selectedFilter);
  }, [applications, selectedFilter]);

  const stats = useMemo(() => {
    return {
      total: applications.length,
      applied: applications.filter((a) => a.status === 'applied').length,
      interview: applications.filter((a) => a.status === 'interview').length,
      offer: applications.filter((a) => a.status === 'offer').length,
      rejected: applications.filter((a) => a.status === 'rejected').length,
    };
  }, [applications]);

  // Format date helper
  const formatDate = (isoString) => {
    if (!isoString) return '';
    const d = new Date(isoString);
    return d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div className="app-container">
      {/* 1. Dynamic Ephemeral Preview Banner (Hidden if PR_NUMBER is empty) */}
      {versionInfo && versionInfo.pr_number && versionInfo.pr_number !== '' && (
        <header className="preview-banner">
          <div className="preview-banner-content">
            <span>🚀 Preview for</span>
            <span className="preview-badge">PR #{versionInfo.pr_number}</span>
            <span>·</span>
            <span className="git-badge">commit {versionInfo.git_sha ? versionInfo.git_sha.substring(0, 7) : 'head'}</span>
            <span>·</span>
            <span>v{versionInfo.app_version}</span>
          </div>
          <span style={{ fontSize: '0.8rem', opacity: 0.9 }}>🟢 Ephemeral Environment</span>
        </header>
      )}

      {/* 2. Main Container */}
      <main className="main-content">
        <section className="header-section">
          <div className="header-title">
            <h1>💼 Job Application Tracker</h1>
            <p>Track job opportunities, interview stages, and offers in this preview environment.</p>
          </div>
          <button
            className="btn btn-primary"
            onClick={() => setShowAddForm((prev) => !prev)}
          >
            {showAddForm ? '✕ Close Form' : '+ Add Application'}
          </button>
        </section>

        {/* 3. Error Alert */}
        {errorMessage && (
          <div className="alert-error">
            <span>⚠️ {errorMessage}</span>
            <button className="btn btn-secondary btn-sm" onClick={fetchApplications}>
              Retry
            </button>
          </div>
        )}

        {/* 4. Statistics Row */}
        <section className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">Total Applications</div>
            <div className="stat-value">{stats.total}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Applied</div>
            <div className="stat-value" style={{ color: 'var(--status-applied-text)' }}>{stats.applied}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Interviewing</div>
            <div className="stat-value" style={{ color: 'var(--status-interview-text)' }}>{stats.interview}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Offers</div>
            <div className="stat-value" style={{ color: 'var(--status-offer-text)' }}>{stats.offer}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Rejected</div>
            <div className="stat-value" style={{ color: 'var(--status-rejected-text)' }}>{stats.rejected}</div>
          </div>
        </section>

        {/* 5. Add Application Form Card */}
        {showAddForm && (
          <form className="form-card" onSubmit={handleCreateApplication}>
            <h2 className="form-title">New Job Application</h2>
            <div className="form-grid">
              <div className="form-group">
                <label>Company *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Google, GitHub, Stripe"
                  className="form-control"
                  value={newCompany}
                  onChange={(e) => setNewCompany(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Role / Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Cloud Platform Engineer"
                  className="form-control"
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Status</label>
                <select
                  className="form-control"
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value)}
                >
                  <option value="applied">Applied</option>
                  <option value="interview">Interview</option>
                  <option value="offer">Offer</option>
                  <option value="rejected">Rejected</option>
                </select>
              </div>
            </div>
            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label>Notes (Optional)</label>
              <input
                type="text"
                placeholder="e.g. Recruiter chat on Monday, referral from Alex"
                className="form-control"
                value={newNotes}
                onChange={(e) => setNewNotes(e.target.value)}
              />
            </div>
            <div className="form-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowAddForm(false)}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="btn btn-primary"
              >
                {isSubmitting ? 'Saving...' : 'Create Application'}
              </button>
            </div>
          </form>
        )}

        {/* 6. Filter Controls */}
        <div className="controls-bar">
          <div className="filter-group">
            {['all', 'applied', 'interview', 'offer', 'rejected'].map((status) => (
              <button
                key={status}
                className={`filter-btn ${selectedFilter === status ? 'active' : ''}`}
                onClick={() => setSelectedFilter(status)}
              >
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </button>
            ))}
          </div>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Showing {filteredApplications.length} of {applications.length}
          </span>
        </div>

        {/* 7. Applications Table & States */}
        <section className="table-container">
          {isLoading ? (
            <div className="state-box">
              <p>⏳ Loading applications from backend database...</p>
            </div>
          ) : filteredApplications.length === 0 ? (
            <div className="state-box">
              <h3>No applications found</h3>
              <p>
                {selectedFilter === 'all'
                  ? "Click '+ Add Application' to record your first job application."
                  : `No applications with status '${selectedFilter}'.`}
              </p>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Notes</th>
                  <th>Created</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredApplications.map((app) => (
                  <tr key={app.id}>
                    <td className="company-cell">{app.company}</td>
                    <td className="role-cell">{app.role}</td>
                    <td>
                      <span className={`status-badge status-${app.status}`}>
                        {app.status}
                      </span>
                    </td>
                    <td className="notes-cell" title={app.notes || ''}>
                      {app.notes || '—'}
                    </td>
                    <td className="date-cell">{formatDate(app.created_at)}</td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '0.5rem', alignItems: 'center' }}>
                        <select
                          className="status-select"
                          value={app.status}
                          onChange={(e) => handleStatusChange(app.id, e.target.value)}
                        >
                          {STATUS_OPTIONS.map((opt) => (
                            <option key={opt} value={opt}>
                              {opt.charAt(0).toUpperCase() + opt.slice(1)}
                            </option>
                          ))}
                        </select>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => handleDeleteApplication(app.id)}
                          title="Delete application"
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </main>

      {/* 8. Footer */}
      <footer className="app-footer">
        <p>🚀 Powered by GitOps (Argo CD) & GitHub Actions · preview-env-platform</p>
      </footer>
    </div>
  );
}
