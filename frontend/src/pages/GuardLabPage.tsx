import { useState } from "react";

import {
  decodeToken,
  getToken,
  rawRequest,
  request,
  type RawResponse,
} from "../api";
import { useAuth } from "../auth";
import type { Order, Page } from "../types";

interface CheckResult {
  label: string;
  expected: string;
  actual: string;
  ok: boolean;
  detail: string;
}

const short = (value: unknown): string => {
  const text = JSON.stringify(value);
  if (!text) return "";
  return text.length > 140 ? `${text.slice(0, 140)}…` : text;
};

export default function GuardLabPage() {
  const { user } = useAuth();
  const claims = decodeToken(getToken());

  const [results, setResults] = useState<CheckResult[]>([]);
  const [busy, setBusy] = useState(false);
  const [otherOrderId, setOtherOrderId] = useState("");

  function record(
    label: string,
    expected: string,
    actual: string,
    ok: boolean,
    detail: string,
  ) {
    setResults((previous) => [
      { label, expected, actual, ok, detail },
      ...previous,
    ]);
  }

  async function run(
    label: string,
    expected: string,
    call: () => Promise<RawResponse>,
    ok: (status: number) => boolean,
  ) {
    setBusy(true);
    try {
      const { status, body } = await call();
      record(label, expected, String(status), ok(status), short(body));
    } catch (error) {
      record(
        label,
        expected,
        "network error",
        false,
        error instanceof Error ? error.message : String(error),
      );
    } finally {
      setBusy(false);
    }
  }

  async function ownershipCheck() {
    setBusy(true);
    try {
      const page = await request<Page<Order>>("/api/orders?limit=100");
      const isMine = page.items.some((order) => order.id === otherOrderId);
      const expectedStatus = user?.role === "admin" || isMine ? 200 : 404;
      const { status, body } = await rawRequest(`/api/orders/${otherOrderId}`);
      record(
        "GET another customer's order",
        String(expectedStatus),
        String(status),
        status === expectedStatus,
        short(body),
      );
    } catch (error) {
      record(
        "GET another customer's order",
        "200 or 404",
        "network error",
        false,
        error instanceof Error ? error.message : String(error),
      );
    } finally {
      setBusy(false);
    }
  }

  async function statusCheck() {
    setBusy(true);
    try {
      const page = await request<Page<Order>>("/api/orders?limit=1");
      const order = page.items[0];
      if (!order) {
        record(
          "PATCH order status (admin-only)",
          user?.role === "admin" ? "200" : "403",
          "no order",
          false,
          "Place an order first, then retry.",
        );
        return;
      }
      const expected = user?.role === "admin" ? 200 : 403;
      const { status, body } = await rawRequest(
        `/api/orders/${order.id}/status`,
        { method: "PATCH", body: { status: order.status } },
      );
      record(
        "PATCH order status (admin-only)",
        String(expected),
        String(status),
        status === expected,
        short(body),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Guard lab</h1>
          <p className="muted">
            Each button performs a real HTTP call and shows the status the server
            returned. Expectations are based on the signed-in role.
          </p>
        </div>
      </div>

      <section className="card">
        <h2>Current session</h2>
        <p>
          Signed in as <strong>{user?.email}</strong> with role{" "}
          <span className={`badge badge-${user?.role}`}>{user?.role}</span>.
        </p>
        <p className="muted small">
          The JWT carries a role claim for convenience, but the backend reloads
          the user from the database on every request — tokens are not trusted
          for authorisation.
        </p>
        <pre className="code">{JSON.stringify(claims, null, 2)}</pre>
      </section>

      <section className="card">
        <h2>Authentication checks</h2>
        <div className="button-row">
          <button
            type="button"
            className="btn"
            disabled={busy}
            onClick={() =>
              void run(
                "GET /api/orders without a token",
                "401",
                () => rawRequest("/api/orders", { token: null }),
                (status) => status === 401,
              )
            }
          >
            No token → 401
          </button>
          <button
            type="button"
            className="btn"
            disabled={busy}
            onClick={() =>
              void run(
                "GET /api/orders with a garbage token",
                "401",
                () => rawRequest("/api/orders", { token: "not-a-jwt" }),
                (status) => status === 401,
              )
            }
          >
            Bad token → 401
          </button>
          <button
            type="button"
            className="btn"
            disabled={busy}
            onClick={() =>
              void run(
                "Login as disabled account",
                "403",
                () =>
                  rawRequest("/api/auth/login", {
                    method: "POST",
                    token: null,
                    form: new URLSearchParams({
                      username: "blocked@example.com",
                      password: "blocked12345",
                    }),
                  }),
                (status) => status === 403,
              )
            }
          >
            Disabled login → 403
          </button>
        </div>
      </section>

      <section className="card">
        <h2>Role checks</h2>
        <p className="muted small">
          As an admin both calls pass; as a customer the server rejects them even
          though the UI could be bypassed.
        </p>
        <div className="button-row">
          <button
            type="button"
            className="btn"
            disabled={busy}
            onClick={() =>
              void run(
                "POST /api/restaurants (admin-only)",
                user?.role === "admin" ? "201" : "403",
                () =>
                  rawRequest("/api/restaurants", {
                    method: "POST",
                    body: {
                      name: `Guard check ${new Date().toLocaleTimeString()}`,
                      address: "Created by the guard lab",
                    },
                  }),
                (status) =>
                  user?.role === "admin" ? status === 201 : status === 403,
              )
            }
          >
            Create restaurant → {user?.role === "admin" ? "201" : "403"}
          </button>
          <button
            type="button"
            className="btn"
            disabled={busy}
            onClick={() => void statusCheck()}
          >
            Update order status → {user?.role === "admin" ? "200" : "403"}
          </button>
        </div>
      </section>

      <section className="card">
        <h2>Ownership check</h2>
        <p className="muted small">
          Paste an order id that belongs to another account (place an order as
          Customer 2, copy its id, sign in as Customer 1). Owners and admins get
          <code> 200</code>; everyone else gets <code>404</code>, not 403.
        </p>
        <div className="row">
          <input
            value={otherOrderId}
            onChange={(event) => setOtherOrderId(event.target.value)}
            placeholder="order UUID"
          />
          <button
            type="button"
            className="btn"
            disabled={busy || !otherOrderId}
            onClick={() => void ownershipCheck()}
          >
            Try to read it
          </button>
        </div>
      </section>

      <section className="card">
        <h2>Results</h2>
        {results.length === 0 && (
          <p className="muted">Run a check above to see the response.</p>
        )}
        {results.length > 0 && (
          <table className="result-table">
            <thead>
              <tr>
                <th>Check</th>
                <th>Expected</th>
                <th>Actual</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {results.map((result, index) => (
                <tr key={`${result.label}-${index}`}>
                  <td>
                    {result.label}
                    <div className="muted small">{result.detail}</div>
                  </td>
                  <td>{result.expected}</td>
                  <td>{result.actual}</td>
                  <td>
                    <span
                      className={
                        result.ok ? "badge badge-delivered" : "badge badge-cancelled"
                      }
                    >
                      {result.ok ? "pass" : "fail"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
