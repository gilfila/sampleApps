import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../services/auth';
import api from '../../services/api';
import Navbar from '../Navbar/Navbar';
import './WorkerProfile.css';

// Logan McNeil's Workday WID (from get_worker_profile tool)
const LOGAN_WORKER_ID = '3aa5550b7fe348b98d7b5741afc65534';

function getNested(obj, path, defaultVal = '—') {
  if (!obj) return defaultVal;
  const val = path.split('.').reduce((o, k) => (o && o[k] != null ? o[k] : null), obj);
  if (val == null || val === '') return defaultVal;
  if (Array.isArray(val)) return val[0] ?? defaultVal;
  return typeof val === 'object' ? JSON.stringify(val) : String(val);
}

/**
 * Extract display fields from either SOAP (Response_Data.Worker) or REST API response shape.
 */
function normalizeWorkerProfile(profile) {
  if (!profile || typeof profile !== 'object') return null;

  // SOAP shape: Response_Data.Worker (array or single), Worker_Data, Personal_Data, etc.
  const soapWorker = Array.isArray(profile.Response_Data?.Worker)
    ? profile.Response_Data.Worker[0]
    : profile.Response_Data?.Worker;
  const soapData = soapWorker?.Worker_Data || {};
  const soapPersonal = soapData.Personal_Data || {};
  const soapLegal = soapPersonal.Name_Data?.Legal_Name_Data?.Name_Detail_Data || {};
  const soapPreferred = soapPersonal.Name_Data?.Preferred_Name_Data?.Name_Detail_Data || {};
  const soapEmployment = soapData.Employment_Data || {};
  const soapPrimaryJob = Array.isArray(soapEmployment.Primary_Job)
    ? soapEmployment.Primary_Job[0]
    : soapEmployment.Primary_Job;

  if (soapWorker) {
    return {
      descriptor: soapWorker.Worker_Descriptor ?? getNested(soapData, 'Worker_ID'),
      workerId: soapData.Worker_ID ?? soapWorker.Worker_Reference?.ID,
      userId: soapData.User_ID,
      legalFirst: soapLegal.First_Name,
      legalLast: soapLegal.Last_Name,
      preferredFirst: soapPreferred.First_Name,
      preferredLast: soapPreferred.Last_Name,
      birthDate: soapPersonal.Personal_Information_Data?.Birth_Date,
      primaryJob: soapPrimaryJob,
      referenceIds: soapWorker.Worker_Reference?.ID,
      source: 'soap',
    };
  }

  // REST shape: data, worker, workers[0], or top-level with descriptor, id, legalName, etc.
  const restRaw = profile.data ?? profile.worker ?? (Array.isArray(profile.workers) ? profile.workers[0] : null) ?? profile;
  const r = typeof restRaw === 'object' ? restRaw : {};
  const legalName = r.legalName ?? r.legal_name ?? r.name ?? {};
  const preferredName = r.preferredName ?? r.preferred_name ?? {};
  const id = r.id ?? r.workerID ?? r.worker_id ?? r.WID ?? LOGAN_WORKER_ID;
  const descriptor = r.descriptor ?? r.displayName ?? r.display_name
    ?? (typeof legalName === 'object' ? [legalName.first, legalName.given, legalName.firstName, legalName.last, legalName.family, legalName.lastName].filter(Boolean).join(' ') : legalName)
    ?? id;

  if (descriptor || id) {
    return {
      descriptor: typeof descriptor === 'string' ? descriptor : (descriptor?.descriptor ?? String(id)),
      workerId: id,
      userId: r.userID ?? r.user_id ?? r.userId,
      legalFirst: legalName.first ?? legalName.given ?? legalName.firstName,
      legalLast: legalName.last ?? legalName.family ?? legalName.lastName,
      preferredFirst: preferredName.first ?? preferredName.given,
      preferredLast: preferredName.last ?? preferredName.family,
      birthDate: r.birthDate ?? r.birth_date,
      businessTitle: r.businessTitle ?? r.business_title ?? r.jobTitle ?? r.job_title,
      primaryWorkEmail: r.primaryWorkEmail ?? r.primary_work_email ?? r.email,
      primaryJob: r.primaryJob ?? r.primary_job ?? r.supervisoryOrganization ?? r.primary_supervisory_organization,
      referenceIds: r.referenceIds ?? id,
      source: 'rest',
    };
  }

  return null;
}

