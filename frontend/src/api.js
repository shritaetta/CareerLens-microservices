export const API = import.meta.env.VITE_API_URL ?? '/api';

/**
 * Resolves a file URL to a valid URL for <a> previews and downloads.
 * Handles relative URLs like /api/files/uploads/... or legacy /uploads/...
 */
export function getFileUrl(url) {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  let normalized = url;
  if (normalized.startsWith('/uploads/')) {
    normalized = `/api/files${normalized}`;
  }
  if (API.startsWith('http://') || API.startsWith('https://')) {
    try {
      const parsedApi = new URL(API);
      return `${parsedApi.origin}${normalized.startsWith('/') ? normalized : `/${normalized}`}`;
    } catch {
      // ignore parsing error, return relative
    }
  }
  return normalized;
}

/**
 * Wrapper around window.fetch that:
 * - Prepends API base path if needed
 * - Attaches Authorization: Bearer <token> from localStorage('access_token')
 * - On 401, clears storage and redirects to /login
 */
export async function apiFetch(path, options = {}) {
  let url = path;
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    const base = API.replace(/\/$/, '');
    if (url.startsWith('/api/')) {
      if (base.endsWith('/api')) {
        url = `${base}${url.slice(4)}`;
      } else {
        url = `${base}${url}`;
      }
    } else {
      const cleanPath = url.startsWith('/') ? url : `/${url}`;
      url = `${base}${cleanPath}`;
    }
  }

  const headers = new Headers(options.headers || {});
  const token = localStorage.getItem('access_token');
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const config = {
    ...options,
    headers,
  };

  const response = await fetch(url, config);

  if (response.status === 401) {
    localStorage.clear();
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }

  return response;
}
