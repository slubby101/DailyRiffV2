import { STUDIO_PALETTE, getStudioThemeStyle } from "@/lib/studio-theme";

describe("STUDIO_PALETTE", () => {
  it("has exactly 12 swatches", () => {
    expect(STUDIO_PALETTE).toHaveLength(12);
  });

  it("starts with Amber as default", () => {
    expect(STUDIO_PALETTE[0].name).toBe("Amber");
    expect(STUDIO_PALETTE[0].hsl).toBe("30 85% 48%");
  });

  it("every swatch has a name and valid HSL string", () => {
    for (const swatch of STUDIO_PALETTE) {
      expect(swatch.name).toBeTruthy();
      expect(swatch.hsl).toMatch(/^\d+ \d+% \d+%$/);
    }
  });
});

describe("getStudioThemeStyle", () => {
  it("returns CSS overriding --primary and --ring", () => {
    const style = getStudioThemeStyle("180 60% 35%");
    expect(style).toContain("--primary: 180 60% 35%");
    expect(style).toContain("--ring: 180 60% 35%");
  });
});
