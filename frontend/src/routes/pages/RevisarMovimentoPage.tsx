import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { useAuth } from "../../app/auth";
import {
  RevisarMovimentoAccessDeniedError,
  RevisarMovimentoSessionExpiredError,
  revisarMovimentoClient,
} from "../../lib/api/revisarMovimentoClient";
import type {
  ContaContabilResumo,
  MovimentoRevisao,
  RevisaoMovimentoRequest,
} from "../../lib/api/revisarMovimentoClient";
import { PageState, operationalMessages } from "../../ui/operationalMessages";
import { ROUTES } from "../paths";

function formatConfidence(value: number | null) {
  if (value === null) return "Sem confianca calculada";
  return `${Math.round(value * 100)}% de confianca`;
}

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

function contaLocal(codigo: number, origem: string): ContaContabilResumo {
  return {
    id: codigo,
    codigo,
    classificacao: String(codigo),
    nome: origem,
    tipo: "local",
    isActive: true,
    isFinancialOrigin: false,
  };
}

function contasVinculadas(movimento: MovimentoRevisao): ContaContabilResumo[] {
  const contas = new Map<number, ContaContabilResumo>();
  const candidates = [
    [movimento.contrapartidaSugerida, "Conta sugerida"],
    [movimento.contrapartidaInformada, "Conta informada"],
    [movimento.contrapartidaFinal, "Conta final"],
  ] as const;

  candidates.forEach(([codigo, origem]) => {
    if (codigo !== null) {
      contas.set(codigo, contaLocal(codigo, origem));
    }
  });

  return Array.from(contas.values());
}

function isContaVinculada(
  conta: ContaContabilResumo | null,
  vinculadas: ContaContabilResumo[],
) {
  return Boolean(conta && vinculadas.some((item) => item.codigo === conta.codigo));
}

