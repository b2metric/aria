"use client";

import { useSession } from "next-auth/react";
import { User, Mail, Shield } from "lucide-react";

interface ProfileRowProps {
  Icon: typeof User;
  label: string;
  value: string;
}

function ProfileRow({ Icon, label, value }: ProfileRowProps) {
  return (
    <div className="flex items-center gap-4 px-6 py-4">
      <Icon className="h-5 w-5 text-gray-400 flex-shrink-0" />
      <div className="min-w-0">
        <div className="text-xs uppercase tracking-wider text-gray-400">{label}</div>
        <div className="text-sm font-medium text-gray-900 break-all">{value}</div>
      </div>
    </div>
  );
}

export default function ProfileSettings() {
  const { data: session } = useSession();
  const user = session?.user;
  const roles = user?.roles ?? [];

  const name = user?.name || "—";
  const email = user?.email || "—";
  const roleLabel = roles.length ? roles.join(", ") : "—";

  return (
    <div className="max-w-2xl mx-auto py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Profile</h1>
        <p className="text-gray-500 mt-1">Your account details.</p>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-100 overflow-hidden">
        <ProfileRow Icon={User} label="Name" value={name} />
        <ProfileRow Icon={Mail} label="Email" value={email} />
        <ProfileRow Icon={Shield} label="Role" value={roleLabel} />
      </div>

      <p className="text-xs text-gray-500">
        Password and email changes are managed through your workspace settings.
      </p>
    </div>
  );
}
