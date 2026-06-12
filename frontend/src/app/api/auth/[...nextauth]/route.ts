import NextAuth, { NextAuthOptions } from "next-auth";
import KeycloakProvider from "next-auth/providers/keycloak";

const KEYCLOAK_ISSUER =
  process.env.KEYCLOAK_ISSUER || "http://auth.aria.localhost/auth/realms/aria";
const KEYCLOAK_CLIENT_ID = process.env.KEYCLOAK_CLIENT_ID || "aria-web";
const KEYCLOAK_CLIENT_SECRET = process.env.KEYCLOAK_CLIENT_SECRET || "";

/**
 * Refresh an expired Keycloak access token using the stored refresh_token.
 *
 * Keycloak access tokens are short-lived (~1h). Without this, the NextAuth
 * session cookie (30d) outlives the access token, so after the first hour
 * every backend Bearer call 401s even though the user still "looks" logged in
 * (this was the `Failed to fetch conversation: 401` bug).
 */
async function refreshAccessToken(token: any) {
  try {
    if (!token.refreshToken) throw new Error("no refresh_token on session");

    const body = new URLSearchParams({
      grant_type: "refresh_token",
      client_id: KEYCLOAK_CLIENT_ID,
      refresh_token: token.refreshToken as string,
    });
    if (KEYCLOAK_CLIENT_SECRET) body.set("client_secret", KEYCLOAK_CLIENT_SECRET);

    const res = await fetch(`${KEYCLOAK_ISSUER}/protocol/openid-connect/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    const refreshed = await res.json();
    if (!res.ok) throw refreshed;

    return {
      ...token,
      accessToken: refreshed.access_token,
      idToken: refreshed.id_token ?? token.idToken,
      // Keycloak rotates refresh tokens — keep the new one, fall back to the old.
      refreshToken: refreshed.refresh_token ?? token.refreshToken,
      expiresAt: Math.floor(Date.now() / 1000) + Number(refreshed.expires_in ?? 300),
      error: undefined,
    };
  } catch (err) {
    console.error("Keycloak token refresh failed", err);
    // Surface to the client so it can force a re-login instead of silently 401ing.
    return { ...token, error: "RefreshAccessTokenError" };
  }
}

export const authOptions: NextAuthOptions = {
  debug: true,
  providers: [
    KeycloakProvider({
      clientId: KEYCLOAK_CLIENT_ID,
      clientSecret: KEYCLOAK_CLIENT_SECRET,
      issuer: KEYCLOAK_ISSUER,
      authorization: {
        params: {
          // offline_access guarantees Keycloak issues a refresh_token so the
          // jwt callback can rotate the short-lived access token.
          scope: "openid profile email offline_access",
        },
      },
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      // 1) Initial sign-in — capture tokens + expiry + roles.
      if (account) {
        token.accessToken = account.access_token;
        token.idToken = account.id_token;
        token.refreshToken = account.refresh_token;
        token.expiresAt = account.expires_at; // epoch seconds

        if (profile) {
          const profileRoles = (profile as any)?.realm_access?.roles || [];
          token.roles = profileRoles;
        }

        if (token.accessToken) {
          try {
            const tokenBase64 = (token.accessToken as string).split(".")[1];
            const decodedToken = JSON.parse(
              Buffer.from(tokenBase64, "base64").toString()
            );
            if (decodedToken.role) {
              token.roles = [decodedToken.role];
            }
          } catch (e) {
            console.error("Could not parse JWT to extract role", e);
          }
        }
        return token;
      }

      // 2) Subsequent requests — reuse the access token while still valid
      //    (60s skew buffer); otherwise refresh it via the refresh_token.
      const expiresAtMs = token.expiresAt
        ? (token.expiresAt as number) * 1000
        : 0;
      if (expiresAtMs && Date.now() < expiresAtMs - 60_000) {
        return token;
      }
      if (token.refreshToken) {
        return await refreshAccessToken(token);
      }
      return token;
    },
    async session({ session, token }: any) {
      session.accessToken = token.accessToken as string;
      session.idToken = token.idToken as string;
      session.error = token.error as string | undefined;

      if (session.user) {
        session.user.roles = (token.roles as string[]) || [];
        session.user.idToken = token.idToken as string; // Expose idToken to client session
      }
      return session;
    },
  },
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
