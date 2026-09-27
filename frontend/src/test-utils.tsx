import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

export interface RecordedCall {
  method: string;
  path: string;
  search: string;
  body: unknown;
}

type Handler = (call: RecordedCall) => { status?: number; body?: unknown } | undefined;

/** fetch'i "METHOD /yol" anahtarlı yanıtlarla değiştirir ve yapılan çağrıları kaydeder. */
export function mockFetch(routes: Record<string, Handler | unknown>) {
  const calls: RecordedCall[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input));
      const method = init?.method ?? "GET";
      let body: unknown = undefined;
      if (typeof init?.body === "string") {
        try {
          body = JSON.parse(init.body);
        } catch {
          body = init.body;
        }
      } else if (init?.body instanceof URLSearchParams) {
        body = Object.fromEntries(init.body);
      }
      const call = { method, path: url.pathname, search: url.search, body };
      calls.push(call);

      const route = routes[`${method} ${url.pathname}`];
      if (route === undefined) return new Response(JSON.stringify({ detail: "Bulunamadı" }), { status: 404 });
      const result = typeof route === "function" ? (route as Handler)(call) : { body: route };
      const status = result?.status ?? 200;
      if (status === 204) return new Response(null, { status });
      return new Response(JSON.stringify(result?.body ?? null), {
        status,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
  return calls;
}

export function renderWithProviders(ui: ReactElement, { route = "/" }: { route?: string } = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}
