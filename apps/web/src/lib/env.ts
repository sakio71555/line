type WebEnv = {
  apiBaseUrl: string;
  liffId: string;
  supabaseUrl: string;
  supabasePublishableKey: string;
};

export const webEnv: WebEnv = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "",
  liffId: import.meta.env.VITE_LIFF_ID ?? "",
  supabaseUrl: import.meta.env.VITE_SUPABASE_URL ?? "",
  supabasePublishableKey: import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY ?? "",
};

export function getMissingFrontendEnv(): string[] {
  const missing: string[] = [];

  if (!webEnv.supabaseUrl) missing.push("VITE_SUPABASE_URL");
  if (!webEnv.supabasePublishableKey) missing.push("VITE_SUPABASE_PUBLISHABLE_KEY");
  if (!webEnv.liffId) missing.push("VITE_LIFF_ID");
  if (!webEnv.apiBaseUrl) missing.push("VITE_API_BASE_URL");

  return missing;
}
