import NextAuth, { NextAuthOptions } from "next-auth";
import KeycloakProvider from "next-auth/providers/keycloak";
import CredentialsProvider from "next-auth/providers/credentials";

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
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        username: { label: "Email/Username", type: "text" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        if (!credentials?.username || !credentials?.password) return null;
        
        try {
          const body = new URLSearchParams({
            grant_type: "password",
            client_id: KEYCLOAK_CLIENT_ID,
            username: credentials.username,
            password: credentials.password,
            scope: "openid",
          });
          
          if (KEYCLOAK_CLIENT_SECRET) {
             body.set("client_secret", KEYCLOAK_CLIENT_SECRET);
          }

          const res = await fetch(`${KEYCLOAK_ISSUER}/protocol/openid-connect/token`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body,
          });
          
          const data = await res.json();
          
          if (!res.ok) {
            console.error("Keycloak auth failed:", data);
            throw new Error(data.error_description || "Invalid credentials");
          }
          
          // Decode the token to extract user info (like email, roles)
          const tokenBase64 = data.access_token.split(".")[1];
          const decodedToken = JSON.parse(Buffer.from(tokenBase64, "base64").toString());

          return {
            id: decodedToken.sub,
            name: decodedToken.name || decodedToken.preferred_username || credentials.username,
            email: decodedToken.email || credentials.username,
            accessToken: data.access_token,
            idToken: data.id_token,
            refreshToken: data.refresh_token,
            expiresAt: Math.floor(Date.now() / 1000) + Number(data.expires_in ?? 300),
            role: decodedToken.role || (decodedToken.realm_access?.roles || [])[0]
          } as any;
        } catch (e) {
          console.error("Error in authorize:", e);
          return null;
        }
      }
    })
  ],
  pages: {
    signIn: '/login',
  },
  callbacks: {
    async jwt({ token, user, account, profile }) {
      // 1) Initial sign-in — capture tokens + expiry + roles.
      // With CredentialsProvider, `user` contains the object returned from `authorize`
      if (user) {
        const u = user as any;
        token.accessToken = u.accessToken;
        token.idToken = u.idToken;
        token.refreshToken = u.refreshToken;
        token.expiresAt = u.expiresAt; // epoch seconds
        
        token.roles = u.role ? [u.role] : [];
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
