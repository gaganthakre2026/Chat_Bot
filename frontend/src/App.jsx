import { FileSearch, Loader2, LogOut } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { deleteDocument, getHistory, listDocuments } from "./api/client.js";
import AuthPanel from "./components/AuthPanel.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import DocumentList from "./components/DocumentList.jsx";
import UploadButton from "./components/UploadButton.jsx";
import { isSupabaseConfigured, supabase } from "./lib/supabaseClient.js";

function getStoredSessionKey(userId, documentId) {
  return `pdf-rag:${userId}:${documentId}:session`;
}

function ConfigurationMissing() {
  return (
    <main className="auth-gradient flex min-h-screen items-center justify-center px-4">
      <section className="glass-card max-w-lg p-8 text-center">
        <h1 className="text-xl font-bold text-slate-900">Configuration missing</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          Add <code className="rounded bg-slate-100 px-1">VITE_SUPABASE_URL</code> and{" "}
          <code className="rounded bg-slate-100 px-1">VITE_SUPABASE_ANON_KEY</code> to{" "}
          <code className="rounded bg-slate-100 px-1">frontend/.env</code>, then restart Vite.
        </p>
      </section>
    </main>
  );
}

function LoadingScreen() {
  return (
    <main className="auth-gradient flex min-h-screen items-center justify-center">
      <div className="flex items-center gap-3 text-sm font-medium text-slate-600">
        <Loader2 size={20} className="animate-spin text-indigo-600" />
        Loading DocChat
      </div>
    </main>
  );
}

function Workspace({ session }) {
  const token = session.access_token;
  const userId = session.user.id;
  const [documents, setDocuments] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState("");
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const selectedDocument = useMemo(
    () => documents.find((document) => document.id === selectedId) || documents[0] || null,
    [documents, selectedId],
  );

  const loadDocuments = useCallback(async () => {
    if (!token) return;
    setLoadingDocuments(true);
    setError("");
    try {
      const nextDocuments = await listDocuments(token);
      setDocuments(nextDocuments);
      if (!selectedId && nextDocuments.length) {
        setSelectedId(nextDocuments[0].id);
      }
      if (selectedId && !nextDocuments.some((document) => document.id === selectedId)) {
        setSelectedId(nextDocuments[0]?.id || "");
      }
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoadingDocuments(false);
    }
  }, [selectedId, token]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    if (!documents.some((document) => document.status === "processing")) return undefined;
    const intervalId = window.setInterval(loadDocuments, 3000);
    return () => window.clearInterval(intervalId);
  }, [documents, loadDocuments]);

  useEffect(() => {
    async function loadHistory() {
      if (!selectedDocument || !token) {
        setMessages([]);
        setSessionId("");
        return;
      }

      const storedSessionId = window.localStorage.getItem(
        getStoredSessionKey(userId, selectedDocument.id),
      );
      setSessionId(storedSessionId || "");

      if (!storedSessionId) {
        setMessages([]);
        return;
      }

      setLoadingHistory(true);
      setError("");
      try {
        const history = await getHistory(storedSessionId, token);
        setMessages(history);
      } catch {
        window.localStorage.removeItem(getStoredSessionKey(userId, selectedDocument.id));
        setSessionId("");
        setMessages([]);
      } finally {
        setLoadingHistory(false);
      }
    }

    loadHistory();
  }, [selectedDocument?.id, token, userId]);

  function handleSessionId(nextSessionId) {
    setSessionId(nextSessionId);
    if (selectedDocument) {
      window.localStorage.setItem(getStoredSessionKey(userId, selectedDocument.id), nextSessionId);
    }
  }

  function handleSelectDocument(documentId) {
    setSelectedId(documentId);
    setMessages([]);
    setSessionId("");
    setSidebarOpen(false);
  }

  async function handleUploaded(document) {
    setDocuments((current) => [document, ...current.filter((item) => item.id !== document.id)]);
    setSelectedId(document.id);
    setMessages([]);
    setSessionId("");
    await loadDocuments();
  }

  async function handleDelete(documentId) {
    const confirmed = window.confirm("Delete this document and all its indexed data?");
    if (!confirmed) return;
    setError("");
    try {
      await deleteDocument(documentId, token);
      window.localStorage.removeItem(getStoredSessionKey(userId, documentId));
      setDocuments((current) => current.filter((document) => document.id !== documentId));
      if (selectedId === documentId) {
        setSelectedId("");
        setMessages([]);
        setSessionId("");
      }
    } catch (deleteError) {
      setError(deleteError.message);
    }
  }

  async function handleSignOut() {
    await supabase.auth.signOut();
  }

  return (
    <main className="chat-gradient flex h-screen min-h-[620px] flex-col text-slate-950">
      <header className="z-10 flex min-h-[64px] items-center justify-between gap-4 border-b border-slate-200/80 bg-white/80 px-4 backdrop-blur-md">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 text-white shadow-md shadow-indigo-200">
            <FileSearch size={20} />
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-base font-bold text-slate-900">DocChat</h1>
            <p className="truncate text-xs text-slate-500">{session.user.email}</p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <UploadButton token={token} onUploaded={handleUploaded} />
          <button
            type="button"
            onClick={() => setSidebarOpen((value) => !value)}
            className="inline-flex h-10 items-center rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50 lg:hidden"
          >
            Docs
          </button>
          <button
            type="button"
            onClick={handleSignOut}
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900"
            title="Sign out"
          >
            <LogOut size={18} />
          </button>
        </div>
      </header>

      {error ? (
        <div className="border-b border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      <div className="relative flex min-h-0 flex-1">
        <aside
          className={`absolute inset-y-0 left-0 z-20 w-72 border-r border-slate-200 bg-white shadow-xl transition-transform lg:static lg:translate-x-0 lg:shadow-none ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <DocumentList
            documents={documents}
            selectedId={selectedDocument?.id}
            loading={loadingDocuments}
            onSelect={handleSelectDocument}
            onDelete={handleDelete}
            onRefresh={loadDocuments}
          />
        </aside>

        {sidebarOpen ? (
          <button
            type="button"
            className="absolute inset-0 z-10 bg-slate-900/20 lg:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close documents panel"
          />
        ) : null}

        <ChatWindow
          document={selectedDocument}
          documents={documents}
          onSelectDocument={handleSelectDocument}
          messages={messages}
          setMessages={setMessages}
          token={token}
          sessionId={sessionId || null}
          onSessionId={handleSessionId}
          loadingHistory={loadingHistory}
        />
      </div>
    </main>
  );
}

export default function App() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isSupabaseConfigured) {
      setLoading(false);
      return undefined;
    }

    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setLoading(false);
    });

    return () => listener.subscription.unsubscribe();
  }, []);

  if (!isSupabaseConfigured) return <ConfigurationMissing />;
  if (loading) return <LoadingScreen />;
  if (!session) return <AuthPanel />;

  return <Workspace session={session} />;
}
