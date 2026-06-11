import NextAuth, { NextAuthOptions } from "next-auth";
import KeycloakProvider from "next-auth/providers/keycloak";

export const authOptions: NextAuthOptions = {
  debug: true,
  providers: [
    KeycloakProvider({
      clientId: process.env.KEYCLOAK_CLIENT_ID || "aria-web",
      clientSecret: process.env.KEYCLOAK_CLIENT_SECRET || "",
      issuer: process.env.KEYCLOAK_ISSUER || "http://auth.aria.localhost/auth/realms/aria",
      authorization: {
        params: {
          scope: "openid"
        }
      }
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account) {
        token.accessToken = account.access_token;
        token.idToken = account.id_token;
        
        if (profile) {
          const profileRoles = (profile as any)?.realm_access?.roles || [];
          token.roles = profileRoles;
        }
        
        if (token.accessToken) {
          try {
            const tokenBase64 = (token.accessToken as string).split('.')[1];
            const decodedToken = JSON.parse(Buffer.from(tokenBase64, 'base64').toString());
            if (decodedToken.role) {
              token.roles = [decodedToken.role];
            }
          } catch (e) {
            console.error("Could not parse JWT to extract role", e);
          }
        }
      }
      return token;
    },
    async session({ session, token }: any) {
      session.accessToken = token.accessToken as string;
      session.idToken = token.idToken as string;
      
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
