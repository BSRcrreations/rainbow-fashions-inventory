import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(new URL("./LoginPage.tsx", import.meta.url), "utf8");

describe("LoginPage credential handling", () => {
  it("starts with blank credential fields and enables browser autofill", () => {
    expect(source).toContain('const [email, setEmail] = useState("");');
    expect(source).toContain('const [password, setPassword] = useState("");');
    expect(source).toContain('autoComplete="username"');
    expect(source).toContain('autoComplete="current-password"');
  });
});
