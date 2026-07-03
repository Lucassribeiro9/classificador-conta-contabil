import { Link, Outlet, useParams } from "react-router-dom";

import { ROUTES } from "../routes/paths";

export function AppShell() {
  const { empresaId } = useParams();
  const companyLabel = empresaId
    ? `Empresa selecionada: ${empresaId}`
    : "Empresa selecionada: nenhuma";

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-sm font-medium text-brand-dark">
              Classificador contabil
            </p>
            <p className="text-xs text-slate-500">{companyLabel}</p>
          </div>
          <nav aria-label="Navegacao principal" className="flex gap-4 text-sm">
            <Link to={ROUTES.empresas}>Empresas</Link>
            {empresaId ? (
              <Link to={ROUTES.empresa.operacao(empresaId)}>Operacao</Link>
            ) : null}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-6">
        <Outlet />
      </main>
    </div>
  );
}
