import { signOut } from "next-auth/react";

// Single source of truth for the Keycloak issuer (no localhost:8080 footgun).
const ISSUER =
  process.env.NEXT_PUBLIC_KEYCLOAK_ISSUER ||
  "http://auth.aria.localhost/auth/realms/aria";
const CLIENT_ID = process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID || "aria-web";

/**
 * Federated logout: clears the NextAuth session AND ends the Keycloak SSO session.
 *
 * NextAuth's signOut({callbackUrl}) only honors SAME-ORIGIN callback URLs, so it
 * silently drops a cross-origin Keycloak end-session URL and the SSO cookie survives
 * (→ the next "login" is a silent SSO re-auth straight to the dashboard). We therefore
 * clear the local session first (redirect:false), then navigate the browser to
 * Keycloak's end-session endpoint with id_token_hint so the SSO session is actually
 * terminated and Keycloak redirects us back clean.
 */
export async function keycloakLogout(idToken?: string | null): Promise<void> {
  await signOut({ redirect: false });
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    post_logout_redirect_uri: window.location.origin,
  });
  if (idToken) params.set("id_token_hint", idToken);
  window.location.href = `${ISSUER}/protocol/openid-connect/logout?${params.toString()}`;
}
