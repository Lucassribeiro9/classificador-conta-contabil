import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./AppShell";
import { ProtectedRoute } from "./ProtectedRoute";
import { ROUTES } from "../routes/paths";
import { EmpresasPage } from "../routes/pages/EmpresasPage";
import { ImportarMovimentosPage } from "../routes/pages/ImportarMovimentosPage";
import { LoginPage } from "../routes/pages/LoginPage";
import { LoteMovimentosPage } from "../routes/pages/LoteMovimentosPage";
import { OperacaoEmpresaPage } from "../routes/pages/OperacaoEmpresaPage";
import { RazaoContasPage } from "../routes/pages/RazaoContasPage";
import { RevisarMovimentoPage } from "../routes/pages/RevisarMovimentoPage";

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to={ROUTES.empresas} replace />} />
        <Route path={ROUTES.login} element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path={ROUTES.empresas} element={<EmpresasPage />} />
            <Route
              path={ROUTES.empresa.operacaoPath}
              element={<OperacaoEmpresaPage />}
            />
            <Route
              path={ROUTES.empresa.importarMovimentosPath}
              element={<ImportarMovimentosPage />}
            />
            <Route
              path={ROUTES.empresa.loteMovimentosPath}
              element={<LoteMovimentosPage />}
            />
            <Route
              path={ROUTES.empresa.revisarMovimentoPath}
              element={<RevisarMovimentoPage />}
            />
            <Route
              path={ROUTES.empresa.razaoContasPath}
              element={<RazaoContasPage />}
            />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
