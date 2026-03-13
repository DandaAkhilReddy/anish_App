/**
 * Tests for src/services/api.ts and src/services/stockApi.ts
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock config before importing the modules under test so the module-level
// `config` binding is resolved against our controlled value.
vi.mock('../../config/env', () => ({
  config: { apiUrl: 'http://test-host', wsUrl: '' },
}));

import { ApiError, get, post } from '../../services/api';
import { analyzeStock } from '../../services/stockApi';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a minimal Response-like object accepted by globalThis.fetch mock. */
function makeResponse(
  status: number,
  body: unknown,
  ok: boolean = status >= 200 && status < 300,
): Response {
  return {
    ok,
    status,
    json: vi.fn().mockResolvedValue(body),
  } as unknown as Response;
}

// ---------------------------------------------------------------------------
// ApiError
// ---------------------------------------------------------------------------

describe('ApiError', () => {
  it('sets status, code, and message from constructor arguments', () => {
    const err = new ApiError(404, 'NOT_FOUND', 'Resource not found');

    expect(err.status).toBe(404);
    expect(err.code).toBe('NOT_FOUND');
    expect(err.message).toBe('Resource not found');
  });

  it('sets name to "ApiError"', () => {
    const err = new ApiError(500, 'SERVER_ERROR', 'Internal error');

    expect(err.name).toBe('ApiError');
  });

  it('is an instance of Error', () => {
    const err = new ApiError(400, 'BAD_REQUEST', 'Bad request');

    expect(err).toBeInstanceOf(Error);
  });

  it('is an instance of ApiError', () => {
    const err = new ApiError(401, 'UNAUTHORIZED', 'Unauthorized');

    expect(err).toBeInstanceOf(ApiError);
  });
});

// ---------------------------------------------------------------------------
// get()
// ---------------------------------------------------------------------------

describe('get', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('calls fetch with the correct URL built from config.apiUrl + path', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockResolvedValue(makeResponse(200, { data: 'ok' }));

    await get('/api/health');

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('http://test-host/api/health');
  });

  it('calls fetch with method GET', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockResolvedValue(makeResponse(200, {}));

    await get('/api/health');

    const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(options.method).toBe('GET');
  });

  it('includes Content-Type: application/json header', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockResolvedValue(makeResponse(200, {}));

    await get('/api/health');

    const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect((options.headers as Record<string, string>)['Content-Type']).toBe(
      'application/json',
    );
  });

  it('returns the parsed JSON body on a successful response', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    const payload = { ticker: 'AAPL', price: 180 };
    mockFetch.mockResolvedValue(makeResponse(200, payload));

    const result = await get<typeof payload>('/api/stocks/AAPL');

    expect(result).toEqual(payload);
  });

  it('passes an AbortSignal so the request can be timed out', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockResolvedValue(makeResponse(200, {}));

    await get('/api/health');

    const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(options.signal).toBeInstanceOf(AbortSignal);
  });

  it('throws ApiError with parsed code and message when response body is structured', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockResolvedValue(
      makeResponse(422, { error: { code: 'VALIDATION_ERROR', message: 'Invalid ticker' } }, false),
    );

    await expect(get('/api/stocks/???')).rejects.toSatisfy((err: unknown) => {
      const apiErr = err as ApiError;
      return (
        apiErr instanceof ApiError &&
        apiErr.status === 422 &&
        apiErr.code === 'VALIDATION_ERROR' &&
        apiErr.message === 'Invalid ticker'
      );
    });
  });

  it('throws ApiError with fallback "HTTP {status}" message when body is not parseable JSON', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    const badResponse = {
      ok: false,
      status: 503,
      json: vi.fn().mockRejectedValue(new SyntaxError('Unexpected token')),
    } as unknown as Response;
    mockFetch.mockResolvedValue(badResponse);

    await expect(get('/api/health')).rejects.toSatisfy((err: unknown) => {
      const apiErr = err as ApiError;
      return (
        apiErr instanceof ApiError &&
        apiErr.status === 503 &&
        apiErr.code === 'UNKNOWN_ERROR' &&
        apiErr.message === 'HTTP 503'
      );
    });
  });

  it('throws ApiError with UNKNOWN_ERROR code when error body lacks expected shape', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    // Body is valid JSON but does not have .error.code / .error.message
    mockFetch.mockResolvedValue(
      makeResponse(500, { unexpected: 'shape' }, false),
    );

    await expect(get('/api/health')).rejects.toSatisfy((err: unknown) => {
      const apiErr = err as ApiError;
      return (
        apiErr instanceof ApiError &&
        apiErr.status === 500 &&
        apiErr.code === 'UNKNOWN_ERROR'
      );
    });
  });
});

