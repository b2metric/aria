import NextAuth from "next-auth";

declare module "next-auth" {
  interface Session {
    accessToken?: string;
    idToken?: string;
    /** Set to "RefreshAccessTokenError" when silent token refresh fails — client should re-login. */
    error?: string;
    user?: {
      name?: string | null;
      email?: string | null;
      image?: string | null;
      /** Realm roles surfaced from the Keycloak JWT (e.g. "admin"). */
      roles?: string[];
    };
  }
}
