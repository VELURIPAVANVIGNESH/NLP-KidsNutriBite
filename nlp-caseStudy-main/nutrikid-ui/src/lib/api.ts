// NutriKid API Client — clean abstraction layer for all backend calls

import type { AskResult, SearchResponse, HealthResponse } from './types';

const getAPIBase = () =>
  typeof window !== 'undefined'
    ? (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
    : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');

export class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'APIError';
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const base = getAPIBase();
  const res = await fetch(`${base}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch {
      // ignore
    }
    throw new APIError(res.status, detail);
  }
  return res.json();
}

export interface StreamCallbacks {
  onStage?: (stage: number, name: string, label: string) => void;
  onToken?: (token: string) => void;
  onDone?: (result: AskResult) => void;
  onError?: (error: string) => void;
}

export const api = {
  health(): Promise<HealthResponse> {
    return apiFetch<HealthResponse>('/api/health');
  },

  ask(question: string, age: number): Promise<AskResult> {
    return apiFetch<AskResult>('/api/ask', {
      method: 'POST',
      body: JSON.stringify({ question, age }),
    });
  },

  async askStream(question: string, age: number, callbacks: StreamCallbacks): Promise<AskResult> {
    const base = getAPIBase();
    const res = await fetch(`${base}/api/ask/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, age }),
    });

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const err = await res.json();
        detail = err.detail || detail;
      } catch {}
      throw new APIError(res.status, detail);
    }

    const reader = res.body?.getReader();
    if (!reader) throw new APIError(500, 'Streaming not supported by browser');
    const decoder = new TextDecoder();
    let buffer = '';
    let finalResult: AskResult | null = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop() || '';

      for (const block of blocks) {
        const line = block.trim();
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.event === 'stage' && callbacks.onStage) {
              callbacks.onStage(data.stage, data.name, data.label);
            } else if (data.event === 'token' && callbacks.onToken) {
              callbacks.onToken(data.token);
            } else if (data.event === 'done') {
              finalResult = data.result;
              if (callbacks.onDone) callbacks.onDone(data.result);
            } else if (data.event === 'error') {
              if (callbacks.onError) callbacks.onError(data.error);
              throw new APIError(500, data.error);
            }
          } catch (err) {
            if (err instanceof APIError) throw err;
          }
        }
      }
    }

    if (!finalResult) {
      throw new APIError(500, 'Stream ended unexpectedly without result payload');
    }
    return finalResult;
  },

  searchFaiss(query: string, k: number): Promise<SearchResponse> {
    return apiFetch<SearchResponse>('/api/similarity-search/faiss', {
      method: 'POST',
      body: JSON.stringify({ query, k }),
    });
  },

  searchChroma(query: string, k: number): Promise<SearchResponse> {
    return apiFetch<SearchResponse>('/api/similarity-search/chroma', {
      method: 'POST',
      body: JSON.stringify({ query, k }),
    });
  },
};
