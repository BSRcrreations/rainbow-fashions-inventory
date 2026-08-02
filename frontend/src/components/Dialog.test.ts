import { describe, expect, it } from "vitest";
import source from "./Dialog.tsx?raw";

describe("Dialog", () => {
  it("renders above the page and keeps its content within the usable viewport", () => {
    expect(source).toContain("createPortal");
    expect(source).toContain("document.body");
    expect(source).toContain("max-h-[min(88svh,52rem)]");
    expect(source).toContain("overflow-y-auto overscroll-contain");
  });

  it("supports predictable closing and keyboard focus", () => {
    expect(source).toContain("event.key === \"Escape\"");
    expect(source).toContain("event.key !== \"Tab\"");
    expect(source).toContain("event.target === event.currentTarget");
    expect(source).toContain("openerRef.current?.focus");
  });
});
