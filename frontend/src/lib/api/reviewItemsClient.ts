import { apiClient } from "./apiClient";

export type ReviewEvidence = {
  id: number;
  sourceType: string;
  sourceId: string;
  summary: string;
  createdAt: string;
};

export type ReviewItem = {
  id: number;
  empresaId: number;
  sourceType: string;
  groupingKey: string;
  summary: string;
  criticality: "low" | "medium" | "high" | "critical";
  status: "pending" | "in_review" | "resolved" | "dismissed";
  assigneeId: number | null;
  assigneeName: string | null;
  claimedAt: string | null;
  createdAt: string;
  updatedAt: string;
  resolvedAt: string | null;
  dismissedAt: string | null;
  availableActions: string[];
  evidences: ReviewEvidence[];
};

export type ReviewItemPage = {
  items: ReviewItem[];
  total: number;
  page: number;
  limit: number;
  hasNext: boolean;
};

export type ReviewAssignee = { id: number; nome: string };

type ReviewEvidenceApi = {
  id: number;
  source_type: string;
  source_id: string;
  summary: string;
  created_at: string;
};

type ReviewItemApi = {
  id: number;
  empresa_id: number;
  source_type: string;
  grouping_key: string;
  summary: string;
  criticality: ReviewItem["criticality"];
  status: ReviewItem["status"];
  assignee_id: number | null;
  assignee_name: string | null;
  claimed_at: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  dismissed_at: string | null;
  available_actions: string[];
  evidences: ReviewEvidenceApi[];
};

type ReviewItemPageApi = {
  items: ReviewItemApi[];
  total: number;
  page: number;
  limit: number;
  has_next: boolean;
};

function mapItem(item: ReviewItemApi): ReviewItem {
  return {
    id: item.id,
    empresaId: item.empresa_id,
    sourceType: item.source_type,
    groupingKey: item.grouping_key,
    summary: item.summary,
    criticality: item.criticality,
    status: item.status,
    assigneeId: item.assignee_id,
    assigneeName: item.assignee_name,
    claimedAt: item.claimed_at,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
    resolvedAt: item.resolved_at,
    dismissedAt: item.dismissed_at,
    availableActions: item.available_actions,
    evidences: item.evidences.map((evidence) => ({
      id: evidence.id,
      sourceType: evidence.source_type,
      sourceId: evidence.source_id,
      summary: evidence.summary,
      createdAt: evidence.created_at,
    })),
  };
}

function root(companyId: string) {
  return `/api/v1/companies/${encodeURIComponent(companyId)}/review-items`;
}

async function list(
  accessToken: string,
  companyId: string,
  page = 1,
  status = "open",
): Promise<ReviewItemPage> {
  const data = await apiClient.get<ReviewItemPageApi>(
    `${root(companyId)}?status=${encodeURIComponent(status)}&page=${page}&limit=100`,
    { accessToken },
  );
  return {
    items: data.items.map(mapItem),
    total: data.total,
    page: data.page,
    limit: data.limit,
    hasNext: data.has_next,
  };
}

async function listAssignees(
  accessToken: string,
  companyId: string,
): Promise<ReviewAssignee[]> {
  const data = await apiClient.get<{ items: ReviewAssignee[] }>(
    `${root(companyId)}/assignees`,
    { accessToken },
  );
  return data.items;
}

async function transition(
  action: string,
  accessToken: string,
  companyId: string,
  itemId: number,
  body?: Record<string, unknown>,
): Promise<ReviewItem> {
  const item = await apiClient.post<ReviewItemApi>(
    `${root(companyId)}/${itemId}/${action}`,
    { accessToken, body },
  );
  return mapItem(item);
}

export const reviewItemsClient = {
  list,
  listAssignees,
  claim: (token: string, company: string, id: number) =>
    transition("claim", token, company, id),
  release: (token: string, company: string, id: number) =>
    transition("release", token, company, id),
  resolve: (token: string, company: string, id: number) =>
    transition("resolve", token, company, id),
  dismiss: (token: string, company: string, id: number, reason: string) =>
    transition("dismiss", token, company, id, { reason }),
  reopen: (token: string, company: string, id: number, reason: string) =>
    transition("reopen", token, company, id, { reason }),
  reassign: (
    token: string,
    company: string,
    id: number,
    assigneeId: number,
    reason: string,
  ) =>
    transition("reassign", token, company, id, {
      assignee_id: assigneeId,
      reason,
    }),
};
