import { act, renderHook } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { useIsMobile } from "@/hooks/use-mobile";

it("follows the sidebar media query independently of innerWidth", () => {
  const media = Object.assign(new EventTarget(), { matches: true });
  const matchMedia = vi.fn(() => media);
  vi.stubGlobal("matchMedia", matchMedia);
  vi.stubGlobal("innerWidth", 1280);

  const { result } = renderHook(useIsMobile);

  expect(matchMedia).toHaveBeenCalledWith("(width < 48rem)");
  expect(result.current).toBe(true);

  vi.stubGlobal("innerWidth", 400);
  act(() => {
    media.matches = false;
    media.dispatchEvent(new Event("change"));
  });

  expect(result.current).toBe(false);
});
