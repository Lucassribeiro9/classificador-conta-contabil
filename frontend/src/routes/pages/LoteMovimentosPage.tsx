import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../../app/auth";
import {
  LoteMovimentosAccessDeniedError,
  LoteMovimentosSessionExpiredError,
  loteMovimentosClient,
} from "../../lib/api/loteMovimentosClient";
import type {
  MovimentoOperacional,
  ReviewMovimentoRequest,
  StatusMovimentoFiltro,
} from "../../lib/api/loteMovimentosClient";
import { PageState, operationalMessages } from "../../ui/operationalMessages";
import { ROUTES } from "../paths";

const STATUS_FILTERS: Array<{ value: StatusMovimentoFiltro; label: string }> = [
  { value: "todos", label: "Todos" },
  { value: "pendente", label: "Pendentes" },
  { value: "pre_classificado", label: "Pre-classificados" },
  { value: "revisao", label: "Revisao" },
  { value: "aprovado", label: "Aprovados" },
  { value: "rejeitado", label: "Rejeitados" },
];

function formatStatus(status: string) {
  const labels: Record<string, string> = {
    aprovado: "Aprovado",
    pendente: "Pendente",
    pre_classificado: "Pre-classificado",
    rejeitado: "Rejeitado",
    revisao: "Revisao",
    sugerido: "Sugerido",
  };

  return labels[status] ?? status.split("_").join(" ");
}

function contaParaAprovar(movimento: MovimentoOperacional) {
  return movimento.contrapartidaSugerida ?? movimento.contrapartidaInformada;
}

function selectedLabel(count: number) {
  return `${count} ${count === 1 ? "selecionado" : "selecionados"}`;
}

