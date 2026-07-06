import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../../app/auth";
import {
  ImportarMovimentosAccessDeniedError,
  ImportarMovimentosBlockedError,
  ImportarMovimentosNetworkError,
  ImportarMovimentosSessionExpiredError,
  importarMovimentosClient,
} from "../../lib/api/importarMovimentosClient";
import type { ImportarMovimentosResumo } from "../../lib/api/importarMovimentosClient";
import { ROUTES } from "../paths";

function statusTitle(resumo: ImportarMovimentosResumo) {
  if (resumo.status === "completed_with_warnings" || resumo.warnings.length) {
    return "Importacao com warnings";
  }

  return "Importacao concluida";
}

function SummaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-xl font-semibold text-slate-950">{value}</p>
      <p className="mt-1 text-xs font-medium uppercase text-slate-500">
        {label}
      </p>
    </div>
  );
}

function ImportSummary({
  empresaId,
  onReset,
  resumo,
}: {
  empresaId: string;
  onReset: () => void;
  resumo: ImportarMovimentosResumo;
}) {
  return (
    <section className="border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-brand-dark">
        Lote {resumo.loteId}
      </p>
      <h2 className="mt-1 text-lg font-semibold text-slate-950">
        {statusTitle(resumo)}
      </h2>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <SummaryMetric
          label="Linhas"
          value={`${resumo.totalLinhas} linhas lidas`}
        />
        <SummaryMetric
          label="Importadas"
          value={`${resumo.totalImportadas} movimentos importados`}
        />
        <SummaryMetric
          label="Bloqueios"
          value={`${resumo.totalInvalidas} bloqueios`}
        />
      </div>

      {resumo.warnings.length ? (
        <div className="mt-4 border border-amber-200 bg-amber-50 px-4 py-3">
          <p className="text-sm font-semibold text-amber-950">Warnings</p>
          <ul className="mt-2 grid gap-1 text-sm text-amber-900">
            {resumo.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-5 flex flex-wrap gap-2">
        <Link
          className="bg-brand px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
          to={ROUTES.empresa.loteMovimentos(empresaId, String(resumo.loteId))}
        >
          Abrir lote
        </Link>
        <button
          className="border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
          onClick={onReset}
          type="button"
        >
          Importar outro arquivo
        </button>
      </div>
    </section>
  );
}

export function ImportarMovimentosPage() {
  const { empresaId } = useParams();
  const navigate = useNavigate();
  const { session, setSession } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [resumo, setResumo] = useState<ImportarMovimentosResumo | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setResumo(null);

    if (!file || !file.name.toLowerCase().endsWith(".xlsx")) {
      setMessage("Selecione um arquivo .xlsx.");
      return;
    }

    if (!session?.accessToken || !empresaId) {
      setMessage("Sessao indisponivel. Entre novamente para continuar.");
      return;
    }

    setIsSubmitting(true);

    try {
      const result = await importarMovimentosClient.importar(
        session.accessToken,
        empresaId,
        file,
      );
      setResumo(result);
    } catch (error) {
      if (error instanceof ImportarMovimentosSessionExpiredError) {
        setSession(null);
        navigate(ROUTES.login, {
          replace: true,
          state: { reason: "Sessao expirada" },
        });
      } else if (error instanceof ImportarMovimentosAccessDeniedError) {
        setMessage("Seu usuario nao tem permissao para importar nesta empresa.");
      } else if (error instanceof ImportarMovimentosBlockedError) {
        setMessage(error.message);
      } else if (
        error instanceof ImportarMovimentosNetworkError ||
        error instanceof TypeError
      ) {
        setMessage("Nao foi possivel conectar a API interna.");
      } else {
        setMessage("Importacao bloqueada pela API.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function resetImport() {
    setFile(null);
    setMessage(null);
    setResumo(null);
  }

  const currentEmpresaId = empresaId ?? "";

  return (
    <section className="space-y-4">
      <div className="border-l-4 border-brand bg-white px-5 py-4 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-dark">
          Movimentos operacionais
        </p>
        <h1 className="mt-1 text-2xl font-semibold text-slate-950">
          Importar Movimentos
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          Envie a planilha `.xlsx` da empresa selecionada e confira o resumo do
          lote antes da proxima acao.
        </p>
      </div>

      <form
        className="border border-slate-200 bg-white p-5 shadow-sm"
        onSubmit={handleSubmit}
      >
        {message ? (
          <p
            className="mb-4 border-l-4 border-amber-400 bg-amber-50 px-4 py-3 text-sm text-amber-950"
            role="alert"
          >
            {message}
          </p>
        ) : null}

        <label className="block text-sm font-semibold text-slate-800">
          Arquivo .xlsx
          <input
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            className="mt-2 block w-full border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 file:mr-4 file:border-0 file:bg-brand file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            type="file"
          />
        </label>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            className="bg-brand px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-400"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Importando..." : "Importar arquivo"}
          </button>
          {file ? (
            <span className="text-sm text-slate-600">{file.name}</span>
          ) : (
            <span className="text-sm text-slate-500">
              Nenhum arquivo selecionado
            </span>
          )}
        </div>
      </form>

      {resumo ? (
        <ImportSummary
          empresaId={currentEmpresaId}
          onReset={resetImport}
          resumo={resumo}
        />
      ) : null}
    </section>
  );
}
