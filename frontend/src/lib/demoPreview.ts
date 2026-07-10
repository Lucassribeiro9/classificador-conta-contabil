export const DEMO_PREVIEW_TOKEN = "demo-preview-token";
export const DEMO_PREVIEW_EMAIL = "demo@preview.local";

export function isDemoPreviewToken(accessToken: string) {
  return (import.meta.env.DEV || import.meta.env.VITE_ENABLE_DEMO_LOGIN === "true") && accessToken === DEMO_PREVIEW_TOKEN;
}
