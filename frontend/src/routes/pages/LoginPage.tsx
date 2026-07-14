import { useState } from "react";
import type { FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../../app/auth";
import {
  InvalidCredentialsError,
  NetworkAuthError,
  authClient,
} from "../../lib/api/authClient";
import { DEMO_PREVIEW_EMAIL, DEMO_PREVIEW_TOKEN } from "../../lib/demoPreview";
import { operationalMessages } from "../../ui/operationalMessages";
import { ROUTES } from "../paths";

export function LoginPage() {
  const { setSession } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(
    location.state?.reason === "Sessao expirada"
      ? `${operationalMessages.sessionExpired.login.title}. ${operationalMessages.sessionExpired.login.description}`
      : null,
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setIsSubmitting(true);

    try {
      const session = await authClient.login({ email, password });
      setSession(session);
      navigate(ROUTES.empresas, { replace: true });
    } catch (error) {
      if (
        error instanceof NetworkAuthError ||
        error instanceof TypeError ||
        String(error).includes("Failed to fetch")
      ) {
        setMessage(operationalMessages.error.network.description);
      } else if (error instanceof InvalidCredentialsError) {
        setMessage(
          "Credenciais invalidas. Verifique os dados ou contate o administrador.",
        );
      } else {
        setMessage(
          "Credenciais invalidas. Verifique os dados ou contate o administrador.",
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleDemoLogin() {
    setSession({
      accessToken: DEMO_PREVIEW_TOKEN,
      userEmail: DEMO_PREVIEW_EMAIL,
    });
    navigate(ROUTES.empresas, { replace: true });
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="grid min-h-screen lg:grid-cols-[0.95fr_1.05fr]">
        <section className="flex min-h-[280px] flex-col justify-between bg-[#004E61] p-8 text-white sm:p-10 lg:p-12">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-100">
              Classificador contabil
            </p>
            <h1 className="mt-8 max-w-xl text-4xl font-semibold leading-tight sm:text-5xl">
              Operacao interna com rastreabilidade por usuario.
            </h1>
          </div>
          <div className="mt-10 grid gap-3 text-sm text-cyan-50 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
            <span className="border-l-2 border-[#007693] pl-3">
              Login individual
            </span>
            <span className="border-l-2 border-[#007693] pl-3">
              Empresas permitidas
            </span>
            <span className="border-l-2 border-[#007693] pl-3">Sessao JWT</span>
          </div>
        </section>

        <section className="flex items-center justify-center px-5 py-10 sm:px-8">
          <div className="w-full max-w-[420px]">
            <div className="mb-7">
              <p className="text-sm font-medium text-[#007693]">
                Acesso restrito
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-slate-950">
                Entrar
              </h2>
            </div>

            {message ? (
              <p
                className="mb-4 border-l-4 border-[#007693] bg-white px-4 py-3 text-sm text-slate-700 shadow-sm"
                role="alert"
              >
                {message}
              </p>
            ) : null}

            <form className="space-y-4" onSubmit={handleSubmit}>
              <label className="block text-sm font-medium text-slate-700">
                Email
                <input
                  autoComplete="username"
                  className="mt-2 w-full border border-slate-300 bg-white px-3 py-2.5 text-base text-slate-950 outline-none transition focus:border-[#007693] focus:ring-2 focus:ring-[#007693]/20"
                  name="email"
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  type="email"
                  value={email}
                />
              </label>

              <label className="block text-sm font-medium text-slate-700">
                Senha
                <input
                  autoComplete="current-password"
                  className="mt-2 w-full border border-slate-300 bg-white px-3 py-2.5 text-base text-slate-950 outline-none transition focus:border-[#007693] focus:ring-2 focus:ring-[#007693]/20"
                  name="password"
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  type="password"
                  value={password}
                />
              </label>

              <button
                className="w-full bg-[#007693] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#004E61] focus:outline-none focus:ring-2 focus:ring-[#007693] focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-400"
                disabled={isSubmitting}
                type="submit"
              >
                {isSubmitting ? "Entrando..." : "Entrar"}
              </button>
            </form>

            {import.meta.env.DEV ||
            import.meta.env.VITE_ENABLE_DEMO_LOGIN === "true" ? (
              <button
                className="mt-3 w-full border border-[#007693] bg-white px-4 py-2.5 text-sm font-semibold text-[#004E61] transition hover:bg-[#007693]/5 focus:outline-none focus:ring-2 focus:ring-[#007693] focus:ring-offset-2"
                onClick={handleDemoLogin}
                type="button"
              >
                Entrar em modo demo
              </button>
            ) : null}

            <p className="mt-5 text-sm leading-6 text-slate-600">
              Problemas de acesso devem ser tratados com o administrador
              interno.
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
