import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api } from '../api';

// ── Helpers ─────────────────────────────────────────────

function mockFetchResponse(body: unknown, status = 200, ok = true) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    json: vi.fn().mockResolvedValue(body),
  });
}

// ── Setup ───────────────────────────────────────────────

beforeEach(() => {
  // Clear any stored token
  localStorage.clear();
  // Reset fetch mock
  vi.stubGlobal('fetch', vi.fn());
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ── Tests ───────────────────────────────────────────────

describe('api.login', () => {
  it('calls POST /api/auth/login with credentials', async () => {
    const fetchMock = mockFetchResponse({ token: 'abc123' });
    vi.stubGlobal('fetch', fetchMock);

    const result = await api.login('alice', 'password123');

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/auth/login');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body)).toEqual({ username: 'alice', password: 'password123' });
    expect(opts.headers['Content-Type']).toBe('application/json');
    expect(result).toEqual({ token: 'abc123' });
  });
});

describe('api.sendMessage', () => {
  it('calls POST /api/message with body', async () => {
    const fetchMock = mockFetchResponse({ status: 'ok' });
    vi.stubGlobal('fetch', fetchMock);

    await api.sendMessage('Hello', 'general');

    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/message');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body)).toEqual({ message: 'Hello', mode: 'general' });
  });
});

describe('api.listConversations', () => {
  it('calls GET /api/conversations', async () => {
    const fetchMock = mockFetchResponse([{ uuid: 'conv-1', title: 'Test' }]);
    vi.stubGlobal('fetch', fetchMock);

    const result = await api.listConversations();

    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/conversations');
    expect(opts.method).toBe('GET');
    expect(opts.body).toBeUndefined();
    expect(result).toEqual([{ uuid: 'conv-1', title: 'Test' }]);
  });
});

describe('Authorization header', () => {
  it('sets Authorization header from localStorage token', async () => {
    localStorage.setItem('openmlr_token', 'my-secret-token');
    const fetchMock = mockFetchResponse({ ok: true });
    vi.stubGlobal('fetch', fetchMock);

    await api.listConversations();

    const [, opts] = fetchMock.mock.calls[0];
    expect(opts.headers['Authorization']).toBe('Bearer my-secret-token');
  });

  it('does not set Authorization header when no token', async () => {
    const fetchMock = mockFetchResponse({ ok: true });
    vi.stubGlobal('fetch', fetchMock);

    await api.listConversations();

    const [, opts] = fetchMock.mock.calls[0];
    expect(opts.headers['Authorization']).toBeUndefined();
  });
});

describe('error handling', () => {
  it('throws on non-ok response', async () => {
    const fetchMock = mockFetchResponse(
      { detail: 'Bad request' },
      400,
      false,
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(api.sendMessage('test')).rejects.toThrow('Bad request');
  });

  it('throws generic HTTP error when response body has no detail', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: vi.fn().mockRejectedValue(new Error('parse fail')),
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(api.sendMessage('test')).rejects.toThrow('HTTP 500');
  });

  it('clears token on 401 response', async () => {
    localStorage.setItem('openmlr_token', 'expired-token');
    expect(localStorage.getItem('openmlr_token')).toBe('expired-token');

    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: vi.fn().mockResolvedValue({ detail: 'Unauthorized' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(api.getMe()).rejects.toThrow('Unauthorized');
    expect(localStorage.getItem('openmlr_token')).toBeNull();
  });
});
