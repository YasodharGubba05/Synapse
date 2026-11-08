import { createContext, useContext } from 'react';

/**
 * Authentication state shared across the app.
 *
 * status: 'loading'       - still resolving the cookie session (first paint)
 *         'authenticated' - `user` is populated
 *         'anonymous'     - show the login / registration screen
 */
export const AuthContext = createContext({
  status: 'loading',
  user: null,
  login: async () => {},
  register: async () => {},
  logout: async () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}
