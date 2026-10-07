import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../../app/auth";
import { reviewItemsClient } from "../../lib/api/reviewItemsClient";
import { ROUTES } from "../paths";
import { ReviewItemsPage } from "./ReviewItemsPage";

vi.mock("../../lib/api/reviewItemsClient", () => ({
  reviewItemsClient: {
    list: vi.fn(),
    get: vi.fn(),
    listAssignees: vi.fn(),
    claim: vi.fn(),
    release: vi.fn(),
    reassign: vi.fn(),
    resolve: vi.fn(),
    dismiss: vi.fn(),
    reopen: vi.fn(),
  },
}));

const listMock = vi.mocked(reviewItemsClient.list);
const getMock = vi.mocked(reviewItemsClient.get);
const claimMock = vi.mocked(reviewItemsClient.claim);

function renderPage(path = ROUTES.empresa.reviewItems("7")) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider initialSession={{ accessToken: "jwt", userEmail: "user@test" }}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route
              path={ROUTES.empresa.reviewItemsPath}
              element={<ReviewItemsPage />}
            />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("ReviewItemsPage", () => {
  beforeEach(() => {
    listMock.mockReset();
    getMock.mockReset();
    claimMock.mockReset();
  });

  it("lists safe evidence and claims an item when the API allows it", async () => {
    listMock.mockResolvedValue({
      items: [
        {
          id: 21,
          empresaId: 7,
          sourceType: "snapshot_conflict",
          groupingKey: "snapshot:2026-01-01",
          summary: "Conflito de vigência",
          criticality: "high",
          status: "pending",
          assigneeId: null,
          assigneeName: null,
          claimedAt: null,
          createdAt: "2026-01-02T10:00:00",
          updatedAt: "2026-01-02T10:00:00",
          resolvedAt: null,
          dismissedAt: null,
          availableActions: ["claim"],
          evidences: [
            {
              id: 1,
              sourceType: "snapshot",
              sourceId: "snapshot-a",
              summary: "Primeira evidência",
              createdAt: "2026-01-02T10:00:00",
            },
          ],
        },
      ],
      total: 1,
      page: 1,
      limit: 100,
      hasNext: false,
    });
    claimMock.mockResolvedValueOnce({} as never);

    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Central de Revisões" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Conflito de vigência")).toBeInTheDocument();
    expect(screen.getByText("Primeira evidência")).toBeInTheDocument();
    expect(listMock).toHaveBeenCalledWith("jwt", "7", 1, "open");
    fireEvent.click(screen.getByRole("button", { name: "Assumir" }));
    await waitFor(() => {
      expect(claimMock).toHaveBeenCalledWith("jwt", "7", 21);
    });
  });

  it("hides operations the API did not authorize", async () => {
    listMock.mockResolvedValue({
      items: [
        {
          id: 22,
          empresaId: 7,
          sourceType: "snapshot_conflict",
          groupingKey: "read-only",
          summary: "Consulta apenas",
          criticality: "low",
          status: "pending",
          assigneeId: null,
          assigneeName: null,
          claimedAt: null,
          createdAt: "2026-01-02T10:00:00",
          updatedAt: "2026-01-02T10:00:00",
          resolvedAt: null,
          dismissedAt: null,
          availableActions: [],
          evidences: [],
        },
      ],
      total: 1,
      page: 1,
      limit: 100,
      hasNext: false,
    });

    renderPage();

    expect(await screen.findByText("Consulta apenas")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Assumir" })).toBeNull();
  });

  it("abre uma pendência por ID mesmo fora da página atual", async () => {
    listMock.mockResolvedValue({
      items: [], total: 150, page: 1, limit: 100, hasNext: true,
    });
    getMock.mockResolvedValue({
      id: 501,
      empresaId: 7,
      sourceType: "movimento_operacional_manual",
      groupingKey: "movimento:91",
      summary: "Movimento operacional 91 enviado para revisão",
      criticality: "medium",
      status: "pending",
      assigneeId: null,
      assigneeName: null,
      claimedAt: null,
      createdAt: "2026-01-02T10:00:00",
      updatedAt: "2026-01-02T10:00:00",
      resolvedAt: null,
      dismissedAt: null,
      availableActions: ["claim"],
      evidences: [],
    });

    renderPage(`${ROUTES.empresa.reviewItems("7")}?itemId=501`);

    expect(await screen.findByText("Movimento operacional 91 enviado para revisão")).toBeInTheDocument();
    expect(getMock).toHaveBeenCalledWith("jwt", "7", 501);
  });
});
