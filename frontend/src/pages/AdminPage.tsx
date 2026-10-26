import { useCallback, useEffect, useState, type FormEvent } from "react";

import { errorMessage, request } from "../api";
import type { MenuItem, Page, Restaurant } from "../types";

const money = (value: string | number) => `RON ${Number(value).toFixed(2)}`;

export default function AdminPage() {
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [priceDrafts, setPriceDrafts] = useState<Record<string, string>>({});

  const [restaurantForm, setRestaurantForm] = useState({
    name: "",
    address: "",
    phone: "",
    cuisine_type: "",
  });
  const [itemForm, setItemForm] = useState({
    name: "",
    price: "",
    description: "",
  });

  const loadRestaurants = useCallback(async () => {
    try {
      const page = await request<Page<Restaurant>>("/api/restaurants?limit=100");
      setRestaurants(page.items);
      setSelectedId((current) => current || page.items[0]?.id || "");
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  const loadMenu = useCallback(async (restaurantId: string) => {
    if (!restaurantId) {
      setMenu([]);
      return;
    }
    try {
      const page = await request<Page<MenuItem>>(
        `/api/restaurants/${restaurantId}/menu-items?limit=100`,
      );
      setMenu(page.items);
      setPriceDrafts(
        Object.fromEntries(page.items.map((item) => [item.id, item.price])),
      );
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    void loadRestaurants();
  }, [loadRestaurants]);

  useEffect(() => {
    void loadMenu(selectedId);
  }, [selectedId, loadMenu]);

  async function createRestaurant(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const created = await request<Restaurant>("/api/restaurants", {
        method: "POST",
        body: {
          name: restaurantForm.name,
          address: restaurantForm.address,
          phone: restaurantForm.phone || null,
          cuisine_type: restaurantForm.cuisine_type || null,
        },
      });
      setNotice(`Created restaurant “${created.name}”.`);
      setRestaurantForm({ name: "", address: "", phone: "", cuisine_type: "" });
      await loadRestaurants();
      setSelectedId(created.id);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function createMenuItem(event: FormEvent) {
    event.preventDefault();
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await request<MenuItem>(`/api/restaurants/${selectedId}/menu-items`, {
        method: "POST",
        body: {
          name: itemForm.name,
          price: itemForm.price,
          description: itemForm.description || null,
          is_available: true,
        },
      });
      setNotice(`Added “${itemForm.name}”.`);
      setItemForm({ name: "", price: "", description: "" });
      await loadMenu(selectedId);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function savePrice(item: MenuItem) {
    setError(null);
    setNotice(null);
    try {
      await request<MenuItem>(`/api/menu-items/${item.id}`, {
        method: "PATCH",
        body: { price: priceDrafts[item.id] },
      });
      await loadMenu(selectedId);
      setNotice(`Updated price for “${item.name}”.`);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function toggleAvailability(item: MenuItem) {
    setError(null);
    setNotice(null);
    try {
      await request<MenuItem>(`/api/menu-items/${item.id}`, {
        method: "PATCH",
        body: { is_available: !item.is_available },
      });
      await loadMenu(selectedId);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function deleteItem(item: MenuItem) {
    setError(null);
    setNotice(null);
    try {
      await request<void>(`/api/menu-items/${item.id}`, { method: "DELETE" });
      await loadMenu(selectedId);
      setNotice(`Deleted “${item.name}”.`);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Admin</h1>
          <p className="muted">
            Every action here hits an admin-only endpoint; a customer calling it
            directly gets <code>403</code> (see Guard lab).
          </p>
        </div>
      </div>

      {error && <p className="alert alert-error">{error}</p>}
      {notice && <p className="alert alert-success">{notice}</p>}

      <div className="two-col">
        <section className="card">
          <h2>Create restaurant</h2>
          <form className="stack" onSubmit={createRestaurant}>
            <label>
              Name
              <input
                required
                value={restaurantForm.name}
                onChange={(event) =>
                  setRestaurantForm({
                    ...restaurantForm,
                    name: event.target.value,
                  })
                }
              />
            </label>
            <label>
              Address
              <input
                required
                value={restaurantForm.address}
                onChange={(event) =>
                  setRestaurantForm({
                    ...restaurantForm,
                    address: event.target.value,
                  })
                }
              />
            </label>
            <div className="row">
              <label>
                Phone
                <input
                  value={restaurantForm.phone}
                  onChange={(event) =>
                    setRestaurantForm({
                      ...restaurantForm,
                      phone: event.target.value,
                    })
                  }
                />
              </label>
              <label>
                Cuisine
                <input
                  value={restaurantForm.cuisine_type}
                  onChange={(event) =>
                    setRestaurantForm({
                      ...restaurantForm,
                      cuisine_type: event.target.value,
                    })
                  }
                />
              </label>
            </div>
            <button className="btn btn-primary" disabled={busy} type="submit">
              Create restaurant
            </button>
          </form>
        </section>

        <section className="card">
          <h2>Menu manager</h2>
          <label>
            Restaurant
            <select
              value={selectedId}
              onChange={(event) => setSelectedId(event.target.value)}
            >
              {restaurants.map((restaurant) => (
                <option key={restaurant.id} value={restaurant.id}>
                  {restaurant.name}
                </option>
              ))}
            </select>
          </label>

          <form className="stack menu-form" onSubmit={createMenuItem}>
            <div className="row">
              <label>
                Item name
                <input
                  required
                  value={itemForm.name}
                  onChange={(event) =>
                    setItemForm({ ...itemForm, name: event.target.value })
                  }
                />
              </label>
              <label>
                Price
                <input
                  required
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={itemForm.price}
                  onChange={(event) =>
                    setItemForm({ ...itemForm, price: event.target.value })
                  }
                />
              </label>
            </div>
            <label>
              Description
              <input
                value={itemForm.description}
                onChange={(event) =>
                  setItemForm({ ...itemForm, description: event.target.value })
                }
              />
            </label>
            <button
              className="btn"
              disabled={busy || !selectedId}
              type="submit"
            >
              Add menu item
            </button>
          </form>

          <ul className="admin-menu">
            {menu.map((item) => (
              <li key={item.id} className="admin-menu-row">
                <div>
                  <strong>{item.name}</strong>
                  <p className="muted small">
                    {money(item.price)} ·{" "}
                    {item.is_available ? "available" : "unavailable"}
                  </p>
                </div>
                <div className="admin-menu-actions">
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    className="price-input"
                    value={priceDrafts[item.id] ?? item.price}
                    onChange={(event) =>
                      setPriceDrafts({
                        ...priceDrafts,
                        [item.id]: event.target.value,
                      })
                    }
                  />
                  <button
                    type="button"
                    className="btn btn-small"
                    onClick={() => void savePrice(item)}
                  >
                    Save
                  </button>
                  <button
                    type="button"
                    className="btn btn-small"
                    onClick={() => void toggleAvailability(item)}
                  >
                    {item.is_available ? "Disable" : "Enable"}
                  </button>
                  <button
                    type="button"
                    className="btn btn-small btn-danger"
                    onClick={() => void deleteItem(item)}
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