export function LoteMovimentosPage() {
  const { empresaId, loteId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { session, setSession } = useAuth();
  const accessToken = session?.accessToken ?? "";
  const [status, setStatus] = useState<StatusMovimentoFiltro>("todos");
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [message, setMessage] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const movimentos = useQuery({
    queryKey: ["empresas", empresaId, "lotes", loteId, "movimentos", status],
    queryFn: () =>
      loteMovimentosClient.listMovimentos(
        accessToken,
        empresaId ?? "",
        loteId ?? "",
        status,
      ),
    enabled: Boolean(accessToken && empresaId && loteId),
  });

  const selectedMovimentos = useMemo(() => {
    return (
      movimentos.data?.items.filter((movimento) =>
        selectedIds.has(movimento.id),
      ) ?? []
    );
  }, [movimentos.data?.items, selectedIds]);

  const reviewMutation = useMutation({
    mutationFn: (requests: ReviewMovimentoRequest[]) =>
      loteMovimentosClient.reviewMovimentos(
        accessToken,
        empresaId ?? "",
        loteId ?? "",
        requests,
      ),
    onSuccess: (result) => {
      if (result.failureCount > 0) {
        setMessage(`${result.failureCount} falha ao atualizar selecionados.`);
      } else {
        setStatusMessage(`${result.successCount} movimento atualizado.`);
        setMessage(null);
      }
      setSelectedIds(new Set());
      void queryClient.invalidateQueries({
        queryKey: ["empresas", empresaId, "lotes", loteId, "movimentos"],
      });
    },
    onError: () => {
      setMessage("Nao foi possivel atualizar os movimentos selecionados.");
    },
  });

  const classifyMutation = useMutation({
    mutationFn: () =>
      loteMovimentosClient.classificarPendentes(accessToken, empresaId ?? ""),
    onSuccess: (result) => {
      setStatusMessage(
        `${result.quantidadeProcessada} pendentes classificados. ${result.totalSugerido} sugeridos, ${result.totalRevisao} para revisao.`,
      );
      setMessage(null);
      void queryClient.invalidateQueries({
        queryKey: ["empresas", empresaId, "lotes", loteId, "movimentos"],
      });
    },
    onError: () => {
      setMessage("Nao foi possivel classificar pendentes da empresa.");
    },
  });

  useEffect(() => {
    if (movimentos.error instanceof LoteMovimentosSessionExpiredError) {
      setSession(null);
      navigate(ROUTES.login, {
        replace: true,
        state: { reason: "Sessao expirada" },
      });
    }
  }, [movimentos.error, navigate, setSession]);

  if (movimentos.isLoading) {
    return <PageState message={operationalMessages.loading.lote} />;
  }

  if (movimentos.error instanceof LoteMovimentosAccessDeniedError) {
    return <PageState message={operationalMessages.accessDenied.lote} />;
  }

  if (movimentos.isError) {
    return <PageState message={operationalMessages.error.lote} />;
  }

  const items = movimentos.data?.items ?? [];
  const allSelected =
    items.length > 0 && items.every((item) => selectedIds.has(item.id));
  const canApprove =
    selectedMovimentos.length > 0 &&
    selectedMovimentos.every((movimento) => contaParaAprovar(movimento));

  function toggleSelected(id: number) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function toggleAll() {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map((item) => item.id)));
    }
  }

  function approveSelected() {
    if (!canApprove) {
      setMessage("Aprovacao exige contrapartida sugerida ou informada.");
      return;
    }

    reviewMutation.mutate(
      selectedMovimentos.map((movimento) => ({
        movimentoId: movimento.id,
        action: "approve",
        contaFinal: contaParaAprovar(movimento) ?? undefined,
      })),
    );
  }

  function rejectSelected() {
    if (!selectedMovimentos.length) return;
    reviewMutation.mutate(
      selectedMovimentos.map((movimento) => ({
        movimentoId: movimento.id,
        action: "reject",
      })),
    );
  }

  function markReviewUnsupported() {
    setMessage("Envio para revisao aguarda contrato da API.");
  }

  return (
    <section className="space-y-4">
      <div className="border-l-4 border-brand bg-white px-5 py-4 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-dark">
          Lote {loteId}
        </p>
        <h1 className="mt-1 text-2xl font-semibold text-slate-950">
          Lote de Movimentos
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          Revise movimentos importados, filtre por status e execute decisoes em
          lote sem aprovar sugestoes automaticamente.
        </p>
      </div>

      {message ? (
        <p
          className="border-l-4 border-amber-400 bg-amber-50 px-4 py-3 text-sm text-amber-950"
          role="alert"
        >
          {message}
        </p>
      ) : null}
      {statusMessage ? (
        <p
          className="border-l-4 border-brand bg-teal-50 px-4 py-3 text-sm text-brand-dark"
          role="status"
        >
          {statusMessage}
        </p>
      ) : null}

      <section className="border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2" aria-label="Filtros de status">
            {STATUS_FILTERS.map((filter) => (
              <button
                className={
                  status === filter.value
                    ? "bg-brand px-3 py-2 text-sm font-semibold text-white"
                    : "border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                }
                key={filter.value}
                onClick={() => {
                  setStatus(filter.value);
                  setSelectedIds(new Set());
                }}
                type="button"
              >
                {filter.label}
              </button>
            ))}
          </div>
          <p className="text-sm font-semibold text-slate-700">
            {selectedLabel(selectedMovimentos.length)}
          </p>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <button
            className="bg-brand px-3 py-2 text-sm font-semibold text-white transition hover:bg-brand-dark disabled:cursor-not-allowed disabled:bg-slate-400"
            disabled={!selectedMovimentos.length || !canApprove}
            onClick={approveSelected}
            type="button"
          >
            Aprovar selecionados
          </button>
          <button
            className="border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
            disabled={!selectedMovimentos.length}
            onClick={rejectSelected}
            type="button"
          >
            Rejeitar selecionados
          </button>
          <button
            className="border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
            disabled={!selectedMovimentos.length}
            onClick={markReviewUnsupported}
            type="button"
          >
            Enviar para revisao
          </button>
          <button
            className="border border-brand px-3 py-2 text-sm font-semibold text-brand-dark transition hover:bg-teal-50"
            onClick={() => classifyMutation.mutate()}
            type="button"
          >
            Classificar pendentes da empresa
          </button>
        </div>
        <p className="mt-3 text-sm text-slate-600">
          Classificar pendentes atua em todos os pendentes da empresa.
        </p>
      </section>

      <section className="overflow-x-auto border border-slate-200 bg-white shadow-sm">
        {items.length ? (
          <table className="min-w-full border-collapse text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="w-10 px-3 py-3">
                  <input
                    aria-label="Selecionar todos"
                    checked={allSelected}
                    onChange={toggleAll}
                    type="checkbox"
                  />
                </th>
                <th className="px-3 py-3">Data</th>
                <th className="px-3 py-3">Historico</th>
                <th className="px-3 py-3">Valor</th>
                <th className="px-3 py-3">Status</th>
                <th className="px-3 py-3">Contrapartida</th>
                <th className="px-3 py-3">Acao</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((movimento) => (
                <tr key={movimento.id}>
                  <td className="px-3 py-3">
                    <input
                      aria-label={`Selecionar movimento ${movimento.id}`}
                      checked={selectedIds.has(movimento.id)}
                      onChange={() => toggleSelected(movimento.id)}
                      type="checkbox"
                    />
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-slate-700">
                    {movimento.data}
                  </td>
                  <td className="min-w-[240px] px-3 py-3 text-slate-950">
                    <p className="font-medium">
                      {movimento.historicoNormalizado}
                    </p>
                    {movimento.mensagensValidacao.length ? (
                      <p className="mt-1 text-xs text-amber-700">
                        {movimento.mensagensValidacao.join(" ")}
                      </p>
                    ) : null}
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-slate-700">
                    {movimento.valorAbsoluto}
                  </td>
                  <td className="whitespace-nowrap px-3 py-3">
                    <span className="border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-700">
                      {formatStatus(movimento.status)}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-slate-700">
                    {contaParaAprovar(movimento) ?? "Sem conta"}
                  </td>
                  <td className="whitespace-nowrap px-3 py-3">
                    <Link
                      className="text-sm font-semibold text-brand-dark underline-offset-4 hover:underline"
                      to={ROUTES.empresa.revisarMovimento(
                        empresaId ?? "",
                        String(movimento.id),
                        loteId,
                      )}
                    >
                      Abrir revisao
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-6">
            <h2 className="text-lg font-semibold text-slate-950">
              {operationalMessages.empty.semMovimentosFiltro.title}
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              {operationalMessages.empty.semMovimentosFiltro.description}
            </p>
          </div>
        )}
      </section>
    </section>
  );
}
