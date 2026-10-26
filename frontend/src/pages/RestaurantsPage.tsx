import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { errorMessage, request } from "../api";
import { useAuth } from "../auth";
import type { MenuItem, Order, Page, Restaurant } from "../types";

const money = (value: string | number) => `RON ${Number(value).toFixed(2)}`;

export default function RestaurantsPage() {
  const { user } = useAuth();

  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [selected, setSelected] = useState<Restaurant | null>(null);
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [menuLoading, setMenuLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [placing, setPlacing] = useState(false);
  const [placed, setPlaced] = useState<Order | null>(null);

  useEffect(() => {
    request<Page<Restaurant>>("/api/restaurants?limit=50")
      .then((page) => setRestaurants(page.items))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  async function choose(restaurant: Restaurant) {
    setSelected(restaurant);
    setMenu([]);
    setQuantities({});
    setPlaced(null);
    setError(null);
    setMenuLoading(true);
    try {
      const page = await request<Page<MenuItem>>(
        `/api/restaurants/${restaurant.id}/menu-items?limit=100`,
      );
      setMenu(page.items);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setMenuLoading(false);
    }
  }

  function setQuantity(id: string, quantity: number) {
    setQuantities((previous) => ({
      ...previous,
      [id]: Math.max(0, Math.min(99, quantity)),
    }));
  }

  const lines = menu
    .filter((item) => (quantities[item.id] ?? 0) > 0)
    .map((item) => ({ item, quantity: quantities[item.id] }));
  const total = lines.reduce(
    (sum, line) => sum + Number(line.item.price) * line.quantity,
    0,
  );

  async function placeOrder() {
    if (!selected || lines.length === 0) return;
    setPlacing(true);
    setError(null);
    try {
      const order = await request<Order>("/api/orders", {
        method: "POST",
        body: {
          restaurant_id: selected.id,
          items: lines.map((line) => ({
            menu_item_id: line.item.id,
            quantity: line.quantity,
          })),
        },
      });
      setPlaced(order);
      setQuantities({});
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPlacing(false);
    }
  }

  if (loading) return <p className="muted">Loading restaurants…</p>;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Restaurants</h1>
          <p className="muted">
            Browse menus and place an order. Empty restaurants are public; admin
            endpoints are guarded server-side.
          </p>
        </div>
      </div>

      {error && <p className="alert alert-error">{error}</p>}

      {placed && (
        <p className="alert alert-success">
          Order <code>{placed.id.slice(0, 8)}</code> created —{" "}
          {money(placed.total_amount)}, status{" "}
          <strong>{placed.status}</strong>. <Link to="/orders">Track it</Link>
        </p>
      )}

      <div className="two-col">
        <section className="card">
          <h2>All restaurants</h2>
          {restaurants.length === 0 && (
            <p className="muted">
              No restaurants yet. Sign in as admin and create one.
            </p>
          )}
          <ul className="restaurant-list">
            {restaurants.map((restaurant) => (
              <li key={restaurant.id}>
                <button
                  type="button"
                  className={
                    selected?.id === restaurant.id
                      ? "restaurant selected"
                      : "restaurant"
                  }
                  onClick={() => void choose(restaurant)}
                >
                  <span className="restaurant-name">{restaurant.name}</span>
                  <span className="muted small">{restaurant.address}</span>
                  {restaurant.cuisine_type && (
                    <span className="badge badge-neutral">
                      {restaurant.cuisine_type}
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="card">
          <h2>{selected ? selected.name : "Menu"}</h2>
          {!selected && (
            <p className="muted">Pick a restaurant to see its menu.</p>
          )}
          {selected && menuLoading && <p className="muted">Loading menu…</p>}
          {selected && !menuLoading && menu.length === 0 && (
            <p className="muted">This restaurant has no menu items yet.</p>
          )}

          {menu.map((item) => (
            <div key={item.id} className="menu-row">
              <div>
                <strong>{item.name}</strong>
                <p className="muted small">
                  {item.description ?? "No description"}
                </p>
              </div>
              <div className="menu-controls">
                <span className="price">{money(item.price)}</span>
                {item.is_available ? (
                  <div className="stepper">
                    <button
                      type="button"
                      onClick={() =>
                        setQuantity(item.id, (quantities[item.id] ?? 0) - 1)
                      }
                      aria-label={`Remove one ${item.name}`}
                    >
                      −
                    </button>
                    <span>{quantities[item.id] ?? 0}</span>
                    <button
                      type="button"
                      onClick={() =>
                        setQuantity(item.id, (quantities[item.id] ?? 0) + 1)
                      }
                      aria-label={`Add one ${item.name}`}
                    >
                      +
                    </button>
                  </div>
                ) : (
                  <span className="badge badge-cancelled">unavailable</span>
                )}
              </div>
            </div>
          ))}

          {selected && menu.length > 0 && (
            <div className="checkout">
              <div className="checkout-total">
                <span>{lines.length} line(s)</span>
                <strong>{money(total)}</strong>
              </div>
              {!user && (
                <p className="muted small">
                  <Link to="/login">Sign in</Link> to place an order.
                </p>
              )}
              <button
                type="button"
                className="btn btn-primary"
                disabled={!user || lines.length === 0 || placing}
                onClick={() => void placeOrder()}
              >
                {placing ? "Placing…" : "Place order"}
              </button>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
