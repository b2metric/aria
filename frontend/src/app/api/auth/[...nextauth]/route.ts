import NextAuth from "next-auth";
import KeycloakProvider from "next-auth/providers/keycloak";

const handler = NextAuth({
  debug: true,
  providers: [
    KeycloakProvider({
      clientId: process.env.KEYCLOAK_CLIENT_ID || "aria-web",
      clientSecret: process.env.KEYCLOAK_CLIENT_SECRET || "",
      issuer: process.env.KEYCLOAK_ISSUER || "http://localhost:8080/auth/realms/aria",
      authorization: {
        params: {
          scope: "openid"
        }
      }
    }),
  ],
  callbacks: {
    async jwt({ token, account }) {
      // Keycloak access token'ini session objesine tasi
      if (account) {
        token.accessToken = account.access_token;
        token.idToken = account.id_token;
      }
      return token;
    },
    async session({ session, token }: any) {
      // Backend'e atilacak Authorization: Bearer ***
      session.accessToken = token.accessToken;
      session.idToken = token.idToken;
      return session;
    },
  },
});

export { handler as GET, handler as POST };
