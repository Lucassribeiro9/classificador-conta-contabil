import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { useAuth } from "../../app/auth";
import {
  ApiAccessDeniedError,
  ApiSessionExpiredError,
} from "../../lib/api/apiClient";
import { reviewItemsClient } from "../../lib/api/reviewItemsClient";
import type { ReviewItem } from "../../lib/api/reviewItemsClient";
import { PageState } from "../../ui/operationalMessages";
import { ROUTES } from "../paths";

const criticalityLabels: Record<ReviewItem["criticality"], string> = {
  low: "Baixa",
  medium: "Média",
  high: "Alta",
  critical: "Crítica",
};

const statusLabels: Record<ReviewItem["status"], string> = {
  pending: "Pendente",
  in_review: "Em revisão",
  resolved: "Resolvida",
  dismissed: "Descartada",
};

function itemDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export function ReviewItemsPage() {
  const { empresaId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const requestedItemId = Number(searchParams.get("itemId"));
  const selectedItemId = Number.isSafeInteger(requestedItemId) && requestedItemId > 0
    ? requestedItemId : null;
  const { session, setSession } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const accessToken = session?.accessToken ?? "";
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("open");
  const [reasons, setReasons] = useState<Record<number, string>>({});
  const [assignees, setAssignees] = useState<Record<number, number | undefined>>(
    {},
  );
  const [success, setSuccess] = useState("");

  const items = useQuery({
    queryKey: ["empresas", empresaId, "review-items", status, page],
    queryFn: () => reviewItemsClient.list(accessToken, empresaId, page, status),
    enabled: Boolean(accessToken && empresaId),
    retry: false,
  });
  const selectedItem = useQuery({
    queryKey: ["empresas", empresaId, "review-items", "item", selectedItemId],
    queryFn: () => reviewItemsClient.get(accessToken, empresaId, selectedItemId!),
    enabled: Boolean(accessToken && empresaId && selectedItemId),
    retry: false,
  });
  const canReassign = items.data?.items.some((item) =>
    item.availableActions.includes("reassign"),
  );
  const reviewers = useQuery({
    queryKey: ["empresas", empresaId, "review-item-assignees"],
    queryFn: () => reviewItemsClient.listAssignees(accessToken, empresaId),
    enabled: Boolean(accessToken && empresaId && canReassign),
    retry: false,
  });

  const action = useMutation({
    mutationFn: ({
      name,
      item,
      reason,
      assigneeId,
    }: {
      name: string;
      item: ReviewItem;
      reason?: string;
      assigneeId?: number;
    }) => {
      if (name === "claim") {
        return reviewItemsClient.claim(accessToken, empresaId, item.id);
      }
      if (name === "release") {
        return reviewItemsClient.release(accessToken, empresaId, item.id);
      }
      if (name === "resolve") {
        return reviewItemsClient.resolve(accessToken, empresaId, item.id);
      }
      if (name === "dismiss") {
        return reviewItemsClient.dismiss(
          accessToken,
          empresaId,
          item.id,
          reason ?? "",
        );
      }
      if (name === "reopen") {
        return reviewItemsClient.reopen(
          accessToken,
          empresaId,
          item.id,
          reason ?? "",
        );
      }
      if (name === "reassign" && assigneeId) {
        return reviewItemsClient.reassign(
          accessToken,
          empresaId,
          item.id,
          assigneeId,
          reason ?? "",
        );
      }
      throw new Error("Ação de revisão inválida");
    },
    onSuccess: (_result, variables) => {
      setSuccess(`Ação ${variables.name} concluída.`);
      setReasons((current) => ({ ...current, [variables.item.id]: "" }));
      void queryClient.invalidateQueries({
        queryKey: ["empresas", empresaId, "review-items"],
      });
    },
  });

  useEffect(() => {
    if (
      items.error instanceof ApiSessionExpiredError ||
      selectedItem.error instanceof ApiSessionExpiredError ||
      reviewers.error instanceof ApiSessionExpiredError ||
      action.error instanceof ApiSessionExpiredError
    ) {
      setSession(null);
      navigate(ROUTES.login, { replace: true });
    }
  }, [items.error, selectedItem.error, reviewers.error, action.error, navigate, setSession]);

  if (items.isLoading) {
    return (
      <PageState
        message={{
          title: "Carregando revisões",
          description: "Buscando pendências abertas para esta empresa.",
        }}
      />
    );
  }
  if (items.error instanceof ApiAccessDeniedError) {
    return (
      <PageState
        message={{
          title: "Acesso negado",
          description: "Seu usuário não pode consultar esta empresa.",
        }}
      />
    );
  }
  if (items.isError || !items.data) {
    return (
      <PageState
        message={{
          title: "Não foi possível carregar as revisões",
          description: "Verifique a API interna e tente novamente.",
        }}
      />
    );
  }

  if (selectedItemId && selectedItem.isLoading) {
    return <PageState message={{ title: "Carregando pendência", description: "Buscando o item selecionado." }} />;
  }
  if (selectedItemId && selectedItem.isError) {
    return <PageState message={{ title: "Pendência não encontrada", description: "Confira o ID ou volte à fila da empresa." }} />;
  }
  const visibleItems = selectedItemId && selectedItem.data
    ? [selectedItem.data] : items.data.items;

  return (
    <section className="space-y-5">
      <header className="border-l-4 border-brand bg-white px-5 py-4 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-dark">
          Empresa {empresaId} · fila de decisão humana
        </p>
        <h1 className="mt-1 text-2xl font-semibold text-slate-950">
          Central de Revisões
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-600">
          Pendências abertas com evidências rastreáveis. Cada decisão registra
          responsável e histórico.
        </p>
      </header>

      {selectedItemId ? (
        <Link className="text-sm font-semibold text-brand-dark underline" to={ROUTES.empresa.reviewItems(empresaId)}>
          Voltar à fila completa
        </Link>
      ) : null}

      {success ? (
        <p className="border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900" role="status">
          {success}
        </p>
      ) : null}
      {action.error instanceof ApiAccessDeniedError ? (
        <p className="border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900" role="alert">
          Seu usuário não tem permissão para essa ação.
        </p>
      ) : null}
      {action.isError && !(action.error instanceof ApiAccessDeniedError) ? (
        <p className="border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900" role="alert">
          A ação não foi concluída. Atualize a fila e tente novamente.
        </p>
      ) : null}
      {reviewers.error instanceof ApiAccessDeniedError ? (
        <p className="border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900" role="alert">
          A lista de responsáveis está disponível somente para administradores da empresa.
        </p>
      ) : null}

      <div className="flex items-center justify-between border-b border-slate-200 pb-3">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm text-slate-700">
            Mostrar
            <select
              aria-label="Filtrar pendências"
              className="ml-2 border border-slate-300 px-2 py-2"
              onChange={(event) => {
                setStatus(event.target.value);
                setPage(1);
              }}
              value={status}
            >
              <option value="open">Abertas</option>
              <option value="resolved">Resolvidas</option>
              <option value="dismissed">Descartadas</option>
            </select>
          </label>
          <p className="text-sm text-slate-600">
            {items.data.total} pendência{items.data.total === 1 ? "" : "s"}{" "}
            {status === "open" ? "aberta" : status === "resolved" ? "resolvida" : "descartada"}
            {items.data.total === 1 ? "" : "s"} · página {items.data.page}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            className="border border-slate-300 px-3 py-2 text-sm disabled:opacity-40"
            disabled={page <= 1 || items.isFetching}
            onClick={() => setPage((current) => current - 1)}
            type="button"
          >
            Anterior
          </button>
          <button
            className="border border-slate-300 px-3 py-2 text-sm disabled:opacity-40"
            disabled={!items.data.hasNext || items.isFetching}
            onClick={() => setPage((current) => current + 1)}
            type="button"
          >
            Próxima
          </button>
        </div>
      </div>

      {visibleItems.length === 0 ? (
        <PageState
          titleAs="h2"
          message={{
            title: "Nenhuma pendência aberta",
            description: "Quando um domínio solicitar uma decisão humana, ela aparecerá nesta fila.",
          }}
        />
      ) : (
        <div className="space-y-3">
          {visibleItems.map((item) => (
            <article
              className="border border-slate-200 bg-white p-5 shadow-sm"
              key={item.id}
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="border border-slate-200 px-2 py-1 font-semibold uppercase text-slate-600">
                      {criticalityLabels[item.criticality]}
                    </span>
                    <span className="text-slate-500">{item.sourceType}</span>
                    <span className="text-slate-500">{statusLabels[item.status]}</span>
                  </div>
                  <h2 className="mt-2 text-lg font-semibold text-slate-950">
                    {item.summary}
                  </h2>
                  <p className="mt-1 text-xs text-slate-500">
                    Aberta em {itemDate(item.createdAt)}
                    {item.assigneeName ? ` · responsável ${item.assigneeName}` : ""}
                  </p>
                </div>
                <p className="shrink-0 text-xs text-slate-500">
                  {item.evidences.length} evidência{item.evidences.length === 1 ? "" : "s"}
                </p>
              </div>

              {item.evidences.length ? (
                <ul className="mt-4 divide-y divide-slate-100 border-y border-slate-100">
                  {item.evidences.map((evidence) => (
                    <li className="flex flex-wrap justify-between gap-2 py-2 text-sm" key={evidence.id}>
                      <span className="text-slate-800">{evidence.summary}</span>
                      <span className="text-xs text-slate-500">
                        {evidence.sourceType} · referência {evidence.sourceId}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}

              <div className="mt-4 flex flex-wrap items-center gap-2">
                {item.availableActions.includes("claim") ? (
                  <button className="bg-brand px-3 py-2 text-sm font-semibold text-white" onClick={() => action.mutate({ name: "claim", item })} type="button">
                    Assumir
                  </button>
                ) : null}
                {item.availableActions.includes("release") ? (
                  <button className="border border-brand px-3 py-2 text-sm font-semibold text-brand-dark" onClick={() => action.mutate({ name: "release", item })} type="button">
                    Liberar
                  </button>
                ) : null}
                {item.availableActions.includes("resolve") ? (
                  <button className="border border-emerald-700 px-3 py-2 text-sm font-semibold text-emerald-800" onClick={() => action.mutate({ name: "resolve", item })} type="button">
                    Resolver
                  </button>
                ) : null}
                {item.availableActions.includes("dismiss") ? (
                  <details className="text-sm">
                    <summary className="cursor-pointer border border-slate-300 px-3 py-2">Descartar</summary>
                    <form className="mt-2 flex flex-wrap gap-2" onSubmit={(event) => { event.preventDefault(); action.mutate({ name: "dismiss", item, reason: reasons[item.id] }); }}>
                      <input aria-label="Justificativa do descarte" className="border border-slate-300 px-3 py-2" maxLength={500} onChange={(event) => setReasons((current) => ({ ...current, [item.id]: event.target.value }))} required value={reasons[item.id] ?? ""} />
                      <button className="bg-slate-800 px-3 py-2 text-sm font-semibold text-white" disabled={action.isPending} type="submit">Confirmar descarte</button>
                    </form>
                  </details>
                ) : null}
                {item.availableActions.includes("reassign") ? (
                  <details className="text-sm">
                    <summary className="cursor-pointer border border-slate-300 px-3 py-2">Reatribuir</summary>
                    <form className="mt-2 flex flex-wrap gap-2" onSubmit={(event) => { event.preventDefault(); const assigneeId = assignees[item.id]; if (assigneeId) action.mutate({ name: "reassign", item, assigneeId, reason: reasons[item.id] }); }}>
                      <select aria-label="Novo responsável" className="border border-slate-300 px-3 py-2" onChange={(event) => setAssignees((current) => ({ ...current, [item.id]: Number(event.target.value) || undefined }))} required value={assignees[item.id] ?? ""}>
                        <option value="">Selecione</option>
                        {(reviewers.data ?? []).map((reviewer) => <option key={reviewer.id} value={reviewer.id}>{reviewer.nome}</option>)}
                      </select>
                      <input aria-label="Justificativa da reatribuição" className="border border-slate-300 px-3 py-2" maxLength={500} onChange={(event) => setReasons((current) => ({ ...current, [item.id]: event.target.value }))} required value={reasons[item.id] ?? ""} />
                      <button className="bg-slate-800 px-3 py-2 text-sm font-semibold text-white" disabled={action.isPending || reviewers.isLoading} type="submit">Confirmar reatribuição</button>
                    </form>
                  </details>
                ) : null}
                {item.availableActions.includes("reopen") ? (
                  <details className="text-sm">
                    <summary className="cursor-pointer border border-slate-300 px-3 py-2">Reabrir</summary>
                    <form className="mt-2 flex flex-wrap gap-2" onSubmit={(event) => { event.preventDefault(); action.mutate({ name: "reopen", item, reason: reasons[item.id] }); }}>
                      <input aria-label="Justificativa da reabertura" className="border border-slate-300 px-3 py-2" maxLength={500} onChange={(event) => setReasons((current) => ({ ...current, [item.id]: event.target.value }))} required value={reasons[item.id] ?? ""} />
                      <button className="bg-slate-800 px-3 py-2 text-sm font-semibold text-white" disabled={action.isPending} type="submit">Confirmar reabertura</button>
                    </form>
                  </details>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
