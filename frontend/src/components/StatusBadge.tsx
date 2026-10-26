import type { ReactNode } from "react";

import type { OrderStatus } from "../types";

type Tone = OrderStatus | "admin" | "customer" | "neutral";

export function StatusBadge({
  tone,
  children,
}: {
  tone: Tone;
  children: ReactNode;
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
