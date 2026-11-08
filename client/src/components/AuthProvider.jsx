import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AuthContext } from '../authContext';
import {
  SESSION_EXPIRED_EVENT,
  fetchCurrentUser,
  loginAccount,
  logoutAccount,
  registerAccount,
} from '../api';
import { SETTINGS_STORAGE_KEY } from '../sessionSettings';

/**
 * Owns the authentication session.
 *
 * On mount it asks the backend who we are. Because the access and refresh
 * tokens live in HTTP-only cookies the browser sends by itself, this is what
 * makes a page refresh keep the user signed in without ever putting a token
 * where page scripts could read it.
 */
export default function AuthProvider({ children }) {
  const [status, setStatus] = useState('loading');
  const [user, setUser] = useState(null);

  // No mounted-ref guard here on purpose: React 19 StrictMode mounts, then
  // unmounts, then remounts in development, and a ref set to false during
  // that first cleanup would block every later update. Setting state after
  // unmount is a no-op in React 18+, so the guard bought nothing anyway.
  const applyUser = useCallback((nextUser) => {
    setUser(nextUser);
    setStatus(nextUser ? 'authenticated' : 'anonymous');
  }, []);

  // Resolve the existing cookie session once, at startup.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const currentUser = await fetchCurrentUser();
        if (!cancelled) applyUser(currentUser);
      } catch {
        if (!cancelled) applyUser(null);
      }
    })();
    return () => { cancelled = true; };
  }, [applyUser]);

  // The API layer raises this when a refresh could not save the session.
  useEffect(() => {
    const handleExpired = () => applyUser(null);
    window.addEventListener(SESSION_EXPIRED_EVENT, handleExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, handleExpired);
  }, [applyUser]);

  const login = useCallback(async (credentials) => {
    const result = await loginAccount(credentials);
    applyUser(result.user);
    return result.user;
  }, [applyUser]);

  const register = useCallback(async (details) => {
    const result = await registerAccount(details);
    applyUser(result.user);
    return result.user;
  }, [applyUser]);

  const logout = useCallback(async () => {
    try {
      await logoutAccount();
    } finally {
      // Drop the Groq key and all per-tab settings so the next person at this
      // browser does not inherit the previous user's credentials or context.
      try { sessionStorage.removeItem(SETTINGS_STORAGE_KEY); } catch { /* ignore */ }
      applyUser(null);
    }
  }, [applyUser]);

  const value = useMemo(
    () => ({ status, user, login, register, logout }),
    [status, user, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
