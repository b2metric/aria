import { redirect } from "next/navigation";

export default function AdminPage() {
  // The /admin index had no content (blank page); land on the first admin screen.
  redirect("/admin/users");
}
