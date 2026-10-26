import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../auth";
import { StatusBadge } from "./StatusBadge";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">T</span>
          <div>
            <strong>Takeaway</strong>
            <span className="brand-sub">manual test console</span>
          </div>
        </div>

        {user ? (
          <>
            <nav className="nav">
              <NavLink to="/restaurants">Restaurants</NavLink>
              <NavLink to="/orders">Orders</NavLink>
              {user.role === "admin" && <NavLink to="/admin">Admin</NavLink>}
              <NavLink to="/guard-lab">Guard lab</NavLink>
            </nav>
            <div className="session">
              <span className="session-name">{user.full_name}</span>
              <StatusBadge tone={user.role === "admin" ? "admin" : "customer"}>
                {user.role}
              </StatusBadge>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => {
                  logout();
                  navigate("/login");
                }}
              >
                Log out
              </button>
            </div>
          </>
        ) : (
          <div className="session">
            <span className="muted">Not signed in</span>
            <NavLink className="btn btn-ghost" to="/login">
              Sign in
            </NavLink>
          </div>
        )}
      </header>

      <main className="container">
        <Outlet />
      </main>

      <footer className="footer">
        API docs:{" "}
        <a href="/docs" target="_blank" rel="noreferrer">
          /docs
        </a>{" "}
        · Frontend calls the API through the same origin.
      </footer>
    </div>
  );
}
