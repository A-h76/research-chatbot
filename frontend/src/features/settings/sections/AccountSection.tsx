import { useState } from "react";
import { LogOut, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useMe, useUpdateProfile } from "@/features/profile/useMe";
import { api } from "@/lib/apiClient";
import { toast } from "@/components/common/Toast";

export function AccountSection() {
  const { data: me, refetch } = useMe();
  const updateProfile = useUpdateProfile();

  const [name, setName] = useState("");
  const [nameTouched, setNameTouched] = useState(false);
  const displayName = nameTouched ? name : (me?.name ?? "");

  const [newEmail, setNewEmail] = useState("");
  const [emailBusy, setEmailBusy] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordBusy, setPasswordBusy] = useState(false);

  const [logoutBusy, setLogoutBusy] = useState(false);

  const hasPassword = Boolean(me?.has_password);
  const provider = me?.auth_provider || "password";

  return (
    <div className="flex flex-col gap-8">
      <div className="rounded-xl border border-border bg-muted/30 p-5">
        <p className="text-sm font-medium text-foreground">Profile</p>
        <p className="mt-1 text-[13px] text-muted-foreground">
          Signed in as <span className="text-foreground">{me?.email}</span>
          {provider !== "password" ? (
            <>
              {" "}
              · via <span className="capitalize text-foreground">{provider}</span>
            </>
          ) : null}
        </p>
        <div className="mt-4 grid gap-1.5">
          <Label htmlFor="account-name">Display name</Label>
          <Input
            id="account-name"
            value={displayName}
            onChange={(e) => {
              setNameTouched(true);
              setName(e.target.value);
            }}
            placeholder="Your name"
            maxLength={200}
          />
        </div>
        <Button
          className="mt-3"
          disabled={updateProfile.isPending || !displayName.trim() || displayName.trim() === me?.name}
          onClick={async () => {
            try {
              await updateProfile.mutateAsync({ name: displayName.trim() });
              toast.success("Name saved");
              setNameTouched(false);
            } catch {
              toast.error("Could not save name");
            }
          }}
        >
          Save name
        </Button>
      </div>

      <div className="rounded-xl border border-border bg-muted/30 p-5">
        <p className="text-sm font-medium text-foreground">Email</p>
        <p className="mt-1 text-[13px] text-muted-foreground">
          Current address: <span className="text-foreground">{me?.email}</span>
        </p>
        <p className="mt-1 text-[13px] text-muted-foreground">
          We&apos;ll send a confirmation link to the new address before switching.
        </p>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="min-w-0 flex-1 grid gap-1.5">
            <Label htmlFor="new-email">New email</Label>
            <Input
              id="new-email"
              type="email"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              placeholder="you@university.edu"
            />
          </div>
          <Button
            variant="outline"
            disabled={emailBusy || !newEmail.trim()}
            onClick={async () => {
              setEmailBusy(true);
              try {
                await api.post("/auth/change-email", { new_email: newEmail.trim() });
                toast.success("Check your new inbox to confirm the change");
                setNewEmail("");
              } catch {
                toast.error("Could not start email change");
              } finally {
                setEmailBusy(false);
              }
            }}
          >
            Change email
          </Button>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-muted/30 p-5">
        <p className="text-sm font-medium text-foreground">
          {hasPassword ? "Change password" : "Set a password"}
        </p>
        <p className="mt-1 text-[13px] text-muted-foreground">
          {hasPassword
            ? "Other devices will be signed out after you change it."
            : "Add a password so you can sign in with email as well as Google or magic link."}
        </p>
        <div className="mt-4 flex flex-col gap-3 max-w-md">
          {hasPassword ? (
            <div className="grid gap-1.5">
              <Label htmlFor="current-password">Current password</Label>
              <Input
                id="current-password"
                type="password"
                autoComplete="current-password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
              />
            </div>
          ) : null}
          <div className="grid gap-1.5">
            <Label htmlFor="new-password">New password</Label>
            <Input
              id="new-password"
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="At least 10 characters"
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="confirm-password">Confirm new password</Label>
            <Input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>
          <Button
            className="self-start"
            disabled={
              passwordBusy ||
              newPassword.length < 10 ||
              newPassword !== confirmPassword ||
              (hasPassword && !currentPassword)
            }
            onClick={async () => {
              if (newPassword !== confirmPassword) {
                toast.error("Passwords do not match");
                return;
              }
              setPasswordBusy(true);
              try {
                await api.post("/auth/change-password", {
                  current_password: hasPassword ? currentPassword : undefined,
                  new_password: newPassword,
                  confirm_password: confirmPassword,
                });
                toast.success(hasPassword ? "Password updated" : "Password set");
                setCurrentPassword("");
                setNewPassword("");
                setConfirmPassword("");
                await refetch();
              } catch (err: unknown) {
                const detail =
                  err && typeof err === "object" && "message" in err
                    ? String((err as { message: string }).message)
                    : "Could not update password";
                toast.error(detail === "session_expired" ? "Session expired" : detail);
              } finally {
                setPasswordBusy(false);
              }
            }}
          >
            {hasPassword ? "Update password" : "Set password"}
          </Button>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-muted/30 p-5">
        <p className="text-sm font-medium text-foreground flex items-center gap-2">
          <Shield className="size-4" /> Sessions
        </p>
        <p className="mt-1 text-[13px] text-muted-foreground">
          Sign out everywhere, including this device. You&apos;ll need to sign in again.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button
            variant="outline"
            disabled={logoutBusy}
            onClick={async () => {
              setLogoutBusy(true);
              try {
                await api.post("/api/auth/logout-all");
                window.location.href = "/auth/sign-in";
              } catch {
                toast.error("Could not revoke sessions");
                setLogoutBusy(false);
              }
            }}
          >
            Sign out all devices
          </Button>
          <Button variant="outline" onClick={() => (window.location.href = "/logout")}>
            <LogOut className="size-4" /> Log out
          </Button>
        </div>
      </div>
    </div>
  );
}
