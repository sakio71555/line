import liff from "@line/liff";

import { webEnv } from "./env";

export type LiffProfileState = {
  ready: boolean;
  inClient: boolean;
  displayName: string | null;
  userId: string | null;
  idToken: string | null;
  error: string | null;
};

export async function initializeLiff(): Promise<LiffProfileState> {
  if (!webEnv.liffId) {
    return {
      ready: false,
      inClient: false,
      displayName: null,
      userId: null,
      idToken: null,
      error: "LIFF ID is not configured.",
    };
  }

  try {
    await liff.init({ liffId: webEnv.liffId });

    const inClient = liff.isInClient();
    if (!liff.isLoggedIn() && !inClient) {
      return {
        ready: true,
        inClient,
        displayName: null,
        userId: null,
        idToken: null,
        error: null,
      };
    }

    const profile = await liff.getProfile();
    const idToken = liff.getIDToken();
    return {
      ready: true,
      inClient,
      displayName: profile.displayName,
      userId: profile.userId,
      idToken,
      error: null,
    };
  } catch {
    return {
      ready: false,
      inClient: false,
      displayName: null,
      userId: null,
      idToken: null,
      error: "LIFF initialization failed.",
    };
  }
}

export function closeLiffWindow(): void {
  if (liff.isInClient()) {
    liff.closeWindow();
  }
}
