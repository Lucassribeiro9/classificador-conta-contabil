import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { useAuth } from "../../app/auth";
import {
  RazaoContasAccessDeniedError,
  RazaoContasSessionExpiredError,
  razaoContasClient,
} from "../../lib/api/razaoContasClient";
import type {
  LancamentoRazaoResumo,
  LoteRazaoResumo,
  PaginatedResult,
} from "../../lib/api/razaoContasClient";
import { PageState, operationalMessages } from "../../ui/operationalMessages";

function formatStatus(status: string) {
  const labels: Record<string, string> = {
    completed: "Concluido",
    completed_with_warnings: "Com warnings",
    failed: "Falhou",
    processing: "Processando",
  };

  return labels[status] ?? status.split("_").join(" ");
}

function filterLancamentos(
  lancamentos: LancamentoRazaoResumo[],
  query: string,
) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return lancamentos;

  return lancamentos.filter((lancamento) => {
    const searchable = [
      lancamento.numeroLancamento,
      lancamento.historicoNormalizado,
      lancamento.contaOrigem,
      lancamento.contaContrapartida,
      lancamento.contaDebito,
      lancamento.contaCredito,
    ]
      .join(" ")
      .toLowerCase();

    return searchable.includes(normalized);
  });
}

function LotesPanel({
  lotes,
  selectedLoteId,
  onSelect,
}: {
  lotes: LoteRazaoResumo[];
  selectedLoteId: string;
  onSelect: (loteId: string) => void;
}) {
  return (
    <section className="border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-base font-semibold text-slate-950">
        Lotes importados
      </h2>
      <div className="mt-3 divide-y divide-slate-100">
        {lotes.map((lote) => {
          const selected = selectedLoteId === String(lote.id);
          return (
            <article className="py-3" key={lote.id}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-950">
                    {lote.originalFilename}
                  </p>
                  <p className="mt-1 text-xs text-slate-600">
                    <span>{formatStatus(lote.status)}</span>
                    <span> · </span>
                    <span>{lote.totalImportadas} importadas</span>
                    <span> · </span>
                    <span>{lote.totalInvalidas} invalidas</span>
                  </p>
                </div>
                <button
                  className={
                    selected
                      ? "bg-brand px-3 py-2 text-sm font-semibold text-white"
                      : "border border-brand px-3 py-2 text-sm font-semibold text-brand-dark hover:bg-teal-50"
                  }
                  onClick={() => onSelect(String(lote.id))}
                  type="button"
                >
                  Abrir lote {lote.id}
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function PaginationSummary<T>({
  data,
  label,
}: {
  data?: PaginatedResult<T>;
  label: string;
}) {
  if (!data) return null;

  return (
    <p className="text-sm text-slate-600">
      {data.total} {label} · pagina {data.page}
      {data.hasNext ? " · ha mais resultados" : ""}
    </p>
  );
}

function LancamentosPanel({
  data,
  query,
  onQueryChange,
}: {
  data?: PaginatedResult<LancamentoRazaoResumo>;
  query: string;
  onQueryChange: (query: string) => void;
}) {
  const filtered = filterLancamentos(data?.items ?? [], query);

  return (
    <section className="border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-950">
            Lancamentos normalizados
          </h2>
          <PaginationSummary data={data} label="lancamentos" />
        </div>
        <label className="text-sm font-semibold text-slate-700">
          Buscar por codigo ou historico
          <input
            className="mt-1 w-full min-w-64 border border-slate-300 px-3 py-2 text-sm text-slate-950 outline-none focus:border-brand"
            onChange={(event) => onQueryChange(event.target.value)}
            value={query}
          />
        </label>
      </div>

      <div className="mt-4 overflow-x-auto">
        {filtered.length ? (
          <table className="min-w-full border-collapse text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-3">Data</th>
                <th className="px-3 py-3">Lancamento</th>
                <th className="px-3 py-3">Historico</th>
                <th className="px-3 py-3">Origem</th>
                <th className="px-3 py-3">Contrapartida</th>
                <th className="px-3 py-3">Valor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((lancamento) => (
                <tr key={lancamento.id}>
                  <td className="whitespace-nowrap px-3 py-3 text-slate-700">
                    {lancamento.data}
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-slate-700">
                    {lancamento.numeroLancamento}
                  </td>
                  <td className="min-w-60 px-3 py-3 font-medium text-slate-950">
                    {lancamento.historicoNormalizado}
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-slate-700">
                    {lancamento.contaOrigem}
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-slate-700">
                    {lancamento.contaContrapartida}
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-slate-700">
                    {lancamento.valor}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="border border-slate-200 bg-slate-50 p-4">
            <h3 className="text-sm font-semibold text-slate-950">
              {operationalMessages.empty.semLancamentosFiltro.title}
            </h3>
            <p className="mt-1 text-sm text-slate-600">
              {operationalMessages.empty.semLancamentosFiltro.description}
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

function ContasVinculadasPanel() {
  return (
    <section
      aria-label="Contas vinculadas"
      className="border border-slate-200 bg-white p-4 shadow-sm"
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-brand-dark">
        Contas vinculadas
      </p>
      <h2 className="mt-1 text-base font-semibold text-slate-950">
        Contrato ainda nao disponivel
      </h2>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        A API ainda nao expoe busca paginada de contas vinculadas por empresa.
      </p>
    </section>
  );
}

export function RazaoContasPage() {
  const { empresaId } = useParams();
  const { session, setSession } = useAuth();
  const accessToken = session?.accessToken ?? "";
  const [lotesPage] = useState(1);
  const [lancamentosPage] = useState(1);
  const [selectedLoteId, setSelectedLoteId] = useState("");
  const [query, setQuery] = useState("");

  const lotes = useQuery({
    queryKey: ["empresas", empresaId, "razao", "lotes", lotesPage],
    queryFn: () =>
      razaoContasClient.listLotes(accessToken, empresaId ?? "", lotesPage),
    enabled: Boolean(accessToken && empresaId),
  });

  const selectedLoteFromData = useMemo(() => {
    return selectedLoteId || String(lotes.data?.items[0]?.id ?? "");
  }, [lotes.data?.items, selectedLoteId]);

  const lancamentos = useQuery({
    queryKey: [
      "empresas",
      empresaId,
      "razao",
      "lotes",
      selectedLoteFromData,
      "lancamentos",
      lancamentosPage,
    ],
    queryFn: () =>
      razaoContasClient.listLancamentos(
        accessToken,
        empresaId ?? "",
        selectedLoteFromData,
        lancamentosPage,
      ),
    enabled: Boolean(accessToken && empresaId && selectedLoteFromData),
  });

  useEffect(() => {
    if (
      lotes.error instanceof RazaoContasSessionExpiredError ||
      lancamentos.error instanceof RazaoContasSessionExpiredError
    ) {
      setSession(null);
    }
  }, [lotes.error, lancamentos.error, setSession]);

  if (lotes.isLoading) {
    return <PageState message={operationalMessages.loading.razao} />;
  }

  if (lotes.error instanceof RazaoContasAccessDeniedError) {
    return <PageState message={operationalMessages.accessDenied.razao} />;
  }

  if (lotes.isError) {
    return <PageState message={operationalMessages.error.razao} />;
  }

  if (!lotes.data?.items.length) {
    return <PageState message={operationalMessages.empty.semRazao} />;
  }

  return (
    <section className="space-y-4">
      <div className="border-l-4 border-brand bg-white px-5 py-4 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-dark">
          Empresa {empresaId}
        </p>
        <h1 className="mt-1 text-2xl font-semibold text-slate-950">
          Razao e Contas Vinculadas
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          Consulte lotes importados e lancamentos normalizados usados como base
          contabil do modelo.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="space-y-4">
          <LotesPanel
            lotes={lotes.data.items}
            onSelect={(loteId) => {
              setSelectedLoteId(loteId);
              setQuery("");
            }}
            selectedLoteId={selectedLoteFromData}
          />
          <ContasVinculadasPanel />
        </div>

        {lancamentos.error instanceof RazaoContasAccessDeniedError ? (
          <PageState message={operationalMessages.accessDenied.lancamentos} />
        ) : lancamentos.isError ? (
          <PageState message={operationalMessages.error.lancamentos} />
        ) : (
          <LancamentosPanel
            data={lancamentos.data}
            onQueryChange={setQuery}
            query={query}
          />
        )}
      </div>
    </section>
  );
}
