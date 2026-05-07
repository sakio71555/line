import { createClient } from "@supabase/supabase-js";

import { webEnv } from "./env";

export const supabase =
  webEnv.supabaseUrl && webEnv.supabasePublishableKey
    ? createClient(webEnv.supabaseUrl, webEnv.supabasePublishableKey)
    : null;
