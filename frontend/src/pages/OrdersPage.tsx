import { useCallback, useEffect, useState } from "react";

import { errorMessage, request } from "../api";
import { useAuth } from "../auth";
import { StatusBadge } from "../components/StatusBadge";
import { NEXT_STATUSES, type Order, type OrderStatus, type Page } from "../types";

const money = (value: string | number) => `RON ${Number(value).toFixed(2)}`;

export default function OrdersPage() {
  const { user } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const page = await request<Page<Order>>("/api/orders?limit=50");
      setOrders(page.items);
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function advance(order: Order, status: OrderStatus) {
    setBusyId(order.id);
    setError(null);
    try {
      await request<Order>(`/api/orders/${order.id}/status`, {
        method: "PATCH",
        body: { status },
      });
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  async function cancel(order: Order) {
    setBusyId(order.id);
    setError(null);
    try {
      await request<Order>(`/api/orders/${order.id}/cancel`, { method: "POST" });
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Orders</h1>
          <p className="muted">
            {user?.role === "admin"
              ? "Admins see every order and can advance statuses. Cancelling is owner-only."
              : "You only see your own orders. Another customer's order returns 404."}
          </p>
        </div>
        <button type="button" className="btn" onClick={() => void load()}>
          Refresh
        </button>
      </div>

      {error && <p className="alert alert-error">{error}</p>}

      {orders.length === 0 && (
        <p className="muted">No orders yet. Place one from the Restaurants page.</p>
      )}

      <div className="stack">
        {orders.map((order) => {
          const isOwner = order.customer_id === user?.id;
          const cancellable = isOwner && order.status === "pending";
          const nextStatuses =
            user?.role === "admin" ? NEXT_STATUSES[order.status] : [];

          return (
            <article key={order.id} className="card order-card">
              <header className="order-head">
                <div>
                  <strong>#{order.id.slice(0, 8)}</strong>
                  <span className="muted small">
                    {" "}
                    {new Date(order.ordered_at).toLocaleString()}
                  </span>
                </div>
                <div className="order-head-right">
                  <StatusBadge tone={order.status}>{order.status}</StatusBadge>
                  <span className="price">{money(order.total_amount)}</span>
                </div>
              </header>

              <ul className="order-lines">
                {order.items.map((line) => (
                  <li key={line.menu_item_id ?? line.menu_item_name}>
                    <span>
                      {line.quantity} × {line.menu_item_name}
                    </span>
                    <span className="muted">
                      {money(line.line_total)}
                    </span>
                  </li>
                ))}
              </ul>

              <footer className="order-actions">
                {isOwner && <span className="tag">your order</span>}
                {cancellable && (
                  <button
                    type="button"
                    className="btn btn-small btn-danger"
                    disabled={busyId === order.id}
                    onClick={() => void cancel(order)}
                  >
                    Cancel
                  </button>
                )}
                {nextStatuses.map((status) => (
                  <button
                    key={status}
                    type="button"
                    className="btn btn-small"
                    disabled={busyId === order.id}
                    onClick={() => void advance(order, status)}
                  >
                    {status.replace(/_/g, " ")}
                  </button>
                ))}
              </footer>
            </article>
          );
        })}
      </div>
    </div>
  );
}
