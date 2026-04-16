export const STUDIO_PALETTE = [
  { name: "Amber", hsl: "30 85% 48%" },
  { name: "Tomato", hsl: "10 78% 54%" },
  { name: "Crimson", hsl: "336 80% 48%" },
  { name: "Plum", hsl: "292 45% 51%" },
  { name: "Violet", hsl: "252 58% 58%" },
  { name: "Indigo", hsl: "226 70% 55%" },
  { name: "Cyan", hsl: "190 90% 38%" },
  { name: "Teal", hsl: "173 80% 36%" },
  { name: "Jade", hsl: "164 60% 40%" },
  { name: "Grass", hsl: "131 41% 46%" },
  { name: "Orange", hsl: "24 94% 50%" },
  { name: "Gold", hsl: "42 90% 48%" },
] as const;

export type StudioColorName = (typeof STUDIO_PALETTE)[number]["name"];

export function getStudioThemeStyle(primaryHsl: string): string {
  return `:root { --primary: ${primaryHsl}; --ring: ${primaryHsl}; }`;
}
