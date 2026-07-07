import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../../app/auth";
import {
  OperacaoEmpresaAccessDeniedError,
  OperacaoEmpresaSessionExpiredError,
  operacaoEmpresaClient,
} from "../../lib/api/operacaoEmpresaClient";
import type { OperacaoEmpresaHub } from "../../lib/api/operacaoEmpresaClient";
import { PageState, operationalMessages } from "../../ui/operationalMessages";
import { ROUTES } from "../paths";

type SummaryCardProps = {
  label: string;
  value: string;
  detail: string;
};

function formatStatus(status?: string) {
  if (!status) return "Sem status";

  const labels: Record<string, string> = {
    completed: "Concluido",
    completed_with_warnings: "Com warnings",
    dataset_insuficiente: "Dataset insuficiente",
    failed: "Falhou",
    modelo_pronto: "Modelo pronto",
    processing: "Processando",
    sem_razao: "Sem razao",
    treinavel_sem_modelo: "Treinavel sem modelo",
  };

  return labels[status] ?? status.split("_").join(" ");
}

function pluralize(count: number, singular: string, plural: string) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function SummaryCard({ label, value, detail }: SummaryCardProps) {
  return (
    <article className="border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-brand">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
      <p className="mt-1 text-sm text-slate-600">{detail}</p>
    </article>
  );
}

function Alert({ children }: { children: string }) {
  return (
    <p className="border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
      {children}
    </p>
  );
}

function OperationalAlerts({ hub }: { hub: OperacaoEmpresaHub }) {
  const alerts = [];

  if (hub.razao.totalLotes === 0 || hub.ml.status === "sem_razao") {
    alerts.push("Importe o razao antes de validar classificacao.");
  }

  if (!hub.ml.treinavel) {
    alerts.push("Base insuficiente para classificacao automatica.");
  }

  if (!alerts.length) return null;

  return (
    <div className="grid gap-2">
      {alerts.map((alert) => (
        <Alert key={alert}>{alert}</Alert>
      ))}
    </div>
  );
}

function QuickActions({ hub }: { hub: OperacaoEmpresaHub }) {
  const empresaId = String(hub.empresa.id);

  return (
    <section className="border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-base font-semibold text-slate-950">
        Atalhos operacionais
      </h2>
      <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <Link
          className="border border-brand px-3 py-2 text-center text-sm font-semibold text-brand-dark transition hover:bg-teal-50 focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
          to={ROUTES.empresa.importarMovimentos(empresaId)}
        >
          Importar movimentos
        </Link>
        {hub.movimentos.ultimoLoteId ? (
          <Link
            className="border border-brand px-3 py-2 text-center text-sm font-semibold text-brand-dark transition hover:bg-teal-50 focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
            to={ROUTES.empresa.loteMovimentos(
              empresaId,
              String(hub.movimentos.ultimoLoteId),
            )}
          >
            Abrir ultimo lote
          </Link>
        ) : (
          <span className="border border-slate-200 px-3 py-2 text-center text-sm font-semibold text-slate-400">
            Sem lote operacional
          </span>
        )}
        <Link
          className="border border-brand px-3 py-2 text-center text-sm font-semibold text-brand-dark transition hover:bg-teal-50 focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
          to={ROUTES.empresa.razaoContas(empresaId)}
        >
          Consultar razao
        </Link>
        <span className="border border-slate-200 px-3 py-2 text-center text-sm font-semibold text-slate-400">
          Classificar pendentes
        </span>
      </div>
    </section>
  );
}

function HubContent({ hub }: { hub: OperacaoEmpresaHub }) {
  return (
    <section className="space-y-5">
      <div className="border-l-4 border-brand bg-white px-5 py-4 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-dark">
          Empresa selecionada
        </p>
        <h1 className="mt-1 text-2xl font-semibold text-slate-950">
          {hub.empresa.nome}
        </h1>
        <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
          {hub.empresa.documento ? (
            <span className="border border-slate-200 px-2 py-1">
              {hub.empresa.documento}
            </span>
          ) : null}
          {hub.empresa.papel ? (
            <span className="border border-teal-100 bg-teal-50 px-2 py-1 text-brand-dark">
              {hub.empresa.papel}
            </span>
          ) : null}
        </div>
      </div>

      <OperationalAlerts hub={hub} />

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          label="Classificacao"
          value={formatStatus(hub.ml.status)}
          detail={`${hub.ml.datasetTotalLinhas} linhas de treino`}
        />
        <SummaryCard
          label="Razao importado"
          value={pluralize(hub.razao.totalLotes, "lote", "lotes")}
          detail={`${hub.razao.totalLinhas} lancamentos importados`}
        />
        <SummaryCard
          label="Contas vinculadas"
          value={
            hub.contasVinculadas === null
              ? "Nao informado pela API"
              : String(hub.contasVinculadas)
          }
          detail="Contrato dedicado ainda nao disponivel"
        />
        <SummaryCard
          label="Movimentos"
          value={pluralize(hub.movimentos.totalLinhas, "movimento", "movimentos")}
          detail={`${hub.movimentos.totalLotes} lotes operacionais`}
        />
      </div>

      <QuickActions hub={hub} />
    </section>
  );
}

export function OperacaoEmpresaPage() {
  const { empresaId } = useParams();
  const { session, setSession } = useAuth();
  const accessToken = session?.accessToken ?? "";

  const hub = useQuery({
    queryKey: ["empresas", empresaId, "hub-operacional"],
    queryFn: () => operacaoEmpresaClient.getHub(accessToken, empresaId ?? ""),
    enabled: Boolean(accessToken && empresaId),
  });

  useEffect(() => {
    if (hub.error instanceof OperacaoEmpresaSessionExpiredError) {
      setSession(null);
    }
  }, [hub.error, setSession]);

  if (hub.isLoading) {
    return <PageState message={operationalMessages.loading.operacao} />;
  }

  if (hub.error instanceof OperacaoEmpresaAccessDeniedError) {
    return <PageState message={operationalMessages.accessDenied.empresa} />;
  }

  if (hub.isError) {
    return <PageState message={operationalMessages.error.operacao} />;
  }

  if (!hub.data) {
    return <PageState message={operationalMessages.empty.empresaNaoEncontrada} />;
  }

  return <HubContent hub={hub.data} />;
}
