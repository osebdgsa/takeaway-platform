import { Link } from "react-router-dom";

import { useAuth } from "../auth";

export default function ForbiddenPage() {
  const { user } = useAuth();

  return (
    <section className="card forbidden">
      <p className="status-code">403</p>
      <h1>Admin area</h1>
      <p>
        You are signed in as <strong>{user?.email}</strong> with role{" "}
        <span className={`badge badge-${user?.role}`}>{user?.role}</span>.
      </p>
      <p className="muted">
        This screen is hidden by the client, but the API enforces the same rule
        independently: direct calls to admin endpoints return{" "}
        <code>403 Forbidden</code>. Try it in the{" "}
        <Link to="/guard-lab">Guard lab</Link>.
      </p>
      <Link className="btn" to="/restaurants">
        Back to restaurants
      </Link>
    </section>
  );
}
