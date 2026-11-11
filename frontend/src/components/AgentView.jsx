import { useEffect, useState, useCallback } from "react";
import { api, auth } from "../api.js";

function formatTime(iso) {
  return new Date(iso).toLocaleString([], {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "short",
  });
}

export default function AgentView() {
  const [token, setToken] = useState(auth.get());

  if (!token) {
    return <Login onLoggedIn={() => setToken(auth.get())} />;
  }
  return <AgentConsole onLogout={() => { auth.clear(); setToken(null); }} />;
}

function Login({ onLoggedIn }) {
  const [username, setUsername] = useState("agent");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await api.login(username, password);
      auth.set(res.token);
      onLoggedIn();
    } catch (err) {
      setError(err.status === 401 ? "Invalid credentials." : err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card" style={{ maxWidth: 380, margin: "40px auto" }}>
      <h2>Agent sign in</h2>
      <form onSubmit={submit}>
        <div className="mb">
          <label>Username</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} />
        </div>
        <div className="mb">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <button className="btn" type="submit" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        {error && <div className="error">{error}</div>}
      </form>
    </div>
  );
}

function AgentConsole({ onLogout }) {
  const [conversations, setConversations] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [listError, setListError] = useState("");

  const loadList = useCallback(async () => {
    try {
      const list = await api.conversations();
      setConversations(list);
      setListError("");
    } catch (e) {
      if (e.status === 401) {
        onLogout();
        return;
      }
      setListError(e.message);
    }
  }, [onLogout]);

  useEffect(() => {
    loadList();
    const id = setInterval(loadList, 5000); // keep the list fresh
    return () => clearInterval(id);
  }, [loadList]);

  return (
    <>
      <div className="mb" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>Conversations</h2>
        <button className="btn secondary" onClick={onLogout}>Sign out</button>
      </div>
      {listError && <div className="error">{listError}</div>}
      <div className="agent-layout">
        <div>
          {conversations.length === 0 && (
            <p className="muted">No conversations yet. Send one from the Customer view.</p>
          )}
          {conversations.map((c) => (
            <div
              key={c.id}
              className={`convo-item ${selectedId === c.id ? "active" : ""}`}
              onClick={() => setSelectedId(c.id)}
            >
              <div className="name">
                <span>{c.customer_name}</span>
                {c.pending_draft && <span className="badge">draft</span>}
              </div>
              <div className="preview">{c.last_message_preview || "…"}</div>
              <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>
                {formatTime(c.last_activity_at)}
              </div>
            </div>
          ))}
        </div>
        <div>
          {selectedId ? (
            <ConversationPage
              id={selectedId}
              onApproved={loadList}
              onAuthError={onLogout}
            />
          ) : (
            <div className="card"><p className="muted">Select a conversation to review its draft.</p></div>
          )}
        </div>
      </div>
    </>
  );
}

function ConversationPage({ id, onApproved, onAuthError }) {
  const [convo, setConvo] = useState(null);
  const [draftText, setDraftText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const c = await api.conversation(id);
      setConvo(c);
      setDraftText(c.draft ? c.draft.text : "");
      setError("");
    } catch (e) {
      if (e.status === 401) return onAuthError();
      setError(e.message);
    }
  }, [id, onAuthError]);

  useEffect(() => { load(); }, [load]);

  const approve = async () => {
    if (!convo?.draft) return;
    setError("");
    setBusy(true);
    try {
      const updated = await api.approve(id, convo.draft.id, draftText);
      setConvo(updated);
      setDraftText(updated.draft ? updated.draft.text : "");
      onApproved();
    } catch (e) {
      if (e.status === 401) return onAuthError();
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (!convo) return <div className="card"><p className="muted">Loading…</p></div>;

  return (
    <div className="card">
      <h2>{convo.customer_name} <span className="muted" style={{ fontWeight: 400 }}>· {convo.customer_phone}</span></h2>

      <div className="chat">
        {convo.messages.map((m) => (
          <div key={m.id} className={`bubble ${m.sender}`}>
            {m.text}
            <span className="time">{m.sender === "agent" ? "You · " : ""}{formatTime(m.created_at)}</span>
          </div>
        ))}
      </div>

      {convo.draft ? (
        <div className="draft-box">
          <div className="draft-label">AI draft reply — edit before approving</div>
          {convo.draft.status === "failed" && (
            <div className="draft-warn">
              The AI draft could not be generated (a fallback is shown). Reason:{" "}
              {convo.draft.error_detail || "unknown"}. You can still write and approve a reply.
            </div>
          )}
          <textarea
            rows={5}
            value={draftText}
            onChange={(e) => setDraftText(e.target.value)}
          />
          <div className="mt">
            <button className="btn" onClick={approve} disabled={busy || !draftText.trim()}>
              {busy ? "Approving…" : "Approve & send"}
            </button>
          </div>
          {error && <div className="error">{error}</div>}
        </div>
      ) : (
        <p className="muted mt">No pending draft. The latest reply has been approved.</p>
      )}
    </div>
  );
}
