import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

export const fetchDisagreements = async (org, reason = null, sort = null) => {
  const params = { org };
  if (reason && reason !== 'ALL') {
    params.reason = reason;
  }
  if (sort) {
    params.sort = sort;
  }
  const response = await apiClient.get('/disagreements/', { params });
  return response.data;
};

export const fetchSummary = async (org) => {
  const response = await apiClient.get('/summary/', { params: { org } });
  return response.data;
};

export const fetchOrganizations = async () => {
  const response = await apiClient.get('/organizations/');
  return response.data.organizations;
};

export default apiClient;
