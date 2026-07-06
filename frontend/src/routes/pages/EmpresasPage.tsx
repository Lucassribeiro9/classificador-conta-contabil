import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../app/auth";
import {
  EmpresasAccessDeniedError,
  EmpresasSessionExpiredError,
  empresasClient,
} from "../../lib/api/empresasClient";
import type { EmpresaResumo } from "../../lib/api/empresasClient";
import { ROUTES } from "../paths";

function EmpresaCard({ empresa }: { empresa: EmpresaResumo }) {
  const navigate = useNavigate();

  return (
    <article className="border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-brand">
            Empresa autorizada
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">
            {empresa.nome}
          </h2>
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-600">
            {empresa.documento ? (
              <span className="border border-slate-200 px-2 py-1">
                {empresa.documento}
              </span>
            ) : null}
            {empresa.papel ? (
              <span className="border border-teal-100 bg-teal-50 px-2 py-1 text-brand-dark">
                {empresa.papel}
              </span>
            ) : null}
          </div>
        </div>
        <button
          type="button"
          className="border border-brand bg-brand px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
          onClick={() => navigate(ROUTES.empresa.operacao(String(empresa.id)))}
        >
          Abrir {empresa.nome}
        </button>
      </div>
    </article>
  );
}

function PageState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <section className="border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-base font-semibold text-slate-950">{title}</h2>
      <p className="mt-2 max-w-2xl text-sm text-slate-600">{description}</p>
    </section>
  );
}

export function EmpresasPage() {
  const { session, setSession } = useAuth();
  const accessToken = session?.accessToken ?? "";

  const empresas = useQuery({
    queryKey: ["empresas", "autorizadas"],
    queryFn: () => empresasClient.list(accessToken),
    enabled: Boolean(accessToken),
  });

  useEffect(() => {
    if (empresas.error instanceof EmpresasSessionExpiredError) {
      setSession(null);
    }
  }, [empresas.error, setSession]);

  if (empresas.isLoading) {
    return (
      <PageState
        title="Carregando empresas"
        description="Buscando as empresas liberadas para o seu usuario."
      />
    );
  }

  if (empresas.error instanceof EmpresasAccessDeniedError) {
    return (
      <PageState
        title="Acesso negado"
        description="Seu usuario nao tem permissao para consultar empresas. Contate o administrador."
      />
    );
  }

  if (empresas.isError) {
    return (
      <PageState
        title="Nao foi possivel carregar empresas"
        description="Verifique a conexao com a API interna e tente novamente."
      />
    );
  }

  if (!empresas.data?.length) {
    return (
      <PageState
        title="Sem empresas vinculadas"
        description="Nenhuma empresa esta liberada para o seu usuario. Contate o administrador."
      />
    );
  }

  return (
    <section className="space-y-5">
      <div className="border-l-4 border-brand bg-white px-5 py-4 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-dark">
          Operacao interna
        </p>
        <h1 className="mt-1 text-2xl font-semibold text-slate-950">
          Escolha a empresa
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-600">
          Selecione conscientemente o cliente antes de importar, classificar ou
          revisar movimentos.
        </p>
      </div>

      <div className="grid gap-3">
        {empresas.data.map((empresa) => (
          <EmpresaCard key={empresa.id} empresa={empresa} />
        ))}
      </div>
    </section>
  );
}
