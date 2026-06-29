import { redirect } from "next/navigation";

export default function SettingsPage() {
  // The /settings index had no content (blank page); land on the first screen.
  redirect("/settings/general");
}
