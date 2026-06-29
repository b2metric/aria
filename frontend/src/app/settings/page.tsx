import { redirect } from "next/navigation";

export default function SettingsPage() {
  // /settings is personal now; land on the profile screen.
  redirect("/settings/profile");
}
