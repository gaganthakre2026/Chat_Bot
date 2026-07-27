import { FileSearch, LockKeyhole, Mail, Sparkles } from "lucide-react";
import { useState } from "react";
import { signIn, signUp } from "../api/client.js";
import { supabase } from "../lib/supabaseClient.js";

export default function AuthPanel() {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const authResponse =
        mode === "login" ? await signIn(email, password) : await signUp(email, password);

      if (!authResponse.access_token || !authResponse.refresh_token) {
        throw new Error(authResponse.message || "Authentication succeeded but no session was returned.");
      }

      const { error: sessionError } = await supabase.auth.setSession({
        access_token: authResponse.access_token,
        refresh_token: authResponse.refresh_token,
      });

      if (sessionError) throw sessionError;
    } catch (authError) {
      setError(
        authError?.message ||
          "Sign in failed. Check your email/password and ensure the backend is running on port 8000.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-gradient flex min-h-screen items-center justify-center px-4 py-10">
      <div className="grid w-full max-w-5xl gap-8 lg:grid-cols-2 lg:items-center">
        <section className="slide-up hidden lg:block">
          <div className="inline-flex items-center gap-2 rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold text-indigo-700">
            <Sparkles size={14} />
            PDF-grounded answers only
          </div>
          <h1 className="mt-6 text-4xl font-bold tracking-tight text-slate-900">
            Chat with your documents
          </h1>
          <p className="mt-4 max-w-md text-base leading-7 text-slate-600">
            Upload a PDF, ask questions, and get answers backed by your file — with confidence
            scores and source pages shown for every reply.
          </p>
          <ul className="mt-8 space-y-3 text-sm text-slate-600">
            <li className="flex items-center gap-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-100 text-indigo-600">
                <FileSearch size={16} />
              </span>
              Answers use only data extracted from your PDF
            </li>
            <li className="flex items-center gap-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-100 text-sky-600">
                <Sparkles size={16} />
              </span>
              Confidence score on every response
            </li>
          </ul>
        </section>

        <section className="glass-card slide-up p-8">
          <div className="mb-8 text-center lg:text-left">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-600 text-white lg:mx-0">
              <FileSearch size={22} />
            </div>
            <h2 className="text-2xl font-bold text-slate-900">Welcome to DocChat</h2>
            <p className="mt-2 text-sm text-slate-500">
              {mode === "login" ? "Sign in to continue" : "Create your account to get started"}
            </p>
          </div>

          <div className="mb-6 grid grid-cols-2 rounded-xl bg-slate-100 p-1">
            <button
              type="button"
              onClick={() => setMode("login")}
              className={`h-10 rounded-lg text-sm font-semibold transition ${
                mode === "login"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={() => setMode("signup")}
              className={`h-10 rounded-lg text-sm font-semibold transition ${
                mode === "signup"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Sign up
            </button>
          </div>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-slate-700">Email</span>
              <span className="flex h-12 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 transition focus-within:border-indigo-500 focus-within:ring-4 focus-within:ring-indigo-100">
                <Mail size={18} className="shrink-0 text-slate-400" />
                <input
                  className="w-full border-0 bg-transparent text-sm outline-none"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </span>
            </label>

            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-slate-700">Password</span>
              <span className="flex h-12 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 transition focus-within:border-indigo-500 focus-within:ring-4 focus-within:ring-indigo-100">
                <LockKeyhole size={18} className="shrink-0 text-slate-400" />
                <input
                  className="w-full border-0 bg-transparent text-sm outline-none"
                  type="password"
                  placeholder="Minimum 6 characters"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  minLength={6}
                  required
                />
              </span>
            </label>

            {error ? (
              <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700 ring-1 ring-rose-100">
                {error}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={loading}
              className="inline-flex h-12 w-full items-center justify-center rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-sm font-semibold text-white shadow-lg shadow-indigo-200 transition hover:from-indigo-500 hover:to-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Please wait..." : mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>
        </section>
      </div>
    </main>
  );
}