// ---------------------------------------------------------------------------
// post()
// ---------------------------------------------------------------------------

describe('post', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('calls fetch with method POST', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockResolvedValue(makeResponse(200, {}));

    await post('/api/analyze/AAPL');

    const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(options.method).toBe('POST');
  });

  it('serializes the body to JSON when a body is provided', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockResolvedValue(makeResponse(200, {}));

    const payload = { ticker: 'TSLA', include_news: true };
    await post('/api/analyze', payload);

    const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(options.body).toBe(JSON.stringify(payload));
  });

  it('sets body to undefined when no body argument is passed', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockResolvedValue(makeResponse(200, {}));

    await post('/api/analyze/AAPL');

    const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(options.body).toBeUndefined();
  });

  it('returns the parsed JSON body on success', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    const response = { ticker: 'GOOG', recommendation: 'buy' };
    mockFetch.mockResolvedValue(makeResponse(200, response));

    const result = await post<typeof response>('/api/analyze/GOOG');

    expect(result).toEqual(response);
  });

  it('includes Content-Type: application/json header', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockResolvedValue(makeResponse(200, {}));

    await post('/api/analyze/AAPL', { data: 1 });

    const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect((options.headers as Record<string, string>)['Content-Type']).toBe(
      'application/json',
    );
  });

  it('throws ApiError on HTTP error response with structured body', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockResolvedValue(
      makeResponse(400, { error: { code: 'BAD_REQUEST', message: 'Missing ticker' } }, false),
    );

    await expect(post('/api/analyze')).rejects.toSatisfy((err: unknown) => {
      const apiErr = err as ApiError;
      return (
        apiErr instanceof ApiError &&
        apiErr.status === 400 &&
        apiErr.code === 'BAD_REQUEST' &&
        apiErr.message === 'Missing ticker'
      );
    });
  });

  it('throws ApiError with fallback message on non-JSON error body', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    const badResponse = {
      ok: false,
      status: 502,
      json: vi.fn().mockRejectedValue(new SyntaxError('Bad JSON')),
    } as unknown as Response;
    mockFetch.mockResolvedValue(badResponse);

    await expect(post('/api/analyze')).rejects.toSatisfy((err: unknown) => {
      const apiErr = err as ApiError;
      return (
        apiErr instanceof ApiError &&
        apiErr.status === 502 &&
        apiErr.code === 'UNKNOWN_ERROR' &&
        apiErr.message === 'HTTP 502'
      );
    });
  });
});

// ---------------------------------------------------------------------------
// request() error branches — timeout, network retry, network exhausted
// ---------------------------------------------------------------------------

