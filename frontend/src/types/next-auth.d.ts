import NextAuth from "next-auth";

declare module "next-auth" {
  interface Session {
    accessToken?: string;
    idToken?: string;
    /** Set to "RefreshAccessTokenError" when silent token refresh fails — client should re-login. */
    error?: string;
  }
}
