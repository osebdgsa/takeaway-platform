export interface DemoCredential {
  label: string;
  email: string;
  password: string;
  role: "admin" | "customer";
  expected: string;
}

export const DEMO_CREDENTIALS: DemoCredential[] = [
  {
    label: "Admin",
    email: "admin@example.com",
    password: "admin12345",
    role: "admin",
    expected: "Can manage menus and advance any order",
  },
  {
    label: "Customer 1",
    email: "customer@example.com",
    password: "customer12345",
    role: "customer",
    expected: "Own orders only; 403 on admin actions",
  },
  {
    label: "Customer 2",
    email: "customer2@example.com",
    password: "customer212345",
    role: "customer",
    expected: "Cannot see Customer 1's orders (404)",
  },
  {
    label: "Disabled",
    email: "blocked@example.com",
    password: "blocked12345",
    role: "customer",
    expected: "Login refused with 403",
  },
];