describe('request error branches', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('throws ApiError with status 408 and code TIMEOUT on AbortError', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    const abortError = new DOMException('signal is aborted', 'AbortError');
    mockFetch.mockRejectedValue(abortError);

    await expect(get('/test')).rejects.toSatisfy((err: unknown) => {
      const e = err as ApiError;
      return e instanceof ApiError && e.status === 408 && e.code === 'TIMEOUT';
    });
  });

  it('AbortError message mentions timed out', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockRejectedValue(new DOMException('aborted', 'AbortError'));

    await expect(get('/test')).rejects.toSatisfy((err: unknown) => {
      const e = err as ApiError;
      return e instanceof ApiError && e.message.toLowerCase().includes('timed out');
    });
  });

  it('retries on network error and succeeds on final attempt', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(makeResponse(200, { ok: true }));

    const promise = get<{ ok: boolean }>('/test');

    // Advance past first retry backoff (attempt 0 → delay 2000ms)
    await vi.advanceTimersByTimeAsync(2000);
    // Advance past second retry backoff (attempt 1 → delay 4000ms)
    await vi.advanceTimersByTimeAsync(4000);

    const result = await promise;
    expect(result).toEqual({ ok: true });
    expect(mockFetch).toHaveBeenCalledTimes(3);
  });

  it('throws ApiError with status 0 and code NETWORK_ERROR after all retries exhausted', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockRejectedValue(new TypeError('Failed to fetch'));

    // Capture the rejection before advancing timers so Vitest tracks it from the start
    let caughtError: unknown;
    const promise = get('/test').catch((e) => { caughtError = e; });

    // Advance past all retry backoffs: attempt 0 → 2000ms, attempt 1 → 4000ms
    await vi.advanceTimersByTimeAsync(10_000);
    await promise;

    const e = caughtError as ApiError;
    expect(e).toBeInstanceOf(ApiError);
    expect(e.status).toBe(0);
    expect(e.code).toBe('NETWORK_ERROR');
    // 1 original attempt + 2 retries
    expect(mockFetch).toHaveBeenCalledTimes(3);
  });

  it('NETWORK_ERROR message mentions connection', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockRejectedValue(new TypeError('Failed to fetch'));

    let caughtError: unknown;
    const promise = get('/test').catch((e) => { caughtError = e; });
    await vi.advanceTimersByTimeAsync(10_000);
    await promise;

    const e = caughtError as ApiError;
    expect(e).toBeInstanceOf(ApiError);
    expect(e.message.toLowerCase()).toContain('connection');
  });

  it('does not retry on AbortError — fetch is called exactly once', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockRejectedValue(new DOMException('aborted', 'AbortError'));

    await expect(get('/test')).rejects.toBeInstanceOf(ApiError);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it('does not retry on ApiError (4xx) — fetch is called exactly once', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockResolvedValue(
      makeResponse(404, { error: { code: 'NOT_FOUND', message: 'Not found' } }, false),
    );

    await expect(get('/test')).rejects.toBeInstanceOf(ApiError);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// analyzeStock()
// ---------------------------------------------------------------------------

describe('analyzeStock', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('calls POST with the path /api/analyze/{ticker}', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockResolvedValue(makeResponse(200, { ticker: 'AAPL' }));

    await analyzeStock('AAPL');

    const [url, options] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('http://test-host/api/analyze/AAPL');
    expect(options.method).toBe('POST');
  });

  it('URL-encodes special characters in the ticker symbol', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockResolvedValue(makeResponse(200, { ticker: 'BRK.B' }));

    await analyzeStock('BRK.B');

    const [url] = mockFetch.mock.calls[0] as [string, RequestInit];
    // encodeURIComponent('BRK.B') === 'BRK.B' (dot is safe), but a ticker
    // with a slash or space must be encoded — verify the call goes through
    // encodeURIComponent by checking a ticker that does need encoding.
    expect(url).toContain(encodeURIComponent('BRK.B'));
  });

  it('URL-encodes a ticker containing a forward slash', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockResolvedValue(makeResponse(200, { ticker: 'A/B' }));

    await analyzeStock('A/B');

    const [url] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('http://test-host/api/analyze/A%2FB');
  });

  it('returns the StockAnalysisResponse parsed from the response body', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    const mockAnalysis = {
      ticker: 'MSFT',
      company_name: 'Microsoft',
      current_price: 420,
      recommendation: 'buy',
    };
    mockFetch.mockResolvedValue(makeResponse(200, mockAnalysis));

    const result = await analyzeStock('MSFT');

    expect(result).toEqual(mockAnalysis);
  });

  it('propagates ApiError when the backend returns an HTTP error', async () => {
    const mockFetch = vi.mocked(globalThis.fetch);
    mockFetch.mockResolvedValue(
      makeResponse(404, { error: { code: 'TICKER_NOT_FOUND', message: 'Unknown ticker XYZ' } }, false),
    );

    await expect(analyzeStock('XYZ')).rejects.toSatisfy((err: unknown) => {
      const apiErr = err as ApiError;
      return (
        apiErr instanceof ApiError &&
        apiErr.status === 404 &&
        apiErr.code === 'TICKER_NOT_FOUND'
      );
    });
  });
});
