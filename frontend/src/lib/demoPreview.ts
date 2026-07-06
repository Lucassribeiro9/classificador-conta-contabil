export const DEMO_PREVIEW_TOKEN = "demo-preview-token";
export const DEMO_PREVIEW_EMAIL = "demo@preview.local";

export function isDemoPreviewToken(accessToken: string) {
  return import.meta.env.DEV && accessToken === DEMO_PREVIEW_TOKEN;
}