function WorkerProfile() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        setError(null);
        const response = await api.get(`/workers/profile/${LOGAN_WORKER_ID}`);
        setProfile(response.data);
      } catch (err) {
        setError(err.response?.data?.error || err.message || 'Failed to load worker profile');
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (loading) {
    return (
      <div>
        <Navbar user={user} onLogout={handleLogout} />
        <div className="container worker-profile-container">
          <p>Loading Logan&apos;s profile from Workday...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <Navbar user={user} onLogout={handleLogout} />
        <div className="container worker-profile-container">
          <h1>Worker Profile</h1>
          <div className="worker-profile-error">{error}</div>
        </div>
      </div>
    );
  }

  const display = normalizeWorkerProfile(profile);
  const showRaw = profile && !display;

  return (
    <div>
      <Navbar user={user} onLogout={handleLogout} />
      <div className="container worker-profile-container">
        <h1>Worker Profile</h1>
        <p className="worker-profile-subtitle">
          From Workday ({display?.source === 'rest' ? 'REST API' : 'Get_Workers SOAP'})
        </p>

        {display ? (
          <>
            <section className="worker-profile-card worker-profile-header">
              <h2>{display.descriptor || 'Logan McNeil'}</h2>
              <div className="worker-profile-meta">
                <span><strong>Worker ID</strong> {display.workerId ?? '—'}</span>
                {display.userId != null && display.userId !== '' && (
                  <span><strong>User ID</strong> {display.userId}</span>
                )}
              </div>
            </section>

            <section className="worker-profile-card">
              <h3>Legal Name</h3>
              <p>{(display.legalFirst || display.legalLast) ? `${display.legalFirst ?? ''} ${display.legalLast ?? ''}`.trim() : '—'}</p>
            </section>

            <section className="worker-profile-card">
              <h3>Preferred Name</h3>
              <p>{(display.preferredFirst || display.preferredLast) ? `${display.preferredFirst ?? ''} ${display.preferredLast ?? ''}`.trim() : '—'}</p>
            </section>

            {(display.birthDate || display.primaryWorkEmail || display.businessTitle) && (
              <section className="worker-profile-card">
                <h3>Personal / Job</h3>
                {display.birthDate && <p><strong>Birth date</strong> {display.birthDate}</p>}
                {display.primaryWorkEmail && <p><strong>Primary work email</strong> {display.primaryWorkEmail}</p>}
                {display.businessTitle && <p><strong>Business title</strong> {display.businessTitle}</p>}
              </section>
            )}

            {display.primaryJob && typeof display.primaryJob === 'object' && (
              <section className="worker-profile-card">
                <h3>Primary Job</h3>
                <p><strong>Position</strong> {getNested(display.primaryJob, 'Position_Reference.ID')}</p>
                <p><strong>Job Title</strong> {getNested(display.primaryJob, 'Job_Profile_Reference.ID')}</p>
              </section>
            )}

            {display.primaryJob && typeof display.primaryJob === 'string' && (
              <section className="worker-profile-card">
                <h3>Primary Job</h3>
                <p>{display.primaryJob}</p>
              </section>
            )}

            <section className="worker-profile-card">
              <h3>Reference IDs</h3>
              <pre className="worker-profile-ids">
                {JSON.stringify(Array.isArray(display.referenceIds) ? display.referenceIds : (display.referenceIds ? [display.referenceIds] : []), null, 2)}
              </pre>
            </section>
          </>
        ) : showRaw ? (
          <section className="worker-profile-card">
            <h3>Raw response</h3>
            <p>Data received but format not recognized. Displaying raw JSON:</p>
            <pre className="worker-profile-ids">{JSON.stringify(profile, null, 2)}</pre>
          </section>
        ) : (
          <section className="worker-profile-card">
            <p>No worker data to display.</p>
          </section>
        )}
      </div>
    </div>
  );
}

export default WorkerProfile;
