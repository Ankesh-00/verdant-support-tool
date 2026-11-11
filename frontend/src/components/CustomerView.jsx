import { useEffect, useState, useCallback } from "react";
import { api } from "../api.js";

function formatTime(iso) {
  return new Date(iso).toLocaleString([], {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "short",
  });
}

export default function CustomerView() {
  const [testCustomers, setTestCustomers] = useState([]);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [text, setText] = useState("");
  const [convo, setConvo] = useState(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .testCustomers()
      .then((list) => {
        setTestCustomers(list);
        if (list.length) {
          setName(list[0].name);
          setPhone(list[0].phone);
        }
      })
      .catch(() => {});
  }, []);

  const refresh = useCallback(async () => {
    if (!phone) return;
    try {
      const c = await api.customerConversation(phone);
      setConvo(c);
    } catch (e) {
      setError(e.message);
    }
  }, [phone]);

  // Load the selected customer's conversation, and poll so the agent's
  // approved reply shows up without a manual refresh.
  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, [refresh]);

  const pickTestCustomer = (e) => {
    const c = testCustomers.find((c) => c.phone === e.target.value);
    if (c) {
      setName(c.name);
      setPhone(c.phone);
    }
  };

  const send = async () => {
    setError("");
    if (!name.trim() || !phone.trim() || !text.trim()) {
      setError("Name, phone and a message are all required.");
      return;
    }
    setSending(true);
    try {
      await api.sendCustomerMessage({ name, phone, text });
      setText("");
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="card">
      <h2>Customer view</h2>
      <p className="muted mb">
        Pick a test customer (or type a name and phone), then send a message.
        It is handled exactly like a WhatsApp webhook delivery.
      </p>

      {testCustomers.length > 0 && (
        <div className="mb">
          <label>Quick pick</label>
          <select value={phone} onChange={pickTestCustomer}>
            {testCustomers.map((c) => (
              <option key={c.phone} value={c.phone}>
                {c.name} ({c.phone})
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="row mb">
        <div>
          <label>Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label>Phone</label>
          <input value={phone} onChange={(e) => setPhone(e.target.value)} />
        </div>
      </div>

      <label>Message</label>
      <textarea
        rows={3}
        value={text}
        placeholder="Hi, my order #4471 hasn't arrived yet. Can I change the delivery address?"
        onChange={(e) => setText(e.target.value)}
      />
      <div className="mt">
        <button className="btn" onClick={send} disabled={sending}>
          {sending ? "Sending…" : "Send message"}
        </button>
      </div>
      {error && <div className="error">{error}</div>}

      <hr className="mt" style={{ border: "none", borderTop: "1px solid var(--border)", margin: "20px 0" }} />

      <h2>Your conversation</h2>
      {!convo || convo.messages.length === 0 ? (
        <p className="muted">No messages yet. Send one above.</p>
      ) : (
        <div className="chat">
          {convo.messages.map((m) => (
            <div key={m.id} className={`bubble ${m.sender}`}>
              {m.text}
              <span className="time">
                {m.sender === "agent" ? "Verdant & Co · " : ""}
                {formatTime(m.created_at)}
              </span>
            </div>
          ))}
        </div>
      )}
      <p className="muted mt">
        You only see your own messages and replies the team has approved — never
        the AI draft.
      </p>
    </div>
  );
}
