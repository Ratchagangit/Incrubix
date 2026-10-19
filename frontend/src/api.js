import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1'
});

function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export async function checkHealth() {
  const resp = await axios.get('/health');
  return resp.data;
}

export async function uploadVideo(file) {
  const formData = new FormData();
  formData.append('file', file);
  const resp = await api.post('/videos/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
      'Idempotency-Key': generateUUID()
    }
  });
  return resp.data;
}

export async function ingestUrl(url) {
  const resp = await api.post('/videos/url', { url }, {
    headers: {
      'Idempotency-Key': generateUUID()
    }
  });
  return resp.data;
}

export async function getVideo(videoId) {
  const resp = await api.get(`/videos/${videoId}`);
  return resp.data;
}

export async function getTranscript(videoId) {
  const resp = await api.get(`/videos/${videoId}/transcript`);
  return resp.data;
}

export async function sendInstruction(projectId, instruction, answer = null) {
  const body = { instruction };
  if (answer) {
    body.answer = answer;
  }
  const resp = await api.post(`/projects/${projectId}/instructions`, body, {
    headers: {
      'Idempotency-Key': generateUUID()
    }
  });
  return resp.data;
}

export async function getTimeline(projectId) {
  const resp = await api.get(`/projects/${projectId}/timeline`);
  return resp.data;
}

export async function getHistory(projectId) {
  const resp = await api.get(`/projects/${projectId}/history`);
  return resp.data;
}

export async function undo(projectId) {
  const resp = await api.post(`/projects/${projectId}/undo`);
  return resp.data;
}

export async function redo(projectId) {
  const resp = await api.post(`/projects/${projectId}/redo`);
  return resp.data;
}

export async function restore(projectId, stepIndex) {
  const resp = await api.post(`/projects/${projectId}/restore`, { step_index: stepIndex });
  return resp.data;
}

export async function renderVideo(projectId, callbackUrl = null) {
  const body = callbackUrl ? { callback_url: callbackUrl } : {};
  const resp = await api.post(`/projects/${projectId}/render`, body);
  return resp.data;
}

export async function getJob(jobId) {
  const resp = await api.get(`/jobs/${jobId}`);
  return resp.data;
}

export default api;
