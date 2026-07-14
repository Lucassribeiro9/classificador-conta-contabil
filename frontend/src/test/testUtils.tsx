import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, renderHook } from "@testing-library/react";
import type { RenderHookOptions, RenderOptions } from "@testing-library/react";
import type { PropsWithChildren, ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import type { MemoryRouterProps } from "react-router-dom";

import { AuthProvider } from "../app/auth";
import type { AuthSession } from "../app/auth";

type TestProviderOptions = {
  initialEntries?: MemoryRouterProps["initialEntries"];
  initialSession?: AuthSession | null;
  queryClient?: QueryClient;
};

type RenderWithProvidersOptions = TestProviderOptions &
  Omit<RenderOptions, "wrapper">;

type RenderHookWithProvidersOptions<Props> = TestProviderOptions &
  Omit<RenderHookOptions<Props>, "wrapper">;

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });
}

function createTestProviders({
  initialEntries = ["/"],
  initialSession = null,
  queryClient = createTestQueryClient(),
}: TestProviderOptions = {}) {
  function TestProviders({ children }: PropsWithChildren) {
    return (
      <QueryClientProvider client={queryClient}>
        <AuthProvider initialSession={initialSession}>
          <MemoryRouter initialEntries={initialEntries}>
            {children}
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );
  }

  return { queryClient, TestProviders };
}

export function renderWithProviders(
  ui: ReactElement,
  options: RenderWithProvidersOptions = {},
) {
  const { initialEntries, initialSession, queryClient, ...renderOptions } =
    options;
  const providers = createTestProviders({
    initialEntries,
    initialSession,
    queryClient,
  });

  return {
    queryClient: providers.queryClient,
    ...render(ui, {
      ...renderOptions,
      wrapper: providers.TestProviders,
    }),
  };
}

export function renderHookWithProviders<Result, Props = void>(
  callback: (initialProps: Props) => Result,
  options: RenderHookWithProvidersOptions<Props> = {},
) {
  const { initialEntries, initialSession, queryClient, ...renderOptions } =
    options;
  const providers = createTestProviders({
    initialEntries,
    initialSession,
    queryClient,
  });

  return {
    queryClient: providers.queryClient,
    ...renderHook(callback, {
      ...renderOptions,
      wrapper: providers.TestProviders,
    }),
  };
}