export function RevisarMovimentoPage() {
  const { empresaId, movimentoId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { session, setSession } = useAuth();
  const accessToken = session?.accessToken ?? "";
  const loteId = searchParams.get("loteId") ?? "";
  const [query, setQuery] = useState("");
  const [resultados, setResultados] = useState<ContaContabilResumo[]>([]);
  const [selectedConta, setSelectedConta] = useState<ContaContabilResumo | null>(
    null,
  );
  const [message, setMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [motivoRejeicao, setMotivoRejeicao] = useState("");

  const movimento = useQuery({
    queryKey: ["empresas", empresaId, "lotes", loteId, "movimentos", movimentoId],
    queryFn: () =>
      revisarMovimentoClient.getMovimento(
        accessToken,
        empresaId ?? "",
        loteId,
        movimentoId ?? "",
      ),
    enabled: Boolean(accessToken && empresaId && loteId && movimentoId),
  });

  const vinculadas = useMemo(() => {
    return movimento.data ? contasVinculadas(movimento.data) : [];
  }, [movimento.data]);

  const searchMutation = useMutation({
    mutationFn: (searchText: string) =>
      revisarMovimentoClient.searchContas(accessToken, searchText),
    onSuccess: (contas) => {
      setResultados(contas);
      setMessage(contas.length ? null : "Nenhuma conta encontrada.");
    },
    onError: () => {
      setMessage("Nao foi possivel buscar no plano de contas.");
    },
  });

  const reviewMutation = useMutation({
    mutationFn: (request: RevisaoMovimentoRequest) =>
      revisarMovimentoClient.reviewMovimento(
        accessToken,
        empresaId ?? "",
        loteId,
        movimentoId ?? "",
        request,
      ),
    onSuccess: (result, request) => {
      const labels = {
        approve: "Movimento aprovado.",
        correct: "Movimento corrigido.",
        reject: "Movimento rejeitado.",
      };

      setSuccessMessage(labels[request.action]);
      setMessage(null);
      queryClient.setQueryData(
        ["empresas", empresaId, "lotes", loteId, "movimentos", movimentoId],
        result,
      );
    },
    onError: () => {
      setMessage("Nao foi possivel salvar a revisao.");
    },
  });

  useEffect(() => {
    if (movimento.error instanceof RevisarMovimentoSessionExpiredError) {
      setSession(null);
      navigate(ROUTES.login, {
        replace: true,
        state: { reason: "Sessao expirada" },
      });
    }
  }, [movimento.error, navigate, setSession]);

  useEffect(() => {
    if (movimento.data?.contrapartidaSugerida) {
      setSelectedConta(
        contaLocal(movimento.data.contrapartidaSugerida, "Conta sugerida"),
      );
    }
  }, [movimento.data]);

  if (!loteId) {
    return (
      <PageState
        message={{
          title: "Lote nao informado",
          description: "Abra a revisao pela lista do lote.",
        }}
      />
    );
  }

  if (movimento.isLoading) {
    return <PageState message={operationalMessages.loading.movimento} />;
  }

  if (movimento.error instanceof RevisarMovimentoAccessDeniedError) {
    return <PageState message={operationalMessages.accessDenied.movimento} />;
  }

  if (movimento.isError || !movimento.data) {
    return <PageState message={operationalMessages.error.movimento} />;
  }

  const isGlobalNaoVinculada = !isContaVinculada(selectedConta, vinculadas);
  const canCorrect = Boolean(selectedConta);
  const canApprove = movimento.data.contrapartidaSugerida !== null;

  function searchPlanoCompleto() {
    const trimmed = query.trim();
    if (!trimmed) {
      setMessage("Informe codigo ou nome para buscar.");
      return;
    }

    searchMutation.mutate(trimmed);
  }

  function approveSugestao() {
    if (!movimento.data?.contrapartidaSugerida) return;
    reviewMutation.mutate({
      action: "approve",
      contaFinal: movimento.data.contrapartidaSugerida,
    });
  }

  function correctSelected() {
    if (!selectedConta) return;
    reviewMutation.mutate({
      action: "correct",
      contaFinal: selectedConta.codigo,
    });
  }

  function rejectMovimento() {
    void motivoRejeicao;
    reviewMutation.mutate({ action: "reject" });
  }

  function selectConta(conta: ContaContabilResumo) {
    setSelectedConta(conta);
    setSuccessMessage(null);
  }

  return (
    <section className="space-y-4">
      <div className="border-l-4 border-brand bg-white px-5 py-4 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-dark">
          Movimento {movimentoId} · Lote {loteId}
        </p>
        <h1 className="mt-1 text-2xl font-semibold text-slate-950">
          Revisar Movimento
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          Confirme a sugestao de ML ou escolha uma contrapartida antes de salvar
          a decisao humana.
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
      {successMessage ? (
        <p
          className="border-l-4 border-brand bg-teal-50 px-4 py-3 text-sm text-brand-dark"
          role="status"
        >
          {successMessage}
        </p>
      ) : null}
      {isGlobalNaoVinculada ? (
        <p
          className="border-l-4 border-amber-400 bg-amber-50 px-4 py-3 text-sm text-amber-950"
          role="alert"
        >
          O vinculo desta conta sera criado pelo backend ao salvar a revisao.
        </p>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="border border-slate-200 bg-white p-4 shadow-sm">
          <div className="grid gap-3 sm:grid-cols-4">
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500">
                Data
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-950">
                {movimento.data.data}
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500">
                Valor
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-950">
                {movimento.data.valorAbsoluto}
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500">
                Direcao
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-950">
                {movimento.data.direcao}
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500">
                Status
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-950">
                {formatStatus(movimento.data.status)}
              </p>
            </div>
          </div>

          <div className="mt-5 border-t border-slate-100 pt-4">
            <p className="text-xs font-semibold uppercase text-slate-500">
              Historico
            </p>
            <p className="mt-1 text-base font-semibold text-slate-950">
              {movimento.data.historicoNormalizado}
            </p>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <div className="border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs font-semibold uppercase text-slate-500">
                Conta financeira
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-950">
                {movimento.data.contaFinanceira}
              </p>
            </div>
            <div className="border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs font-semibold uppercase text-slate-500">
                Sugestao
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-950">
                {movimento.data.contrapartidaSugerida ?? "Sem sugestao"}
              </p>
              <p className="mt-1 text-xs font-semibold text-brand-dark">
                {formatConfidence(movimento.data.confidenceSugerida)}
              </p>
            </div>
            <div className="border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs font-semibold uppercase text-slate-500">
                Selecionada
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-950">
                {selectedConta
                  ? `${selectedConta.codigo} · ${selectedConta.nome}`
                  : "Nenhuma conta"}
              </p>
            </div>
          </div>

          {movimento.data.mensagensValidacao.length ? (
            <div className="mt-4 border-l-4 border-amber-400 bg-amber-50 px-4 py-3">
              {movimento.data.mensagensValidacao.map((warning) => (
                <p className="text-sm text-amber-950" key={warning}>
                  {warning}
                </p>
              ))}
            </div>
          ) : null}
        </div>

        <div className="border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-base font-semibold text-slate-950">Decisao</h2>
          <div className="mt-3 space-y-2">
            <button
              className="w-full bg-brand px-3 py-2 text-sm font-semibold text-white transition hover:bg-brand-dark disabled:cursor-not-allowed disabled:bg-slate-400"
              disabled={!canApprove || reviewMutation.isPending}
              onClick={approveSugestao}
              type="button"
            >
              Aprovar sugestao
            </button>
            <button
              className="w-full border border-brand px-3 py-2 text-sm font-semibold text-brand-dark transition hover:bg-teal-50 disabled:cursor-not-allowed disabled:border-slate-300 disabled:text-slate-400"
              disabled={!canCorrect || reviewMutation.isPending}
              onClick={correctSelected}
              type="button"
            >
              Corrigir com conta selecionada
            </button>
            <label className="block text-sm font-semibold text-slate-700">
              Motivo de rejeicao
              <textarea
                className="mt-1 min-h-20 w-full border border-slate-300 px-3 py-2 text-sm text-slate-950 outline-none focus:border-brand"
                onChange={(event) => setMotivoRejeicao(event.target.value)}
                value={motivoRejeicao}
              />
            </label>
            <button
              className="w-full border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
              disabled={reviewMutation.isPending}
              onClick={rejectMovimento}
              type="button"
            >
              Rejeitar movimento
            </button>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-base font-semibold text-slate-950">
            Contas vinculadas
          </h2>
          <div className="mt-3 divide-y divide-slate-100">
            {vinculadas.length ? (
              vinculadas.map((conta) => (
                <div
                  className="flex items-center justify-between gap-3 py-3"
                  key={conta.codigo}
                >
                  <div>
                    <p className="text-sm font-semibold text-slate-950">
                      {conta.codigo} · {conta.nome}
                    </p>
                    <p className="text-xs text-slate-500">{conta.classificacao}</p>
                  </div>
                  <button
                    className="border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                    onClick={() => selectConta(conta)}
                    type="button"
                  >
                    Usar {conta.codigo}
                  </button>
                </div>
              ))
            ) : (
              <p className="py-3 text-sm text-slate-600">
                Nenhuma conta vinculada ao movimento.
              </p>
            )}
          </div>
        </div>

        <div className="border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-base font-semibold text-slate-950">
            Plano completo
          </h2>
          <div className="mt-3 flex gap-2">
            <label className="min-w-0 flex-1 text-sm font-semibold text-slate-700">
              Buscar conta
              <input
                className="mt-1 w-full border border-slate-300 px-3 py-2 text-sm text-slate-950 outline-none focus:border-brand"
                onChange={(event) => setQuery(event.target.value)}
                value={query}
              />
            </label>
            <button
              className="mt-6 border border-brand px-3 py-2 text-sm font-semibold text-brand-dark transition hover:bg-teal-50 disabled:cursor-not-allowed disabled:text-slate-400"
              disabled={searchMutation.isPending}
              onClick={searchPlanoCompleto}
              type="button"
            >
              Buscar no plano completo
            </button>
          </div>

          <div className="mt-3 divide-y divide-slate-100">
            {resultados.map((conta) => (
              <div
                className="flex items-center justify-between gap-3 py-3"
                key={conta.id}
              >
                <div>
                  <p className="text-sm font-semibold text-slate-950">
                    {conta.codigo} · {conta.nome}
                  </p>
                  <p className="text-xs text-slate-500">
                    {conta.classificacao} · {conta.tipo}
                  </p>
                </div>
                <button
                  className="border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                  onClick={() => selectConta(conta)}
                  type="button"
                >
                  Usar {conta.codigo}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>
    </section>
  );
}
