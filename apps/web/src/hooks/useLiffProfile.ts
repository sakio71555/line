import { useEffect, useState } from "react";

import { initializeLiff, type LiffProfileState } from "../lib/liff";

const initialState: LiffProfileState = {
  ready: false,
  inClient: false,
  displayName: null,
  userId: null,
  idToken: null,
  error: null,
};

export function useLiffProfile(): LiffProfileState {
  const [profile, setProfile] = useState<LiffProfileState>(initialState);

  useEffect(() => {
    let mounted = true;

    initializeLiff().then((state) => {
      if (mounted) setProfile(state);
    });

    return () => {
      mounted = false;
    };
  }, []);

  return profile;
}
