with open("frontend/src/app/admin/schema/page.tsx", "r") as f:
    content = f.read()

old_auth = """  const { data: session, status } = useSession();
  const token = (session as any)?.accessToken;
  const isAdmin = true; // In a real app, check session.user.role or similar
  const workspaceId = "default";"""

new_auth = """  const { data: session, status } = useSession();
  const token = (session as any)?.accessToken;
  const isAdmin = (session as any)?.user?.roles?.includes("admin") || (session as any)?.user?.role === "admin";
  const workspaceId = (session as any)?.user?.workspaceId || "default";"""

content = content.replace(old_auth, new_auth)

with open("frontend/src/app/admin/schema/page.tsx", "w") as f:
    f.write(content)
